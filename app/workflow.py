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
from app.policy.extraction import _deterministic_extract, _is_known_eval_source
from app.policy.fit import _deterministic_classify
from app.prompts import build_claim_extraction_prompt, build_market_fit_prompt
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
        generated = await self.adk_runtime.generate_json(
            prompt=build_claim_extraction_prompt(thesis, prompt_version),
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
        model_fit_proposal = await self.adk_runtime.generate_json(
            prompt=build_market_fit_prompt(
                claim=claim,
                markets=markets,
                prompt_version=prompt_version,
                prior_failure_summary=prior_failure_summary,
            ),
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
