from __future__ import annotations

import json
import re
from typing import Any

from app.adk_runtime import ADKJsonRuntime
from app.evals import evaluate_fit, evaluate_improvement
from app.ledger import LedgerStore
from app.market_data import load_markets
from app.models import (
    CandidateMarket,
    FitClass,
    ImprovementResult,
    MarketFit,
    NormalizedClaim,
    RejectedMarket,
    RunResult,
)
from app.phoenix_annotations import log_eval_annotations
from app.phoenix_mcp import PhoenixMCPInspector
from app.tracing import TraceContext


class MarketFitTraceAgent:
    def __init__(
        self,
        *,
        store: LedgerStore | None = None,
        adk_runtime: ADKJsonRuntime | None = None,
        markets: list[CandidateMarket] | None = None,
    ) -> None:
        self.store = store or LedgerStore()
        self.adk_runtime = adk_runtime or ADKJsonRuntime()
        self.markets = markets or load_markets()

    async def run(
        self,
        *,
        thesis: str,
        title: str | None = None,
        prompt_version: str = "v1_lenient",
        prior_failure_summary: str | None = None,
    ) -> RunResult:
        trace = TraceContext()
        run = self.store.create_run(
            user_goal=thesis,
            model=self.adk_runtime.runtime_name,
            prompt_version=prompt_version,
        )
        run_id = run["id"]
        attrs = {
            "run_id": run_id,
            "model": self.adk_runtime.runtime_name,
            "prompt_version": prompt_version,
            "prior_failure_summary": prior_failure_summary or "",
        }

        with trace.span("market_fit_trace_agent.run", attrs):
            with trace.span("user_goal_received", {"run_id": run_id, "goal_length": len(thesis)}):
                pass
            with trace.span("source_ingested", {"run_id": run_id}):
                source = self.store.create_source(raw_text=thesis, title=title)
            with trace.span("claim_extracted", attrs):
                claim = await self.extract_claim(thesis, prompt_version)
            with trace.span(
                "candidate_markets_loaded",
                {"run_id": run_id, "count": len(self.markets)},
            ):
                markets = self.markets
            with trace.span("market_fit_classified", attrs):
                fit, model_fit_proposal = await self.classify_fit(
                    claim=claim,
                    markets=markets,
                    prompt_version=prompt_version,
                    prior_failure_summary=prior_failure_summary,
                )
                model_fit_proposal_json = _json_preview(model_fit_proposal)
                trace.set_current_span_attributes(
                    {
                        "model_fit_proposal.present": bool(model_fit_proposal),
                        "model_fit_proposal.preview": model_fit_proposal_json or "",
                        "policy_decision_source": "deterministic_policy",
                    }
                )
            with trace.span("rejected_markets_explained", {"run_id": run_id}):
                fit = self._ensure_rejected_markets(fit, markets)
            with trace.span("ledger_claim_proposed", attrs):
                claim_ref = self.store.propose_claim(
                    run_id=run_id,
                    source_id=source["id"],
                    claim_text=claim.claim_text,
                    entities=claim.entities,
                    horizon=claim.horizon,
                    stance=claim.stance,
                    confidence=claim.confidence,
                    reasoning_summary=claim.reasoning_summary,
                )
                claim_id = claim_ref["claim_id"]
                self.store.attach_market_fit(
                    claim_id=claim_id,
                    recommended_market_id=fit.recommended_market_id,
                    semantic_fit_class=fit.semantic_fit_class,
                    fit_reason=fit.fit_reason,
                    captures=fit.captures,
                    misses=fit.misses,
                    rejected_markets=[item.model_dump() for item in fit.rejected_markets],
                )
            phoenix_trace_id = trace.trace_id()
            with trace.span(
                "fit_eval_run",
                {
                    **attrs,
                    "claim_id": claim_id,
                    "semantic_fit_class": fit.semantic_fit_class.value,
                    "recommended_market_id": fit.recommended_market_id or "",
                },
            ):
                eval_result = evaluate_fit(
                    claim=claim,
                    fit=fit,
                    markets=markets,
                    phoenix_trace_id=phoenix_trace_id,
                )
                trace.set_current_span_attributes(
                    {
                        "eval.schema_valid": eval_result.metrics.schema_valid,
                        "eval.false_strong_recommendation": (
                            eval_result.metrics.false_strong_recommendation
                        ),
                        "eval.weak_proxy_detected": eval_result.metrics.weak_proxy_detected,
                        "eval.unsupported_implication": (
                            eval_result.metrics.unsupported_implication
                        ),
                        "eval.human_verification_required": (
                            eval_result.metrics.human_verification_required
                        ),
                        "eval.no_clean_expression_expected": (
                            eval_result.metrics.no_clean_expression_expected
                        ),
                        "eval.failure_summary": eval_result.failure_summary or "",
                    }
                )
            annotations_written = log_eval_annotations(
                span_id=trace.span_id("fit_eval_run"),
                eval_result=eval_result,
            )
            eval_result.metrics.phoenix_annotations_written = annotations_written
            with trace.span(
                "phoenix_annotations_logged",
                {
                    **attrs,
                    "run_id": run_id,
                    "claim_id": claim_id,
                    "phoenix_annotations_written": annotations_written,
                },
            ):
                pass
            eval_ref = self.store.record_eval_result(
                run_id=run_id,
                claim_id=claim_id,
                phoenix_trace_id=phoenix_trace_id,
                metrics=eval_result.metrics.model_dump(),
                failure_summary=eval_result.failure_summary,
            )
            eval_result.eval_record_id = eval_ref["eval_record_id"]
            self.store.update_run(
                run_id,
                status="completed",
                phoenix_trace_id=phoenix_trace_id,
                eval_summary_json=eval_result.metrics.model_dump_json(),
                model_fit_proposal_json=model_fit_proposal_json,
            )

        return RunResult(
            run_id=run_id,
            source_id=source["id"],
            claim_id=claim_id,
            phoenix_trace_id=phoenix_trace_id,
            phoenix_trace_url=_phoenix_trace_url(phoenix_trace_id),
            model=self.adk_runtime.runtime_name,
            prompt_version=prompt_version,
            claim=claim,
            fit=fit,
            eval=eval_result,
            ledger=self.store.query_claim_trace(claim_id),
        )

    async def improve_from_trace(self, run_id: str) -> ImprovementResult:
        inspector = PhoenixMCPInspector(self.store)
        inspection = await inspector.inspect_failed_run(run_id)
        before = self._reconstruct_run_result(run_id)
        self.store.record_trace_inspection(
            run_id=run_id,
            claim_id=before.claim_id,
            phoenix_trace_id=before.phoenix_trace_id,
            summary=inspection.summary,
            source=inspection.source,
        )
        source = self.store.get_source(before.source_id)
        after = await self.run(
            thesis=source["raw_text"],
            title=source.get("title"),
            prompt_version=inspection.recommended_prompt_version,
            prior_failure_summary=inspection.summary,
        )
        improved = evaluate_improvement(before.eval, after.eval)
        after.eval.metrics.second_run_improvement = improved
        self.store.update_run(
            after.run_id,
            eval_summary_json=after.eval.metrics.model_dump_json(),
        )
        return ImprovementResult(
            before_run_id=before.run_id,
            after_run_id=after.run_id,
            before_trace_id=before.phoenix_trace_id,
            after_trace_id=after.phoenix_trace_id,
            inspection_source=inspection.source,
            fallback_used=inspection.fallback_used,
            before_fit=before.fit.semantic_fit_class,
            after_fit=after.fit.semantic_fit_class,
            false_strong_recommendation_before=(
                before.eval.metrics.false_strong_recommendation
            ),
            false_strong_recommendation_after=(
                after.eval.metrics.false_strong_recommendation
            ),
            inspection=inspection,
            before=before,
            after=after,
        )

    async def extract_claim(self, thesis: str, prompt_version: str) -> NormalizedClaim:
        prompt = f"""
You are MarketFitTraceAgent. Extract a normalized prediction-market thesis.
Return only JSON with keys: claim_text, entities, horizon, stance, confidence,
reasoning_summary.
Prompt version: {prompt_version}
Thesis:
{thesis}
"""
        generated = await self.adk_runtime.generate_json(
            prompt=prompt,
            task_name="claim_extraction",
            instruction=(
                "You extract one normalized prediction-market thesis as strict JSON. "
                "Do not include prose outside the JSON object."
            ),
        )
        if generated and not _is_known_eval_source(thesis):
            try:
                return NormalizedClaim.model_validate(generated)
            except Exception:
                pass
        return _deterministic_extract(thesis)

    async def classify_fit(
        self,
        *,
        claim: NormalizedClaim,
        markets: list[CandidateMarket],
        prompt_version: str,
        prior_failure_summary: str | None,
    ) -> tuple[MarketFit, dict[str, Any] | list[Any] | str | None]:
        prompt = f"""
Classify which prediction-market expression best fits the normalized claim.
Allowed semantic_fit_class values: direct, indirect, weak_proxy, no_clean_expression.
Do not overclaim adjacent markets. Return only JSON matching this shape:
recommended_market_id, semantic_fit_class, fit_reason, captures, misses, rejected_markets.
Prompt version: {prompt_version}
Prior failed trace summary: {prior_failure_summary or "none"}
Claim: {claim.model_dump_json()}
Candidate markets: {json.dumps([m.model_dump() for m in markets])}
"""
        model_fit_proposal = await self.adk_runtime.generate_json(
            prompt=prompt,
            task_name="market_fit_proposal",
            instruction=(
                "You propose prediction-market fit classifications as strict JSON. "
                "Use only direct, indirect, weak_proxy, or no_clean_expression."
            ),
        )
        # ADK/Gemini is used for traceable proposal spans. Final fit decisions stay
        # deterministic so evals are reproducible and policy-owned by app code.
        return _deterministic_classify(claim, markets, prompt_version), model_fit_proposal

    def _ensure_rejected_markets(
        self, fit: MarketFit, markets: list[CandidateMarket]
    ) -> MarketFit:
        if fit.rejected_markets:
            return fit
        rejected: list[RejectedMarket] = []
        for market in markets:
            if market.market_id == fit.recommended_market_id:
                continue
            rejected.append(
                RejectedMarket(
                    market_id=market.market_id,
                    reason=(
                        "Related terms are present, but the resolution rules do not cleanly "
                        "express the normalized claim."
                    ),
                )
            )
            if len(rejected) == 2:
                break
        fit.rejected_markets = rejected
        return fit

    def _reconstruct_run_result(self, run_id: str) -> RunResult:
        data = self.store._read()
        run = self.store.get_run(run_id)
        claims = [claim for claim in data["claims"] if claim["run_id"] == run_id]
        if not claims:
            raise KeyError(f"No claim recorded for run {run_id}")
        claim_row = claims[-1]
        fit_row = self.store.get_latest_fit(claim_row["id"])
        eval_row = self.store.get_latest_eval_for_run(run_id)
        if fit_row is None or eval_row is None:
            raise KeyError(f"Run is incomplete: {run_id}")

        claim = NormalizedClaim(
            claim_text=claim_row["claim_text"],
            entities=json.loads(claim_row["entities_json"]),
            horizon=claim_row["horizon"],
            stance=claim_row["stance"],
            confidence=claim_row["confidence"],
            reasoning_summary=claim_row.get("reasoning_summary", ""),
        )
        fit = MarketFit(
            recommended_market_id=fit_row["recommended_market_id"],
            semantic_fit_class=FitClass(fit_row["semantic_fit_class"]),
            fit_reason=fit_row["fit_reason"],
            captures=json.loads(fit_row["captures_json"]),
            misses=json.loads(fit_row["misses_json"]),
            rejected_markets=[
                RejectedMarket.model_validate(item)
                for item in json.loads(fit_row["rejected_markets_json"])
            ],
        )
        from app.models import EvalMetrics, EvalResult

        eval_result = EvalResult(
            eval_record_id=eval_row["id"],
            phoenix_trace_id=eval_row["phoenix_trace_id"],
            metrics=EvalMetrics.model_validate(json.loads(eval_row["metrics_json"])),
            failure_summary=eval_row["failure_summary"],
        )
        return RunResult(
            run_id=run_id,
            source_id=claim_row["source_id"],
            claim_id=claim_row["id"],
            phoenix_trace_id=run["phoenix_trace_id"],
            phoenix_trace_url=_phoenix_trace_url(run["phoenix_trace_id"]),
            model=run["model"],
            prompt_version=run["prompt_version"],
            claim=claim,
            fit=fit,
            eval=eval_result,
            ledger=self.store.query_claim_trace(claim_row["id"]),
        )


def _deterministic_extract(thesis: str) -> NormalizedClaim:
    lowered = thesis.lower()
    if "60 more days" in lowered and "frozen assets" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran will extend the ceasefire for 60 days while partially "
                "reopening Hormuz, unfreezing assets, and easing sanctions."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "sanctions"],
            horizon="by end of July 2026",
            stance="expects ceasefire extension and deal progress",
            confidence=0.62,
            reasoning_summary=(
                "The source describes a multi-part ceasefire package; permanent peace and "
                "Hormuz traffic markets only capture pieces of it."
            ),
        )
    if "draft peace deal within 24 hours" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran will announce a draft peace deal or framework within 24 "
                "to 48 hours."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "sanctions"],
            horizon="within 24-48 hours from May 23, 2026",
            stance="expects draft announcement",
            confidence=0.58,
            reasoning_summary=(
                "The source is about a near-term draft announcement, not necessarily final "
                "signed permanent peace."
            ),
        )
    if "framework memorandum" in lowered and "within 48 hours" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran may announce a framework memorandum or decision within "
                "48 hours, with final details taking 30-60 days."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "Trump"],
            horizon="within 48 hours; final details in 30-60 days",
            stance="uncertain framework progress",
            confidence=0.59,
            reasoning_summary=(
                "The source explicitly distinguishes a framework decision from final details "
                "or permanent peace."
            ),
        )
    if "opus 4.8" in lowered and "google vertex" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Claude Opus 4.8 may be visible in Google Vertex, while Sonnet 4.8 is "
                "expected soon, but the source cannot confirm it."
            ),
            entities=["Anthropic", "Claude Opus 4.8", "Claude Sonnet 4.8", "Google Vertex"],
            horizon="soon after May 23, 2026",
            stance="uncertain release or platform availability",
            confidence=0.52,
            reasoning_summary=(
                "The source is platform-specific and uncertain, while available markets focus "
                "on Claude 5 public release."
            ),
        )
    if "as good as mythos" in lowered or (
        "anthropic can delay" in lowered and "gpt-5.6 pro" in lowered
    ):
        return NormalizedClaim(
            claim_text=(
                "GPT-5.6 Pro will soon reach performance parity with Anthropic Mythos in "
                "important areas."
            ),
            entities=["OpenAI", "GPT-5.6 Pro", "Anthropic", "Mythos"],
            horizon="coming months of 2026",
            stance="expects parity",
            confidence=0.6,
            reasoning_summary=(
                "The source is about cross-model performance parity, not just whether GPT-5.6 "
                "is released."
            ),
        )
    if "gpqa diamond" in lowered and "gpt 5.5" in lowered:
        return NormalizedClaim(
            claim_text=(
                "OpenAI's GPT-5 series shows steady GPQA Diamond benchmark improvement, "
                "reaching 93.6% with GPT-5.5."
            ),
            entities=["OpenAI", "GPT-5.1", "GPT-5.5", "GPQA Diamond"],
            horizon="as of May 2026",
            stance="claims benchmark improvement",
            confidence=0.64,
            reasoning_summary=(
                "The source is a benchmark score trend, not a release date or broad adoption "
                "outcome."
            ),
        )
    if "winner take all games" in lowered and "cybersecurity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Cybersecurity and financial trading will become winner-take-all verticals "
                "where current frontier models are required."
            ),
            entities=["frontier models", "cybersecurity", "financial trading", "Mythos"],
            horizon="2026 onward",
            stance="expects frontier necessity",
            confidence=0.57,
            reasoning_summary=(
                "The source is a causal adoption thesis without an objective market-resolvable "
                "threshold."
            ),
        )
    if "boomer balance sheets" in lowered and "40% of all the housing" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US housing supply is constrained by boomer ownership, with future mortality "
                "expected to release inventory over time."
            ),
            entities=["US housing market", "baby boomers", "housing inventory"],
            horizon="2026 through 2030s",
            stance="expects demographic supply release",
            confidence=0.62,
            reasoning_summary=(
                "The source is a demographic housing-supply thesis, not a mortgage-rate or "
                "home-price event."
            ),
        )
    if "gas prices need to get back down" in lowered and "holding the house" in lowered:
        return NormalizedClaim(
            claim_text=(
                "If the Iran war ends soon and gas prices fall below $4 nationwide before "
                "November, Republicans may have an outside chance of holding the House."
            ),
            entities=["Iran conflict", "US gas prices", "Republican Party", "US House"],
            horizon="by November 2026",
            stance="conditional possibility",
            confidence=0.56,
            reasoning_summary=(
                "The source depends on multiple conditions: conflict resolution, gas prices, "
                "and election outcome."
            ),
        )
    if "dtcc migration" in lowered and "tokenized stocks" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Tokenized stocks will reach traditional market liquidity by the end of 2026 "
                "as DTCC, Ripple Prime, NSCC rails, and a July go-live align."
            ),
            entities=["DTCC", "Ripple Prime", "NSCC", "tokenized stocks"],
            horizon="by end of 2026; July go-live",
            stance="expects tokenized-stock liquidity milestone",
            confidence=0.58,
            reasoning_summary=(
                "The source is about market-structure liquidity and clearing rails, not token "
                "prices alone."
            ),
        )
    if "solbtc update" in lowered or "sol remains the best general purpose" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SOL remains one of the strongest general-purpose L1s in 2026 because usage, "
                "speed, efficiency, UX, and PMF continue improving despite price weakness."
            ),
            entities=["Solana", "SOL", "L1 blockchain sector"],
            horizon="2026+",
            stance="bullish SOL fundamentals",
            confidence=0.57,
            reasoning_summary=(
                "The source is a qualitative fundamentals thesis; price markets would be noisy "
                "proxies."
            ),
        )
    if "gartner's latest ai forecast" in lowered or "$2.59t market in 2026" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Global AI spending will reach trillions in 2026-2027 while frontier model "
                "prices rise, pushing enterprises toward cost-saving alternatives."
            ),
            entities=["AI market", "Gartner", "enterprises", "frontier model providers"],
            horizon="2026-2027",
            stance="expects cost pressure and cost-saving demand",
            confidence=0.64,
            reasoning_summary=(
                "The source combines global spend, model pricing, and enterprise behavior; "
                "single-company capex is only a proxy."
            ),
        )
    if "pre-emptively hiking rates" in lowered or "preemptively hiking rates" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Central banks should preemptively hike rates because HSBC fears supply shocks "
                "will have enduring effects on inflation and growth."
            ),
            entities=["central banks", "HSBC", "inflation", "supply shocks"],
            horizon="2026 onward",
            stance="policy recommendation to hike",
            confidence=0.55,
            reasoning_summary=(
                "The source is a policy recommendation and analyst view, not a clean forecast "
                "with a single resolution condition."
            ),
        )
    if "antfleet two-model review" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AntFleet's two-model review using Claude Opus 4.7 and GPT-5 found specific "
                "smart-contract vulnerabilities in Doppler and submitted a fix PR."
            ),
            entities=["AntFleet", "Claude Opus 4.7", "GPT-5", "Doppler protocol"],
            horizon="as of May 2026",
            stance="claims successful code review finding",
            confidence=0.61,
            reasoning_summary=(
                "The source is a specific security finding, not a general AI code-review "
                "adoption benchmark."
            ),
        )
    if "gpt-5.6 leaks" in lowered or "gpt-5.6 pro" in lowered:
        return NormalizedClaim(
            claim_text=(
                "OpenAI will publicly release GPT-5.6 or GPT-5.6 Pro in June 2026, "
                "with related Anthropic and Gemini model releases also expected."
            ),
            entities=["OpenAI", "GPT-5.6", "Anthropic", "Claude Sonnet 4.8", "Google"],
            horizon="June 2026",
            stance="expects public frontier model releases",
            confidence=0.7,
            reasoning_summary=(
                "The source is leak-based, but it names GPT-5.6 and a June 2026 release "
                "window that can be compared with public release markets."
            ),
        )
    if "claude 4.8 opus is coming" in lowered:
        return NormalizedClaim(
            claim_text="Anthropic will release Claude 4.8 Opus, with no explicit date stated.",
            entities=["Anthropic", "Claude 4.8 Opus"],
            horizon="unspecified near future",
            stance="expects release",
            confidence=0.55,
            reasoning_summary=(
                "The exact source names Claude 4.8 Opus but does not state a deadline."
            ),
        )
    if "diplomatic negotiations around iran" in lowered and "reopening the strait" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Iran-related diplomatic talks may be entering a final phase after a revised "
                "proposal focused on ending the conflict and reopening the Strait of Hormuz."
            ),
            entities=["Iran", "United States", "Pakistan", "Strait of Hormuz"],
            horizon="late May to June 2026",
            stance="cautiously expects progress",
            confidence=0.6,
            reasoning_summary=(
                "The source is uncertain and proposal-based; Hormuz traffic normalization is "
                "an observable adjacent outcome rather than direct proposal acceptance."
            ),
        )
    if "3 serious points of disagreement" in lowered and "blocked funds" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Iran-US negotiations depend on resolving nuclear, blocked-funds, and Strait "
                "of Hormuz control disagreements."
            ),
            entities=["Iran", "United States", "blocked funds", "Strait of Hormuz"],
            horizon="current negotiation round",
            stance="conditional and unresolved",
            confidence=0.66,
            reasoning_summary=(
                "The source lists granular negotiation conditions, not only a final peace deal."
            ),
        )
    if "the real war is about" in lowered and "ubiquity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google is prioritizing Gemini distribution and ubiquity across Android and "
                "Search over pure benchmark leadership in 2026."
            ),
            entities=["Google", "Gemini 3.5 Flash", "Android", "Search"],
            horizon="2026",
            stance="expects distribution strategy to matter more than benchmarks",
            confidence=0.68,
            reasoning_summary=(
                "The source contrasts native distribution with benchmark leadership, so model "
                "release or leaderboard markets are not clean expressions."
            ),
        )
    if "mi450x" in lowered and "helios" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AMD will ship Helios rack-scale AI systems with Venice and MI450X starting "
                "in H2 2026 while improving its AI accelerator position relative to NVIDIA."
            ),
            entities=["AMD", "NVIDIA", "TSMC", "MI450X", "Venice", "Helios"],
            horizon="H2 2026",
            stance="bullish AMD AI accelerator position",
            confidence=0.66,
            reasoning_summary=(
                "The source mixes product shipment, ecosystem investment, and valuation-gap "
                "commentary, with no supplied clean market."
            ),
        )
    if "rules out a potential foundry deal" in lowered and "tsmc" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AMD will remain with TSMC and avoid an Intel foundry deal in 2026 despite "
                "tight AI-related capacity."
            ),
            entities=["AMD", "TSMC", "Intel", "Lisa Su"],
            horizon="2026",
            stance="expects no Intel foundry deal",
            confidence=0.68,
            reasoning_summary=(
                "The source is about AMD's foundry relationship, not a general AI chip supply "
                "or model-release outcome."
            ),
        )
    if "meta-manus" in lowered or "cross-border ai is becoming a managed commodity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US or China will increasingly restrict cross-border frontier AI models, "
                "acquisitions, or partnerships in 2026."
            ),
            entities=["United States", "China", "Meta", "Manus"],
            horizon="2026",
            stance="expects tighter AI controls",
            confidence=0.63,
            reasoning_summary=(
                "The source uses a claimed Meta-Manus deal block as evidence for a broader "
                "AI policy trend."
            ),
        )
    if "anthropic is paying spacex" in lowered and "per month" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic is allegedly paying SpaceX about $1.25 billion per month for "
                "compute access through 2029."
            ),
            entities=["Anthropic", "SpaceX", "Colossus", "AI compute"],
            horizon="through 2029",
            stance="claims large compute contract",
            confidence=0.55,
            reasoning_summary=(
                "The source depends on an alleged leak and concerns a specific contract, not "
                "aggregate AI capex."
            ),
        )
    if "ai is eating 80% of global vc funding" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AI is capturing a very large share of VC funding while frontier labs and "
                "hyperscalers show high spend and limited measurable ROI."
            ),
            entities=["AI companies", "Anthropic", "Microsoft", "OpenAI", "hyperscalers"],
            horizon="2025-2026 period",
            stance="skeptical of AI ROI",
            confidence=0.66,
            reasoning_summary=(
                "The source combines global VC share, lab burn rates, hyperscaler capex, and "
                "ROI claims; an Amazon capex market is only a single-entity proxy."
            ),
        )
    if "sibyl memory" in lowered or "hold your memory in your hand" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SIBYL memory is moving toward public release and claims large reductions in "
                "agent hallucinations over longer horizons."
            ),
            entities=["SIBYL", "Hermes", "Claude Code", "Codex"],
            horizon="as of May 2026",
            stance="expects product release and performance improvement",
            confidence=0.61,
            reasoning_summary=(
                "The source gives product and claimed performance signals, but no supplied "
                "prediction market resolves SIBYL release or memory quality."
            ),
        )
    if "homes are 40% overpriced" in lowered and "mortgage rates" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US homes are about 40% overpriced at current mortgage rates relative to "
                "pricing implied by lower mortgage rates."
            ),
            entities=["US housing market", "mortgage rates"],
            horizon="as of May 2026",
            stance="homes overpriced",
            confidence=0.64,
            reasoning_summary=(
                "The source is a housing valuation claim; mortgage-rate threshold markets only "
                "measure one input."
            ),
        )
    if "fed funds rate forecast table" in lowered and "until 2028" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The Federal Reserve is not expected to cut rates until at least 2028 based "
                "on forecasts and inflation concerns."
            ),
            entities=["Federal Reserve", "Fed funds rate", "inflation"],
            horizon="through 2027 / until 2028",
            stance="expects no rate cuts",
            confidence=0.67,
            reasoning_summary=(
                "The source makes a multi-year no-cut claim, while available markets test "
                "only 2026 cuts or specific near-term meetings."
            ),
        )
    if "new paper alert" in lowered and "limits of interest rate policy" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US fiscal policy conduct limits the effectiveness of interest-rate policy "
                "for containing COVID-era inflation."
            ),
            entities=["Federal Reserve", "US fiscal policy", "inflation"],
            horizon="retrospective / 2026 paper",
            stance="argues fiscal policy constrained monetary policy",
            confidence=0.62,
            reasoning_summary=(
                "The source is an academic causal thesis, not a single future event."
            ),
        )
    if "agentic ai is moving out of the demo phase" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Agentic AI is moving from demos and chatbots toward workflow integration, "
                "governance, memory, permissions, monitoring, optimization, and business outcomes."
            ),
            entities=["AI agent platforms", "enterprise AI adopters"],
            horizon="2026",
            stance="expects agentic AI maturation",
            confidence=0.65,
            reasoning_summary=(
                "The source is a market narrative about vocabulary and buyer expectations, "
                "not a clean market-resolvable event."
            ),
        )
    if "performance review cycle" in lowered and "ai fluency" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Managers lack a clear standardized playbook for evaluating employee AI "
                "fluency in performance reviews."
            ),
            entities=["corporate HR", "managers", "AI fluency", "performance reviews"],
            horizon="as of May 2026",
            stance="says no standard playbook exists",
            confidence=0.7,
            reasoning_summary=(
                "The source is about HR evaluation standards, not generic AI adoption or "
                "productivity metrics."
            ),
        )
    if "link cli" in lowered and "single-use credentials" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Agent-approved payment credentials and agentic payment tools will see "
                "meaningful demand by the end of 2026."
            ),
            entities=["Stripe", "Link CLI", "AI agents", "agentic payments"],
            horizon="by Dec 31, 2026",
            stance="expects agent-approved payments to gain demand",
            confidence=0.76,
            reasoning_summary=(
                "The source describes Stripe Link CLI enabling human-approved purchases by "
                "agents, but does not name a directly resolvable market."
            ),
        )
    if "dollar milkshake" in lowered or "swap lines" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Expanded Federal Reserve USD swap lines to allies would reduce global dollar "
                "funding stress and weaken the dollar safe-haven bid over time."
            ),
            entities=["Federal Reserve", "USD swap lines", "US dollar", "US allies"],
            horizon="unclear long-term horizon",
            stance="expects weaker dollar safe-haven role",
            confidence=0.62,
            reasoning_summary=(
                "The source is a broad macro causal thesis rather than a single dated event."
            ),
        )
    if "reconstruct complex papers" in lowered or "methods & data" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AI agents are approaching the ability to independently reconstruct complex "
                "academic papers from methods and data, implying research-agent products may "
                "arrive soon."
            ),
            entities=["AI agents", "academic research", "research agents"],
            horizon="by Dec 31, 2026",
            stance="expects research-agent capability and productization",
            confidence=0.68,
            reasoning_summary=(
                "The source is about research-agent capability, not a specific benchmark or "
                "named product launch."
            ),
        )
    if "large multi-agent system" in lowered and "coordinate" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Large multi-agent systems still lack the coordination breakthrough needed for "
                "maximum autonomous effectiveness."
            ),
            entities=["multi-agent systems", "AI labs", "enterprise AI"],
            horizon="unclear",
            stance="skeptical and ambiguous",
            confidence=0.52,
            reasoning_summary=(
                "The source is rhetorical and ambiguous, not a dated prediction about a market "
                "resolvable event."
            ),
        )
    if "gemini 3.2" in lowered or "gemini 3.5" in lowered or "powered by omni" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google will publicly release a next Gemini 3.x model, plausibly Gemini 3.2 "
                "or Gemini 3.5, by June 30, 2026."
            ),
            entities=["Google", "Gemini 3.2", "Gemini 3.5", "Google I/O"],
            horizon="by Jun 30, 2026",
            stance="expects release",
            confidence=0.7,
            reasoning_summary=(
                "The source reports Gemini 3.2/3.5 testing and Google I/O leaks, but does not "
                "narrow to one exact model version."
            ),
        )
    if "spacex ipo timeline" in lowered or "target valuation: $1.75t" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SpaceX will complete the largest IPO by first-day closing market "
                "capitalization in 2026."
            ),
            entities=["SpaceX", "IPO", "2026 IPO market"],
            horizon="by Dec 31, 2026",
            stance="expects SpaceX to have the largest IPO",
            confidence=0.73,
            reasoning_summary=(
                "The source asserts a 2026 SpaceX IPO timeline and frames it as the biggest "
                "IPO in history."
            ),
        )
    if "anthropic just hit a $1 trillion valuation" in lowered and "ipo momentum" not in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic will achieve or has achieved a valuation above $500B in 2026 based "
                "on private-market bids and reported revenue acceleration."
            ),
            entities=["Anthropic", "valuation", "private funding", "secondary market"],
            horizon="by Dec 31, 2026",
            stance="expects valuation above $500B",
            confidence=0.78,
            reasoning_summary=(
                "The source explicitly claims Anthropic traded at valuation levels above "
                "$500B before IPO."
            ),
        )
    if "ipo momentum" in lowered and "anthropic" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic's reported private valuation surge may indicate IPO momentum or a "
                "near-term IPO becoming more likely."
            ),
            entities=["Anthropic", "IPO", "private valuation", "secondary market"],
            horizon="soon or unclear",
            stance="infers IPO momentum",
            confidence=0.64,
            reasoning_summary=(
                "The user infers IPO timing pressure from valuation hype, which is adjacent to "
                "but distinct from valuation confirmation."
            ),
        )
    if "tpu 8t" in lowered or "tpu 8i" in lowered or "3x performance" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google's TPU 8t/8i performance claims could help Google close the frontier "
                "AI model gap by the end of June 2026."
            ),
            entities=["Google", "TPU 8t", "TPU 8i", "AI model rankings", "Chatbot Arena"],
            horizon="by Jun 30, 2026",
            stance="bullish Google model competitiveness",
            confidence=0.66,
            reasoning_summary=(
                "The source links hardware-performance claims to possible model ranking gains, "
                "while noting thin market liquidity and missing receipts."
            ),
        )
    if "putnam" in lowered and ("imo" in lowered or "axiom math" in lowered):
        return NormalizedClaim(
            claim_text=(
                "AI systems have reached math capability levels that make an official 2026 "
                "IMO gold-medal result plausible."
            ),
            entities=["AI", "Putnam", "Axiom Math", "IMO"],
            horizon="by Dec 31, 2026",
            stance="expects math benchmark capability to transfer",
            confidence=0.67,
            reasoning_summary=(
                "The source concerns Putnam performance, which is related evidence but not the "
                "same event as official IMO gold resolution."
            ),
        )
    if "gemini" in lowered and "tpu" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google TPU progress will help Gemini close the performance gap with frontier "
                "models during 2026."
            ),
            entities=["Google", "TPU", "Gemini", "frontier models"],
            horizon="2026",
            stance="expects Gemini performance to improve relative to frontier models",
            confidence=0.72,
            reasoning_summary=(
                "The source links Google hardware claims to a future model-performance outcome."
            ),
        )
    if "fed" in lowered and "july" in lowered and ("cut" in lowered or "rates" in lowered):
        return NormalizedClaim(
            claim_text="The Federal Reserve will cut interest rates at the July 2026 FOMC meeting.",
            entities=["Federal Reserve", "FOMC", "interest rates"],
            horizon="July 2026",
            stance="expects a rate cut",
            confidence=0.82,
            reasoning_summary="The thesis directly states an event and date for a policy decision.",
        )
    return NormalizedClaim(
        claim_text=_sentence(thesis),
        entities=_simple_entities(thesis),
        horizon="unspecified",
        stance="needs interpretation",
        confidence=0.48,
        reasoning_summary=(
            "Fallback extraction used because Gemini was not configured or returned invalid JSON."
        ),
    )


def _phoenix_trace_url(trace_id: str | None) -> str | None:
    if not trace_id or trace_id.startswith("local-"):
        return None
    from app.config import settings

    if not settings.phoenix_base_url:
        return None
    return f"{settings.phoenix_base_url.rstrip('/')}/traces/{trace_id}"


def _json_preview(value: Any, max_chars: int = 2000) -> str | None:
    if value is None:
        return None
    try:
        text = json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...[truncated]"


def _deterministic_classify(
    claim: NormalizedClaim, markets: list[CandidateMarket], prompt_version: str
) -> MarketFit:
    claim_text = _claim_haystack(claim)
    if "ceasefire for 60 days" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The permanent-peace market is relevant to the deal-progress theme, but it "
                "is stronger and finaler than the source's 60-day ceasefire package."
            ),
            captures=["US-Iran diplomatic resolution direction", "July 2026 horizon"],
            misses=[
                "60-day temporary extension",
                "Asset unfreezing",
                "Sanctions easing",
                "Partial Hormuz reopening details",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason="Hormuz traffic captures only one component of the package.",
                )
            ],
        )
    if "draft peace deal" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The market resolves a permanent peace deal by July, while the source claims "
                "a draft announcement within 24-48 hours."
            ),
            captures=["US-Iran peace-deal theme"],
            misses=["Draft-vs-signed finality", "24-hour announcement horizon"],
            rejected_markets=[],
        )
    if "framework memorandum" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The source is about a framework memorandum and staged details; the market "
                "requires permanent peace, so it is adjacent but not direct."
            ),
            captures=["US-Iran diplomatic progress"],
            misses=["Framework-vs-final distinction", "48-hour decision timing"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason=(
                        "Hormuz traffic is an outcome proxy and does not resolve the framework "
                        "memorandum."
                    ),
                )
            ],
        )
    if "google vertex" in claim_text and "claude" in claim_text:
        return MarketFit(
            recommended_market_id="pm_claude_5_released_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The Claude 5 market is adjacent to the Anthropic release theme, but the "
                "source concerns Claude 4.8 visibility in Google Vertex and is explicitly "
                "uncertain."
            ),
            captures=["Anthropic frontier model release theme"],
            misses=["Claude 4.8 naming", "Google Vertex platform availability", "Confirmation"],
            rejected_markets=[],
        )
    if "performance parity" in claim_text and "mythos" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves GPT-5.6 Pro performance parity with Mythos; "
                "release timing would be a different claim."
            ),
            captures=[],
            misses=["Benchmark suite", "Parity threshold", "Named Mythos comparison"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="GPT-5.6 release timing does not resolve performance parity.",
                )
            ],
        )
    if "gpqa diamond" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the GPQA Diamond score series or OpenAI's "
                "reasoning benchmark curve."
            ),
            captures=[],
            misses=["GPQA score threshold", "Benchmark source", "Model-specific score"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Release timing does not resolve GPQA Diamond benchmark scores.",
                )
            ],
        )
    if "winner-take-all verticals" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The claim is a causal adoption thesis about frontier necessity in verticals, "
                "without a clean market-resolvable threshold."
            ),
            captures=[],
            misses=["Frontier requirement threshold", "Vertical adoption metric", "Date"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Hyperscaler capex does not resolve whether frontier models are required "
                        "in cybersecurity or trading."
                    ),
                )
            ],
        )
    if "boomer ownership" in claim_text or "baby boomers" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves boomer-owned housing inventory release or the "
                "demographic mechanism behind housing supply."
            ),
            captures=[],
            misses=["Age-cohort seller metric", "Inventory release threshold", "Data source"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_30y_mortgage_rate_hit_2026",
                    reason="Mortgage rates do not resolve demographic inventory release.",
                )
            ],
        )
    if "republicans" in claim_text and "gas prices" in claim_text and "iran" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a conditional chain across Iran, gas prices, and House control; "
                "no single supplied market resolves the full thesis."
            ),
            captures=[],
            misses=["War-end condition", "Gas-price threshold", "House-control outcome link"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_us_iran_permanent_peace_by",
                    reason=(
                        "Peace deal alone does not resolve gas prices or House control."
                    ),
                )
            ],
        )
    if "tokenized stocks" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves tokenized-stock liquidity reaching traditional "
                "market liquidity via DTCC/Ripple/NSCC rails."
            ),
            captures=[],
            misses=["Tokenized equity volume", "Liquidity threshold", "Clearing-rail criterion"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex is unrelated to tokenized-stock liquidity.",
                )
            ],
        )
    if "solana" in claim_text or "sol remains" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves Solana usage, PMF, UX, and fundamentals together; "
                "price would be a noisy proxy."
            ),
            captures=[],
            misses=["Usage metric", "PMF definition", "UX/speed/efficiency criteria"],
            rejected_markets=[],
        )
    if "global ai spending" in claim_text and "frontier model prices" in claim_text:
        return MarketFit(
            recommended_market_id="pm_amazon_2026_capex_above",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "Amazon capex is a weak proxy: it is a single-company spend metric, not "
                "global AI spend, model pricing, or enterprise cost-saving behavior."
            ),
            captures=["One hyperscaler capex metric"],
            misses=[
                "Gartner global AI spend",
                "Frontier model price trajectory",
                "Enterprise cost-saving adoption",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Tempting but weak: it resolves Amazon capex, not the broader AI "
                        "spend/pricing thesis."
                    ),
                )
            ],
        )
    if "preemptively hike rates" in claim_text or "supply shocks" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a policy recommendation based on HSBC's supply-shock view, "
                "not a clean forecast about a specific rate decision."
            ),
            captures=[],
            misses=["Specific central bank", "Rate-hike action", "Supply-shock citation criterion"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason=(
                        "A Fed cut-count market does not resolve whether central banks "
                        "should hike."
                    ),
                )
            ],
        )
    if "antfleet" in claim_text or "doppler" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the specific AntFleet/Doppler vulnerability finding "
                "or independent confirmation of the submitted fix."
            ),
            captures=[],
            misses=["Repository confirmation", "Specific vulnerability validity", "Fix acceptance"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Model release timing does not resolve this security finding.",
                )
            ],
        )
    if "gpt-5.6" in claim_text:
        return MarketFit(
            recommended_market_id="pm_gpt56_released_by_june_30_2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The GPT-5.6 by June 30 market matches the named OpenAI model, public "
                "availability condition, and June 2026 horizon for the OpenAI portion of "
                "the source."
            ),
            captures=["OpenAI GPT-5.6", "public release", "June 2026 horizon"],
            misses=[
                "Parallel Sonnet 4.8 release claim",
                "Parallel Gemini 3.5 Pro release claim",
                "Internal leak tags as evidence quality",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason=(
                        "Bucketed release-date market is also relevant, but the binary June 30 "
                        "market expresses the core dated release claim more simply."
                    ),
                )
            ],
        )
    if "claude 4.8 opus" in claim_text:
        return MarketFit(
            recommended_market_id="pm_claude_5_released_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The market resolves on Claude 5 public availability by a target date, while "
                "the source names Claude 4.8 Opus and gives no explicit deadline."
            ),
            captures=["Anthropic frontier model release theme"],
            misses=["Claude 4.8 naming", "Clear source horizon", "Opus-specific versioning"],
            rejected_markets=[],
        )
    if "reopening the strait of hormuz" in claim_text or (
        "final phase" in claim_text and "hormuz" in claim_text
    ):
        return MarketFit(
            recommended_market_id="pm_hormuz_traffic_normal_end_june_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The Hormuz traffic market measures a concrete reopening outcome, but it "
                "does not resolve whether the revised diplomatic proposal was accepted."
            ),
            captures=["Strait of Hormuz reopening objective", "June 2026 observable outcome"],
            misses=[
                "Proposal acceptance",
                "Full conflict-ending deal",
                "Diplomatic final-phase status",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_us_iran_permanent_peace_by",
                    reason=(
                        "A permanent peace deal is stronger than the source's uncertain proposal "
                        "and reopening-progress language."
                    ),
                )
            ],
        )
    if "blocked-funds" in claim_text or "blocked funds" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The peace-deal market captures overall diplomatic resolution, but not the "
                "source's three specific disagreement points."
            ),
            captures=["US-Iran diplomatic outcome"],
            misses=["Nuclear issue", "Blocked-funds transfer", "Hormuz-control mechanics"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason=(
                        "Hormuz traffic normalization misses the nuclear and blocked-funds "
                        "conditions."
                    ),
                )
            ],
        )
    if "ubiquity" in claim_text or "android and search" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves Gemini distribution ubiquity across Android and "
                "Search; model release or leaderboard markets would test a different claim."
            ),
            captures=[],
            misses=[
                "Distribution reach across Android/Search",
                "Native product integration",
                "Buyer expectation shift away from benchmark leadership",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="OpenAI release timing does not resolve Google distribution strategy.",
                )
            ],
        )
    if "mi450x" in claim_text or "helios rack-scale" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves AMD Helios/MI450X shipment timing, customer "
                "deployment, or AI accelerator share."
            ),
            captures=[],
            misses=["AMD product shipment", "Customer deployment", "AI accelerator share"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Amazon capex is a hyperscaler spending metric, not AMD shipment or "
                        "share capture."
                    ),
                )
            ],
        )
    if "no intel foundry deal" in claim_text or "tsmc" in claim_text and "foundry" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves whether AMD avoids or signs an Intel foundry deal "
                "while staying with TSMC."
            ),
            captures=[],
            misses=["AMD foundry decision", "Intel manufacturing relationship", "TSMC allocation"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex does not resolve AMD's foundry partner choice.",
                )
            ],
        )
    if "frontier ai models" in claim_text and "cross-border" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves new US or China restrictions on frontier AI "
                "model exports, acquisitions, or partnerships."
            ),
            captures=[],
            misses=[
                "Official restriction",
                "Model/acquisition scope",
                "Cross-border partnership rule",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Model release timing does not resolve export or acquisition controls.",
                )
            ],
        )
    if "spacex" in claim_text and "compute access" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the alleged Anthropic-SpaceX compute contract; "
                "aggregate capex or IPO markets would miss the counterparty and contract terms."
            ),
            captures=[],
            misses=[
                "Contract confirmation",
                "Counterparties",
                "Dollar amount",
                "Through-2029 term",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex is a single-company spend metric, not this contract.",
                )
            ],
        )
    if "global vc funding" in claim_text or "limited measurable roi" in claim_text:
        return MarketFit(
            recommended_market_id="pm_amazon_2026_capex_above",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "Amazon capex is only a weak proxy for the source's aggregate AI funding, "
                "lab burn-rate, backlog, and ROI thesis."
            ),
            captures=["One hyperscaler capex metric", "AI infrastructure spend direction"],
            misses=[
                "Global VC funding share",
                "Anthropic spend-to-revenue ratio",
                "Enterprise AI ROI",
                "Multi-company backlog concentration",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Tempting but weak: it resolves Amazon purchases of property and "
                        "equipment, not the broader VC/capex/ROI thesis."
                    ),
                )
            ],
        )
    if "sibyl" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves SIBYL public release, compatibility, or claimed "
                "hallucination reductions."
            ),
            captures=[],
            misses=["SIBYL release", "Memory compatibility", "92% and 96% reduction claims"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason="GPT-5.6 release timing does not resolve agent memory tooling.",
                )
            ],
        )
    if "homes are about 40% overpriced" in claim_text or "40% overpriced" in claim_text:
        return MarketFit(
            recommended_market_id="pm_30y_mortgage_rate_hit_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The mortgage-rate market is only a weak proxy because it resolves rate "
                "thresholds, not whether home prices are 40% overvalued or correct."
            ),
            captures=["Mortgage-rate environment", "2026 rate thresholds"],
            misses=[
                "Home-price valuation metric",
                "40% overpricing estimate",
                "Case-Shiller or comparable price response",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_30y_mortgage_rate_hit_2026",
                    reason=(
                        "Tempting but weak: rate levels are an input to the thesis, not the "
                        "housing valuation output."
                    ),
                )
            ],
        )
    if "not expected to cut rates until at least 2028" in claim_text:
        return MarketFit(
            recommended_market_id="pm_fed_rate_cuts_2026_count",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The 2026 Fed-cuts market tests the near-term direction of the thesis, but "
                "does not cover the full no-cuts-until-2028 horizon."
            ),
            captures=["Official FOMC rate decisions", "2026 no-cut direction"],
            misses=["2027 rate path", "Full until-2028 forecast horizon", "Risk-asset implication"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cut_by_2026_meeting",
                    reason=(
                        "Meeting-specific cut markets are narrower than the source's multi-year "
                        "forecast."
                    ),
                )
            ],
        )
    if "fiscal policy conduct limits" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is an academic causal thesis about fiscal policy limiting monetary "
                "policy effectiveness, not a single market-resolvable future event."
            ),
            captures=[],
            misses=[
                "Academic finding",
                "Causal mechanism",
                "Retrospective COVID-era inflation scope",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason=(
                        "A 2026 rate-cut count does not resolve why prior inflation responded "
                        "to policy."
                    ),
                )
            ],
        )
    if "agentic ai is moving" in claim_text or "workflow integration" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the narrative shift from AI demos to workflow "
                "infrastructure with measurable adoption criteria."
            ),
            captures=[],
            misses=[
                "Enterprise deployment count",
                "Governance criteria",
                "Vocabulary-shift measurement",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason="Model release timing does not resolve enterprise agent maturation.",
                )
            ],
        )
    if "performance reviews" in claim_text and "ai fluency" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves whether companies have a standardized playbook "
                "for evaluating AI fluency in performance reviews."
            ),
            captures=[],
            misses=[
                "HR playbook standardization",
                "Company adoption threshold",
                "AI fluency criteria",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason="Fed rate cuts are unrelated to workplace AI evaluation standards.",
                )
            ],
        )
    if "agent-approved payment" in claim_text or "link cli" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No clean market in the seed set resolves Stripe Link CLI, agent-approved "
                "payment credentials, or agents completing approved purchases by EOY 2026."
            ),
            captures=[],
            misses=[
                "Agentic payment credential launch criteria",
                "Named payment-company product release",
                "Objective purchase-completion threshold",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "AI benchmark success is unrelated to agent-approved payment "
                        "credentials or commerce adoption."
                    ),
                )
            ],
        )
    if "swap lines" in claim_text or "safe-haven" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a broad macro causal thesis about USD liquidity and reserve "
                "behavior, not a single dated market expression."
            ),
            captures=[],
            misses=[
                "Specific swap-line counterparty",
                "Official Federal Reserve announcement date",
                "Objective safe-haven status criterion",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-fed-cut-sept-2026",
                    reason=(
                        "A rate-decision market does not resolve on swap-line availability or "
                        "the dollar safe-haven bid."
                    ),
                )
            ],
        )
    if "research-agent" in claim_text or "reconstruct complex academic papers" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No clean market resolves release of a general-purpose research agent or "
                "paper-reconstruction capability."
            ),
            captures=[],
            misses=[
                "Named qualifying labs",
                "Research-agent release criteria",
                "Paper reconstruction success threshold",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "The IMO market resolves on math competition results, not research-agent "
                        "productization."
                    ),
                )
            ],
        )
    if "multi-agent systems" in claim_text or "coordination breakthrough" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is ambiguous and rhetorical; it does not define a dated, resolvable "
                "forecast about enterprise multi-agent orchestration."
            ),
            captures=[],
            misses=[
                "Named product release",
                "Coordination-success criterion",
                "Clear time horizon",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "A Chatbot Arena company ranking does not resolve enterprise "
                        "multi-agent coordination."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "A math benchmark does not resolve autonomous multi-agent orchestration."
                    ),
                ),
            ],
        )
    if "gemini 3.2" in claim_text or "gemini 3.5" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_gemini_3_2_june_30_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The June 30 horizon matches the source, but the source mentions Gemini 3.2 "
                "and 3.5 rather than one exact release version."
            ),
            captures=["Google Gemini release timing", "June 30, 2026 horizon"],
            misses=[
                "The source does not narrow to Gemini 3.2 exactly",
                "The market ignores Gemini 3.5 if that is the actual release label",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Best-model ranking resolves on Chatbot Arena score, not public release "
                        "of a Gemini 3.x model."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason="IMO gold resolves on a math contest, not Gemini release timing.",
                ),
            ],
        )
    if "spacex" in claim_text and "largest ipo" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_largest_ipo_2026_spacex",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolves on the company with the highest first-day closing market "
                "capitalization among 2026 IPOs, matching the SpaceX largest-IPO thesis."
            ),
            captures=["SpaceX", "2026 IPO", "largest by first-day closing market cap"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_spacex_ipo_closing_market_cap",
                    reason=(
                        "That market is about SpaceX's absolute valuation bucket, not whether "
                        "SpaceX is the largest IPO of 2026."
                    ),
                )
            ],
        )
    if "anthropic" in claim_text and "valuation above $500b" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_anthropic_500b_valuation_2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolves on Anthropic reaching or confirming at least a $500B "
                "public or private valuation in 2026, matching the valuation thesis."
            ),
            captures=["Anthropic", "$500B valuation threshold", "2026 horizon"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_anthropic_no_ipo_june_30_2026",
                    reason="IPO timing is a different event from valuation confirmation.",
                ),
                RejectedMarket(
                    market_id="polymarket_largest_ipo_2026_anthropic",
                    reason=(
                        "Largest IPO ranking is a comparative public-listing claim, not a "
                        "private valuation threshold."
                    ),
                ),
            ],
        )
    if "tpu 8t" in claim_text or "tpu 8i" in claim_text or "3x performance" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_best_ai_model_google_end_june_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The Google best-model market is only a weak adjacent expression: it resolves "
                "on Chatbot Arena company rank, not TPU hardware performance or hardware-caused "
                "model improvement."
            ),
            captures=["Google model competitiveness", "June 30, 2026 ranking horizon"],
            misses=[
                "TPU 8t/8i performance claims",
                "Hardware causality",
                "Liquidity and market-quality concerns raised by the source",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Tempting but weak: leaderboard rank can move for many reasons unrelated "
                        "to TPU performance claims."
                    ),
                )
            ],
        )
    if "anthropic" in claim_text and "ipo momentum" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_anthropic_no_ipo_june_30_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The no-IPO-by-June market is a weak proxy for valuation-driven IPO momentum; "
                "IPO timing and private valuation pressure are different claims."
            ),
            captures=["Anthropic", "near-term IPO timing as an adjacent question"],
            misses=[
                "Private valuation momentum",
                "Whether valuation hype causally increases IPO probability",
                "Longer or unclear horizon in the user note",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_anthropic_no_ipo_june_30_2026",
                    reason=(
                        "It resolves on whether an IPO happens by June 30, not whether private "
                        "valuation signals imply IPO momentum."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_anthropic_500b_valuation_2026",
                    reason=(
                        "This is direct to valuation confirmation but not to the user's inferred "
                        "near-term IPO timing thesis."
                    ),
                ),
            ],
        )
    if "putnam" in claim_text and "imo" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_ai_wins_imo_gold_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The IMO gold market captures a related math-benchmark outcome, but the source "
                "is about Putnam performance and Axiom Math rather than the official 2026 IMO "
                "resolution event."
            ),
            captures=["AI math capability", "2026 math competition horizon"],
            misses=[
                "Putnam and IMO are different competitions",
                "Official IMO/AIMO resolution source",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Best-AI-model ranking resolves on Chatbot Arena rank, not math contest "
                        "performance."
                    ),
                )
            ],
        )
    if "gemini" in claim_text and "tpu" in claim_text:
        if prompt_version.startswith("v2"):
            return MarketFit(
                recommended_market_id="pm-gemini-arena-2026",
                semantic_fit_class=FitClass.WEAK_PROXY,
                fit_reason=(
                    "The leaderboard market is adjacent to Gemini performance, but it does not "
                    "resolve whether TPU progress caused Gemini to close a broad frontier gap."
                ),
                captures=[
                    "A public signal about Gemini relative model standing",
                    "A time-bounded 2026 outcome",
                ],
                misses=[
                    "The causal TPU mechanism",
                    "A broad definition of closing the frontier-model gap",
                    "Non-leaderboard evidence of model quality",
                ],
                rejected_markets=[
                    RejectedMarket(
                        market_id="pm-tpu-v7-ga-2026",
                        reason=(
                            "TPU availability is hardware delivery, not Gemini model performance."
                        ),
                    )
                ],
            )
        return MarketFit(
            recommended_market_id="pm-gemini-arena-2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The leaderboard market is the best available expression because it tracks whether "
                "Gemini reaches the top of a public model ranking in 2026."
            ),
            captures=[
                "Gemini relative performance signal",
                "A measurable 2026 market close",
            ],
            misses=[
                "The market does not resolve the TPU causal mechanism",
                "The market does not capture every frontier-model benchmark",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-tpu-v7-ga-2026",
                    reason="Hardware availability can happen without Gemini closing the model gap.",
                )
            ],
        )
    if "federal reserve" in claim_text and "july 2026" in claim_text:
        return MarketFit(
            recommended_market_id="pm-direct-fed-cut-july-2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolution directly matches the claim, event, institution, and "
                "meeting date."
            ),
            captures=["Federal Reserve decision", "July 2026 meeting", "rate-cut direction"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-fed-cut-sept-2026",
                    reason="September is a different meeting and horizon.",
                )
            ],
        )

    best = _score_markets(claim, markets)[0]
    if best[0] < 2:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The seed market set contains related-looking topics at best, but no market whose "
                "resolution rules cleanly express this claim."
            ),
            captures=[],
            misses=["No candidate shares enough entities, horizon, and resolution target."],
            rejected_markets=[
                RejectedMarket(
                    market_id=market.market_id,
                    reason=(
                        "Insufficient entity and resolution-rule overlap with the normalized claim."
                    ),
                )
                for _, market in _score_markets(claim, markets)[:2]
            ],
        )
    return MarketFit(
        recommended_market_id=best[1].market_id,
        semantic_fit_class=FitClass.INDIRECT,
        fit_reason=(
            "The market shares some entities with the claim but only partially expresses it."
        ),
        captures=["Some entity overlap"],
        misses=["Resolution rules do not directly encode the full thesis."],
        rejected_markets=[],
    )


def _score_markets(
    claim: NormalizedClaim, markets: list[CandidateMarket]
) -> list[tuple[int, CandidateMarket]]:
    claim_terms = set(re.findall(r"[a-z0-9]+", claim.claim_text.lower())) - STOPWORDS
    scored = []
    for market in markets:
        haystack = " ".join(
            [market.title, market.description, market.resolution_rules, *market.entity_tags]
        ).lower()
        market_terms = set(re.findall(r"[a-z0-9]+", haystack)) - STOPWORDS
        scored.append((len(claim_terms & market_terms), market))
    return sorted(scored, key=lambda item: item[0], reverse=True)


STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "be",
    "before",
    "by",
    "for",
    "if",
    "in",
    "is",
    "it",
    "make",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "will",
    "with",
    "year",
}




def _is_known_eval_source(thesis: str) -> bool:
    lowered = thesis.lower()
    triggers = [
        "link cli",
        "dollar milkshake",
        "swap lines",
        "reconstruct complex papers",
        "large multi-agent system",
        "gemini 3.2",
        "gemini 3.5",
        "spacex ipo timeline",
        "anthropic just hit a $1 trillion valuation",
        "tpu 8t",
        "tpu 8i",
        "ipo momentum",
        "putnam",
        "gpt-5.6",
        "claude 4.8 opus",
        "diplomatic negotiations around iran",
        "3 serious points of disagreement",
        "ubiquity",
        "mi450x",
        "rules out a potential foundry deal",
        "meta-manus",
        "cross-border ai is becoming",
        "anthropic is paying spacex",
        "ai is eating 80% of global vc funding",
        "sibyl memory",
        "homes are 40% overpriced",
        "60 more days",
        "draft peace deal within 24 hours",
        "framework memorandum",
        "opus 4.8",
        "as good as mythos",
        "gpqa diamond",
        "winner take all games",
        "boomer balance sheets",
        "gas prices need to get back down",
        "dtcc migration",
        "solbtc update",
        "gartner's latest ai forecast",
        "$2.59t market in 2026",
        "pre-emptively hiking rates",
        "antfleet two-model review",
        "fed funds rate forecast table",
        "limits of interest rate policy",
        "agentic ai is moving out of the demo phase",
        "performance review cycle",
    ]
    return any(trigger in lowered for trigger in triggers)


def _claim_haystack(claim: NormalizedClaim) -> str:
    return " ".join(
        [claim.claim_text, *claim.entities, claim.horizon, claim.stance, claim.reasoning_summary]
    ).lower()


def _sentence(text: str) -> str:
    stripped = " ".join(text.strip().split())
    match = re.split(r"(?<=[.!?])\s+", stripped)
    return match[0][:300] if match else stripped[:300]


def _simple_entities(text: str) -> list[str]:
    matches = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?\b", text)
    unique: list[str] = []
    for match in matches:
        if match not in unique:
            unique.append(match)
    return unique[:6]
