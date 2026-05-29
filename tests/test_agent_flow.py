from __future__ import annotations

import asyncio

from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from app.market_provider import MarketRetrievalResult
from app.models import CandidateMarket, FitClass, NormalizedClaim


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


def test_weak_proxy_first_run_then_improves(tmp_path):
    asyncio.run(_weak_proxy_first_run_then_improves(tmp_path))


async def _weak_proxy_first_run_then_improves(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=OfflineADKRuntime())

    thesis = (
        "Google TPU claims mean Gemini will close the gap with frontier models this year. "
        "Find the best prediction-market expression and tell me whether the market is a clean fit."
    )
    first = await agent.run(thesis=thesis, prompt_version="v1_lenient")
    assert first.fit.semantic_fit_class == FitClass.INDIRECT
    assert first.eval.metrics.false_strong_recommendation is True

    improved = await agent.improve_from_trace(first.run_id)
    assert improved.inspection_source == "local_eval_fallback"
    assert improved.fallback_used is True
    assert improved.before_run_id == first.run_id
    assert improved.before_trace_id == first.phoenix_trace_id
    assert improved.before_fit == FitClass.INDIRECT
    assert improved.after.fit.semantic_fit_class == FitClass.WEAK_PROXY
    assert improved.after_fit == FitClass.WEAK_PROXY
    assert improved.false_strong_recommendation_before is True
    assert improved.false_strong_recommendation_after is False
    assert improved.after.eval.metrics.false_strong_recommendation is False
    assert improved.after.eval.metrics.weak_proxy_detected is True
    assert improved.after.eval.metrics.second_run_improvement is True


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


def test_model_fit_proposal_is_captured_but_policy_wins(tmp_path):
    asyncio.run(_model_fit_proposal_is_captured_but_policy_wins(tmp_path))


async def _model_fit_proposal_is_captured_but_policy_wins(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(store=store, adk_runtime=ProposalADKRuntime())

    result = await agent.run(
        thesis=(
            "Google TPU claims mean Gemini will close the gap with frontier models this year."
        ),
        prompt_version="v2_trace_inspected",
    )

    run = store.get_run(result.run_id)
    assert run["model_fit_proposal_json"]
    assert "pm-gemini-arena-2026" in run["model_fit_proposal_json"]
    assert result.fit.semantic_fit_class == FitClass.WEAK_PROXY
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
