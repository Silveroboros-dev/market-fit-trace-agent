from __future__ import annotations

from google.adk import Agent

from app.adk_runtime import ADKJsonRuntime
from market_fit_adk.agent import candidate_market_snapshots, market_fit_policy, root_agent


def test_root_agent_uses_official_adk_shape() -> None:
    assert isinstance(root_agent, Agent)
    assert root_agent.name == "market_fit_trace_agent"
    assert root_agent.model
    assert root_agent.instruction
    assert root_agent.tools


def test_root_agent_has_product_tools() -> None:
    markets = candidate_market_snapshots()
    policy = market_fit_policy()

    assert markets["markets"][0]["market_id"] == "pm-gemini-arena-2026"
    assert {
        "polymarket_anthropic_500b_valuation_2026",
        "polymarket_anthropic_no_ipo_june_30_2026",
        "polymarket_largest_ipo_2026_anthropic",
    }.issubset({market["market_id"] for market in markets["markets"]})
    assert "weak_proxy" in policy["classes"]
    assert "Deterministic code" in policy["invariant"]


def test_adk_runtime_imports_deployable_root_agent() -> None:
    runtime = ADKJsonRuntime()

    assert runtime._imports_available()
    assert runtime.runtime_name.startswith("google-adk:")
