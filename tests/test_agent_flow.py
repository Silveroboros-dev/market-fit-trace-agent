from __future__ import annotations

import asyncio

import pytest

from app.agent import MarketFitTraceAgent, TraceInspectionUnavailableError
from app.ledger import LedgerStore
from app.market_provider import MarketRetrievalResult
from app.models import CandidateMarket, FitClass, NormalizedClaim, PhoenixInspection


class OfflineADKRuntime:
    runtime_name = "offline-test-runtime"

    async def generate_json(self, **_kwargs):
        return None


class ProposalADKRuntime:
    runtime_name = "proposal-test-runtime"

    async def generate_json(self, **kwargs):
        if kwargs.get("task_name") == "market_fit_proposal":
            return {
                "recommended_market_id": "pm-gemini-arena-2026",
                "semantic_fit_class": "direct",
                "fit_reason": "model proposal intentionally overstates fit",
            }
        return None


class RephrasingExtractionADKRuntime:
    runtime_name = "rephrasing-test-runtime"

    async def generate_json(self, **kwargs):
        if kwargs.get("task_name") == "claim_extraction":
            return {
                "claim_text": (
                    "Google TPU progress will help Gemini close the performance gap with "
                    "frontier models during 2026."
                ),
                "entities": ["Google", "TPU", "Gemini", "frontier models"],
                "horizon": "2026",
                "stance": "expects Gemini performance to improve relative to frontier models",
                "confidence": 0.72,
                "reasoning_summary": "Valid but visibly rephrased extraction.",
            }
        return None


class AnthropicExtractionADKRuntime:
    runtime_name = "google-adk:test-double"

    async def generate_json(self, **kwargs):
        if kwargs.get("task_name") == "claim_extraction":
            return {
                "claim_text": (
                    "Anthropic will reach a valuation over 500 billion dollars in "
                    "2026 based on private-market bids."
                ),
                "entities": ["Anthropic", "private valuation"],
                "horizon": "2026",
                "stance": "expects valuation over threshold",
                "confidence": 0.77,
                "reasoning_summary": "Valid ADK extraction using non-$500B wording.",
            }
        if kwargs.get("task_name") == "market_fit_proposal":
            return {
                "recommended_market_id": "polymarket_anthropic_no_ipo_june_30_2026",
                "semantic_fit_class": "weak_proxy",
                "fit_reason": "Model proposal should not override deterministic policy.",
            }
        return None


class MissingRecommendationMarketProvider:
    name = "polydata"

    def retrieve(self, claim: NormalizedClaim | None = None) -> MarketRetrievalResult:
        return MarketRetrievalResult(
            mode=self.name,
            markets=[
                CandidateMarket(
                    market_id="live-unrelated-market",
                    title="Will an unrelated market resolve?",
                    venue="Polymarket",
                    description="A live retrieved market that does not express the claim.",
                    resolution_rules="",
                    close_date="2026-12-31",
                    outcomes=["Yes", "No"],
                    current_probability=0.5,
                    known_fit_risks=[
                        "dynamic_polydata_retrieval",
                        "missing_resolution_rules",
                    ],
                    entity_tags=["Politics"],
                )
            ],
            snapshot_id="test-snapshot",
            as_of_ts="2026-05-26T00:00:00Z",
            retrieval_id="retr_test_missing_market",
            query_summary={"returned_count": 1},
        )

    def get_markets(self, claim: NormalizedClaim | None = None) -> list[CandidateMarket]:
        return self.retrieve(claim).markets


class FakePhoenixMCPInspector:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    async def inspect_failed_run(self, run_id: str) -> PhoenixInspection:
        run = self.store.get_run(run_id)
        return PhoenixInspection(
            run_id=run_id,
            phoenix_trace_id=run["phoenix_trace_id"],
            source="phoenix_mcp",
            fallback_used=False,
            summary=(
                "Phoenix MCP inspected fit_eval_run and returned "
                "false_strong_recommendation=true, unsupported_implication=true, "
                "causal_mechanism_mismatch=true, resolution_target_mismatch=true."
            ),
            recommended_prompt_version="v2_trace_inspected",
            mcp_configured=True,
        )


def test_local_fallback_does_not_apply_trace_repair_gate(tmp_path):
    asyncio.run(_local_fallback_does_not_apply_trace_repair_gate(tmp_path))


def test_phoenix_mcp_trace_context_applies_false_strong_cap(tmp_path):
    asyncio.run(_phoenix_mcp_trace_context_applies_false_strong_cap(tmp_path))


def test_known_tpu_demo_source_uses_stable_extraction(tmp_path):
    asyncio.run(_known_tpu_demo_source_uses_stable_extraction(tmp_path))


async def _known_tpu_demo_source_uses_stable_extraction(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=RephrasingExtractionADKRuntime())

    thesis = "Google TPU progress means Gemini closes the frontier-model gap in 2026."
    result = await agent.run(thesis=thesis, prompt_version="v1_lenient")

    assert result.claim.claim_text == thesis


async def _local_fallback_does_not_apply_trace_repair_gate(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=OfflineADKRuntime())

    thesis = "Google TPU progress means Gemini closes the frontier-model gap in 2026."
    first = await agent.run(thesis=thesis, prompt_version="v1_lenient")
    assert first.claim.claim_text == thesis
    assert first.fit.semantic_fit_class == FitClass.INDIRECT
    assert first.eval.metrics.false_strong_recommendation is True
    assert first.eval.metrics.causal_mechanism_mismatch is True
    assert first.eval.metrics.trace_repair_candidate is True

    with pytest.raises(TraceInspectionUnavailableError):
        await agent.improve_from_trace(first.run_id)

    improved = await agent.improve_from_trace(
        first.run_id, allow_local_fallback=True
    )
    assert improved.inspection_source == "local_eval_fallback"
    assert improved.fallback_used is True
    assert improved.before_run_id == first.run_id
    assert improved.before_trace_id == first.phoenix_trace_id
    assert improved.before_fit == FitClass.INDIRECT
    assert improved.after.claim.claim_text == thesis
    assert improved.after.fit.semantic_fit_class == FitClass.INDIRECT
    assert improved.after_fit == FitClass.INDIRECT
    assert improved.false_strong_recommendation_before is True
    assert improved.false_strong_recommendation_after is True
    assert improved.after.eval.metrics.false_strong_recommendation is True
    assert improved.after.eval.metrics.weak_proxy_detected is False
    assert improved.after.eval.metrics.trace_repair_gate_applied is False
    assert improved.after.eval.metrics.second_run_improvement is False


async def _phoenix_mcp_trace_context_applies_false_strong_cap(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(
        store=store,
        adk_runtime=OfflineADKRuntime(),
        phoenix_inspector_factory=FakePhoenixMCPInspector,
    )

    thesis = "Google TPU progress means Gemini closes the frontier-model gap in 2026."
    first = await agent.run(thesis=thesis, prompt_version="v1_lenient")
    assert first.fit.semantic_fit_class == FitClass.INDIRECT
    assert "closest retrieved adjacent signal" in first.fit.fit_reason
    assert "best available expression" not in first.fit.fit_reason
    assert first.eval.metrics.false_strong_recommendation is True
    assert first.eval.metrics.causal_mechanism_mismatch is True
    assert first.eval.metrics.resolution_target_mismatch is True

    improved = await agent.improve_from_trace(first.run_id)

    assert improved.inspection_source == "phoenix_mcp"
    assert improved.fallback_used is False
    assert improved.after.fit.semantic_fit_class == FitClass.WEAK_PROXY
    assert improved.after_fit == FitClass.WEAK_PROXY
    assert improved.false_strong_recommendation_after is False
    assert improved.after.eval.metrics.weak_proxy_detected is True
    assert improved.after.eval.metrics.trace_repair_gate_applied is True
    assert improved.after.eval.metrics.previous_trace_id == first.phoenix_trace_id
    assert improved.after.eval.metrics.inspection_source == "phoenix_mcp"
    assert improved.after.eval.metrics.second_run_improvement is True
    assert any(
        event.event_type == "trace_repair_gate_applied"
        for event in improved.after.ledger.events
    )


def test_direct_market_fit(tmp_path):
    asyncio.run(_direct_market_fit(tmp_path))


async def _direct_market_fit(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=OfflineADKRuntime())

    result = await agent.run(
        thesis="The Fed will cut interest rates at the July 2026 FOMC meeting.",
        prompt_version="v1_lenient",
    )

    assert result.fit.semantic_fit_class == FitClass.DIRECT
    assert result.fit.recommended_market_id == "pm-direct-fed-cut-july-2026"
    assert result.eval.metrics.false_strong_recommendation is False
    assert result.market_retrieval is not None
    assert result.market_retrieval.mode == "fixture"
    assert result.market_retrieval.market_ids_considered
    assert any(event.event_type == "market_retrieval_run" for event in result.ledger.events)


def test_anthropic_valuation_fixture_is_direct(tmp_path):
    asyncio.run(_anthropic_valuation_fixture_is_direct(tmp_path))


async def _anthropic_valuation_fixture_is_direct(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=OfflineADKRuntime())

    result = await agent.run(
        thesis=(
            "Anthropic will achieve or has achieved a valuation above $500B in 2026, "
            "based on private-market bids and reported revenue acceleration."
        ),
        prompt_version="v1_lenient",
    )

    assert result.fit.semantic_fit_class == FitClass.DIRECT
    assert (
        result.fit.recommended_market_id
        == "polymarket_anthropic_500b_valuation_2026"
    )
    assert result.eval.metrics.no_clean_expression_expected is False
    assert result.eval.metrics.false_strong_recommendation is False
    assert result.market_retrieval is not None
    assert (
        "polymarket_anthropic_500b_valuation_2026"
        in result.market_retrieval.market_ids_considered
    )


def test_anthropic_valuation_adk_extraction_wording_is_direct(tmp_path):
    asyncio.run(_anthropic_valuation_adk_extraction_wording_is_direct(tmp_path))


async def _anthropic_valuation_adk_extraction_wording_is_direct(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=AnthropicExtractionADKRuntime())

    result = await agent.run(
        thesis=(
            "Anthropic will achieve or has achieved a valuation above $500B in 2026, "
            "based on private-market bids and reported revenue acceleration."
        ),
        prompt_version="v1_lenient",
    )

    assert result.model == "google-adk:test-double"
    assert "500 billion" in result.claim.claim_text
    assert result.fit.semantic_fit_class == FitClass.DIRECT
    assert (
        result.fit.recommended_market_id
        == "polymarket_anthropic_500b_valuation_2026"
    )
    assert result.eval.metrics.no_clean_expression_expected is False


def test_tpu_v7_general_availability_is_direct(tmp_path):
    asyncio.run(_tpu_v7_general_availability_is_direct(tmp_path))


async def _tpu_v7_general_availability_is_direct(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=OfflineADKRuntime())

    result = await agent.run(
        thesis="Will Google make TPU v7 generally available before 2027?",
        prompt_version="v1_lenient",
    )

    assert result.fit.semantic_fit_class == FitClass.DIRECT
    assert result.fit.recommended_market_id == "pm-tpu-v7-ga-2026"
    assert result.eval.metrics.false_strong_recommendation is False
    assert result.eval.metrics.unsupported_implication is False
    assert result.market_retrieval is not None
    assert "pm-tpu-v7-ga-2026" in result.market_retrieval.market_ids_considered


def test_model_fit_proposal_is_captured_but_policy_wins(tmp_path):
    asyncio.run(_model_fit_proposal_is_captured_but_policy_wins(tmp_path))


async def _model_fit_proposal_is_captured_but_policy_wins(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=ProposalADKRuntime())

    result = await agent.run(
        thesis="Google TPU progress means Gemini closes the frontier-model gap in 2026.",
        prompt_version="v2_trace_inspected",
    )

    run = store.get_run(result.run_id)
    assert run["model_fit_proposal_json"]
    assert "pm-gemini-arena-2026" in run["model_fit_proposal_json"]
    assert result.fit.semantic_fit_class == FitClass.INDIRECT
    assert result.eval.metrics.trace_repair_gate_applied is False
    assert isinstance(result.eval.metrics.phoenix_annotations_written, bool)


def test_missing_recommended_market_is_guarded_to_no_clean_expression(tmp_path):
    asyncio.run(_missing_recommended_market_is_guarded_to_no_clean_expression(tmp_path))


async def _missing_recommended_market_is_guarded_to_no_clean_expression(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(
        store=store,
        adk_runtime=OfflineADKRuntime(),
        market_provider=MissingRecommendationMarketProvider(),
    )

    result = await agent.run(
        thesis=(
            "AI IS EATING 80% OF GLOBAL VC FUNDING. Anthropic spends $3 for every "
            "$1 in revenue. Microsoft dumped $300B in capex while AI revenue is "
            "far smaller. Enterprises are burning through annual AI budgets with "
            "limited measurable ROI."
        )
    )

    assert result.fit.semantic_fit_class == FitClass.NO_CLEAN_EXPRESSION
    assert result.fit.recommended_market_id is None
    assert result.eval.metrics.no_clean_expression_expected is True
    assert result.fit.rejected_markets[0].market_id == "pm_amazon_2026_capex_above"
    assert "not returned" in result.fit.rejected_markets[0].reason


def test_composite_iran_package_is_weak_proxy(tmp_path):
    asyncio.run(_composite_iran_package_is_weak_proxy(tmp_path))


async def _composite_iran_package_is_weak_proxy(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(
        store=store,
        adk_runtime=OfflineADKRuntime(),
        markets=[
            CandidateMarket(
                market_id="2155023",
                title=(
                    "Will Donald Trump announce that the United States blockade of "
                    "the Strait of Hormuz has been lifted by June 30, 2026?"
                ),
                venue="Polymarket",
                description="Announcement market for lifting the US blockade of Hormuz.",
                resolution_rules=(
                    "This market resolves Yes if the US government officially announces "
                    "the end of the United States blockade of the Strait of Hormuz. "
                    "Whether maritime traffic resumes absent a qualifying announcement "
                    "will not be considered."
                ),
                close_date="2026-06-30",
                outcomes=["Yes", "No"],
                current_probability=0.83,
                known_fit_risks=["dynamic_polydata_retrieval"],
                entity_tags=["Iran", "Strait of Hormuz", "US-Iran"],
            )
        ],
    )

    result = await agent.run(
        thesis=(
            "The US and Iran will extend a 60-day ceasefire, partially reopen the "
            "Strait of Hormuz, unfreeze blocked assets, and ease sanctions by July 2026."
        )
    )

    assert result.fit.semantic_fit_class == FitClass.WEAK_PROXY
    assert result.fit.recommended_market_id == "2155023"
    assert result.eval.metrics.weak_proxy_detected is True
    assert result.eval.metrics.false_strong_recommendation is False
    assert "asset unfreezing" in " ".join(result.fit.misses).lower()
