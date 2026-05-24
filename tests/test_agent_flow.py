from __future__ import annotations

import asyncio

from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from app.models import FitClass


class OfflineADKRuntime:
    runtime_name = "offline-test-runtime"

    async def generate_json(self, **_kwargs):
        return None


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
    assert improved.after.fit.semantic_fit_class == FitClass.WEAK_PROXY
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
