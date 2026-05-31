from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.adk_runtime import ADKJsonRuntime
from app.evals import evaluate_fit, evaluate_improvement
from app.ledger import LedgerStore
from app.market_provider import MarketProvider, build_market_provider
from app.models import (
    CandidateMarket,
    EvalMetrics,
    FitClass,
    ImprovementResult,
    MarketFit,
    MarketRetrievalProvenance,
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


@dataclass(frozen=True)
class TraceRepairContext:
    previous_run_id: str
    previous_trace_id: str
    previous_recommended_market_id: str | None
    previous_metrics: EvalMetrics
    previous_failure_summary: str | None
    inspection_source: str
    fallback_used: bool
    inspection_summary: str


class MarketFitTraceAgent:
    def __init__(
        self,
        *,
        store: LedgerStore | None = None,
        adk_runtime: ADKJsonRuntime | None = None,
        markets: list[CandidateMarket] | None = None,
        market_provider: MarketProvider | None = None,
        market_provider_resolver: Callable[[str], MarketProvider | None] | None = None,
        phoenix_inspector_factory: Callable[[LedgerStore], PhoenixMCPInspector]
        | None = None,
    ) -> None:
        self.store = store or LedgerStore()
        self.adk_runtime = adk_runtime or ADKJsonRuntime()
        self.market_provider = market_provider or build_market_provider(markets=markets)
        self.market_provider_resolver = market_provider_resolver
        self.phoenix_inspector_factory = phoenix_inspector_factory or PhoenixMCPInspector

    async def run(
        self,
        *,
        thesis: str,
        title: str | None = None,
        prompt_version: str = "v1_lenient",
        prior_failure_summary: str | None = None,
        trace_repair_context: TraceRepairContext | None = None,
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
            "trace_repair.context_present": trace_repair_context is not None,
            "trace_repair.previous_trace_id": (
                trace_repair_context.previous_trace_id if trace_repair_context else ""
            ),
            "trace_repair.inspection_source": (
                trace_repair_context.inspection_source if trace_repair_context else ""
            ),
        }

        with trace.span("market_fit_trace_agent.run", attrs):
            with trace.span("user_goal_received", {"run_id": run_id, "goal_length": len(thesis)}):
                pass
            with trace.span("source_ingested", {"run_id": run_id}):
                source = self.store.create_source(raw_text=thesis, title=title)
            with trace.span("claim_extracted", attrs):
                claim = await self.extract_claim(thesis, prompt_version)
            with trace.span(
                "market_retrieval_run",
                {
                    "run_id": run_id,
                    "market_data_mode": self._market_provider_for(thesis).name,
                },
            ):
                retrieval = self._market_provider_for(thesis).retrieve(claim)
                markets = retrieval.markets
                trace.set_current_span_attributes(
                    {
                        "market_data_mode": retrieval.mode,
                        "snapshot_id": retrieval.snapshot_id or "",
                        "as_of_ts": retrieval.as_of_ts or "",
                        "retrieval_id": retrieval.retrieval_id or "",
                        "returned_count": len(markets),
                        "top_k": retrieval.query_summary.get("top_k", len(markets)),
                        "min_liquidity_usd": retrieval.query_summary.get(
                            "min_volume_usd", ""
                        ),
                        "liquidity_metric": retrieval.query_summary.get(
                            "liquidity_metric", ""
                        ),
                    }
                )
            with trace.span("market_fit_classified", attrs):
                fit, model_fit_proposal = await self.classify_fit(
                    claim=claim,
                    markets=markets,
                    prompt_version=prompt_version,
                    prior_failure_summary=prior_failure_summary,
                )
                fit, trace_repair_gate_applied = self._trace_informed_false_strong_cap(
                    fit=fit,
                    markets=markets,
                    context=trace_repair_context,
                )
                fit, missing_market_id = self._guard_recommended_market_in_context(
                    fit, markets
                )
                model_fit_proposal_json = _json_preview(model_fit_proposal)
                trace.set_current_span_attributes(
                    {
                        "model_fit_proposal.present": bool(model_fit_proposal),
                        "model_fit_proposal.preview": model_fit_proposal_json or "",
                        "policy_decision_source": "deterministic_policy",
                        "policy_guard.recommended_market_in_context": (
                            missing_market_id is None
                        ),
                        "policy_guard.missing_recommended_market_id": (
                            missing_market_id or ""
                        ),
                        "trace_repair_gate.applied": trace_repair_gate_applied,
                        "trace_repair_gate.previous_trace_id": (
                            trace_repair_context.previous_trace_id
                            if trace_repair_context
                            else ""
                        ),
                        "trace_repair_gate.inspection_source": (
                            trace_repair_context.inspection_source
                            if trace_repair_context
                            else ""
                        ),
                    }
                )
            with trace.span("rejected_markets_explained", {"run_id": run_id}):
                fit = self._ensure_rejected_markets(fit, markets)
            market_retrieval = _retrieval_provenance(retrieval)
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
                self.store.record_market_retrieval(
                    run_id=run_id,
                    claim_id=claim_id,
                    retrieval=market_retrieval.model_dump(),
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
                    trace_repair_gate_applied=trace_repair_gate_applied,
                    previous_trace_id=(
                        trace_repair_context.previous_trace_id
                        if trace_repair_context
                        else None
                    ),
                    previous_failure_summary=(
                        trace_repair_context.previous_failure_summary
                        if trace_repair_context
                        else None
                    ),
                    inspection_source=(
                        trace_repair_context.inspection_source
                        if trace_repair_context
                        else None
                    ),
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
                        "eval.causal_mechanism_mismatch": (
                            eval_result.metrics.causal_mechanism_mismatch
                        ),
                        "eval.resolution_target_mismatch": (
                            eval_result.metrics.resolution_target_mismatch
                        ),
                        "eval.horizon_mismatch": eval_result.metrics.horizon_mismatch,
                        "eval.entity_mismatch": eval_result.metrics.entity_mismatch,
                        "eval.trace_repair_candidate": (
                            eval_result.metrics.trace_repair_candidate
                        ),
                        "eval.trace_repair_gate_applied": (
                            eval_result.metrics.trace_repair_gate_applied
                        ),
                        "eval.previous_trace_id": (
                            eval_result.metrics.previous_trace_id or ""
                        ),
                        "eval.inspection_source": (
                            eval_result.metrics.inspection_source or ""
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
            if trace_repair_gate_applied and trace_repair_context is not None:
                self.store.record_trace_repair_gate(
                    run_id=run_id,
                    claim_id=claim_id,
                    previous_trace_id=trace_repair_context.previous_trace_id,
                    previous_failure_summary=(
                        trace_repair_context.previous_failure_summary or ""
                    ),
                    inspection_source=trace_repair_context.inspection_source,
                    recommended_market_id=fit.recommended_market_id,
                )
            eval_result.eval_record_id = eval_ref["eval_record_id"]
            self.store.update_run(
                run_id,
                status="completed",
                phoenix_trace_id=phoenix_trace_id,
                eval_summary_json=eval_result.metrics.model_dump_json(),
                model_fit_proposal_json=model_fit_proposal_json,
                market_retrieval_json=market_retrieval.model_dump_json(),
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
            market_retrieval=market_retrieval,
            market_context=markets,
            eval=eval_result,
            ledger=self.store.query_claim_trace(claim_id),
        )

    async def improve_from_trace(self, run_id: str) -> ImprovementResult:
        inspector = self.phoenix_inspector_factory(self.store)
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
        trace_repair_context = TraceRepairContext(
            previous_run_id=before.run_id,
            previous_trace_id=before.phoenix_trace_id,
            previous_recommended_market_id=before.fit.recommended_market_id,
            previous_metrics=before.eval.metrics,
            previous_failure_summary=before.eval.failure_summary,
            inspection_source=inspection.source,
            fallback_used=inspection.fallback_used,
            inspection_summary=inspection.summary,
        )
        after = await self.run(
            thesis=source["raw_text"],
            title=source.get("title"),
            prompt_version=inspection.recommended_prompt_version,
            prior_failure_summary=inspection.summary,
            trace_repair_context=trace_repair_context,
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

    def _market_provider_for(self, thesis: str) -> MarketProvider:
        if self.market_provider_resolver is None:
            return self.market_provider
        return self.market_provider_resolver(thesis) or self.market_provider

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

    def _trace_informed_false_strong_cap(
        self,
        *,
        fit: MarketFit,
        markets: list[CandidateMarket],
        context: TraceRepairContext | None,
    ) -> tuple[MarketFit, bool]:
        if context is None:
            return fit, False
        if context.inspection_source != "phoenix_mcp" or context.fallback_used:
            return fit, False
        if fit.semantic_fit_class not in {FitClass.DIRECT, FitClass.INDIRECT}:
            return fit, False
        if not _prior_trace_context_has_failure(context):
            return fit, False
        if not _prior_trace_context_has_mismatch(context):
            return fit, False
        if not _same_or_equivalent_market(
            fit.recommended_market_id,
            context.previous_recommended_market_id,
            markets,
        ):
            return fit, False

        capped_reason = (
            "The leaderboard market is the best retrieved adjacent signal, but not a "
            "clean expression of the thesis. Trace-informed cap: Phoenix MCP retrieved "
            "the prior failed trace/eval context, which showed a false-strong "
            "recommendation with an explicit mismatch signal. This market remains "
            "useful only as a weak proxy unless its resolution directly expresses the "
            "thesis mechanism."
        )
        misses = [
            *fit.misses,
            "Phoenix MCP prior trace exposed false-strong fit risk",
            "Prior eval context contained causal or resolution-target mismatch",
        ]
        return (
            MarketFit(
                recommended_market_id=fit.recommended_market_id,
                semantic_fit_class=FitClass.WEAK_PROXY,
                fit_reason=capped_reason,
                captures=fit.captures,
                misses=_dedupe(misses),
                rejected_markets=fit.rejected_markets,
            ),
            True,
        )

    def _guard_recommended_market_in_context(
        self, fit: MarketFit, markets: list[CandidateMarket]
    ) -> tuple[MarketFit, str | None]:
        recommended_id = fit.recommended_market_id
        if recommended_id is None:
            return fit, None
        retrieved_ids = {market.market_id for market in markets}
        if recommended_id in retrieved_ids:
            return fit, None

        guarded_fit = MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                f"The policy proposed market `{recommended_id}`, but that market was not "
                "present in the bounded retrieved market context for this run. The app "
                "cannot recommend a market it did not retrieve and inspect, so this run is "
                "classified as no_clean_expression pending reviewed market evidence."
            ),
            captures=[],
            misses=[
                "Recommended market absent from retrieved market context",
                "No retrieved market cleanly expresses the normalized thesis",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id=recommended_id,
                    reason=(
                        "Rejected because this market ID was not returned by the bounded "
                        "market retrieval step for this run."
                    ),
                )
            ],
        )
        return guarded_fit, recommended_id

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
        market_retrieval_json = run.get("market_retrieval_json")
        market_retrieval = (
            MarketRetrievalProvenance.model_validate(json.loads(market_retrieval_json))
            if market_retrieval_json
            else None
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
            market_retrieval=market_retrieval,
            market_context=[],
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


def _retrieval_provenance(retrieval: Any) -> MarketRetrievalProvenance:
    return MarketRetrievalProvenance(
        mode=retrieval.mode,
        snapshot_id=retrieval.snapshot_id,
        as_of_ts=retrieval.as_of_ts,
        retrieval_id=retrieval.retrieval_id,
        query_summary=retrieval.query_summary,
        excluded_summary=retrieval.excluded_summary,
        market_ids_considered=[market.market_id for market in retrieval.markets],
    )


def _prior_trace_context_has_failure(context: TraceRepairContext) -> bool:
    summary = context.inspection_summary.lower()
    return bool(
        (
            context.previous_metrics.false_strong_recommendation
            or context.previous_metrics.unsupported_implication
        )
        and (
            "false_strong_recommendation" in summary
            or "unsupported_implication" in summary
        )
    )


def _prior_trace_context_has_mismatch(context: TraceRepairContext) -> bool:
    summary = context.inspection_summary.lower()
    prior_mismatch = any(
        (
            context.previous_metrics.causal_mechanism_mismatch,
            context.previous_metrics.resolution_target_mismatch,
            context.previous_metrics.horizon_mismatch,
            context.previous_metrics.entity_mismatch,
        )
    )
    return bool(
        prior_mismatch
        and (
            "causal_mechanism_mismatch" in summary
            or "resolution_target_mismatch" in summary
            or "horizon_mismatch" in summary
            or "entity_mismatch" in summary
            or "mismatch" in summary
        )
    )


def _same_or_equivalent_market(
    current_market_id: str | None,
    previous_market_id: str | None,
    markets: list[CandidateMarket],
) -> bool:
    if not current_market_id or not previous_market_id:
        return False
    if current_market_id == previous_market_id:
        return True
    current = next((market for market in markets if market.market_id == current_market_id), None)
    previous = next((market for market in markets if market.market_id == previous_market_id), None)
    return bool(current and previous and current.title.lower() == previous.title.lower())


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
