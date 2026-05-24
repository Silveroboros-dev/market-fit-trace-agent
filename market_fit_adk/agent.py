from __future__ import annotations

import os
from typing import Any

from google.adk import Agent
from google.genai import types


def candidate_market_snapshots() -> dict[str, Any]:
    """Return public-safe seed market snapshots for market-fit reasoning."""
    return {
        "markets": [
            {
                "market_id": "pm-gemini-arena-2026",
                "title": "Will Gemini be ranked #1 on a public model leaderboard in 2026?",
                "fit_risk": "weak_proxy_for_tpu_causal_claim",
                "why_it_is_tempting": (
                    "It has Gemini, public model performance, and a 2026 horizon."
                ),
                "why_it_is_not_clean": (
                    "It does not resolve whether TPU progress caused Gemini to close a broad "
                    "frontier-model gap."
                ),
            },
            {
                "market_id": "pm-tpu-v7-ga-2026",
                "title": "Will Google TPU v7 be generally available before 2027?",
                "fit_risk": "hardware_delivery_not_model_outcome",
                "why_it_is_tempting": "It mentions Google TPU and a 2026 horizon.",
                "why_it_is_not_clean": (
                    "Hardware availability can happen without resolving Gemini model quality."
                ),
            },
            {
                "market_id": "pm-direct-fed-cut-july-2026",
                "title": "Will the Federal Reserve cut rates at the July 2026 FOMC meeting?",
                "fit_risk": "direct_when_claim_mentions_july_2026_fomc_cut",
                "why_it_is_tempting": "It directly names the actor, event, date, and direction.",
                "why_it_is_not_clean": "",
            },
        ]
    }


def market_fit_policy() -> dict[str, Any]:
    """Return the deterministic policy vocabulary used by the app after Gemini proposes."""
    return {
        "classes": {
            "direct": "Resolution rules directly express the claim.",
            "indirect": "Market captures part of the thesis but misses material detail.",
            "weak_proxy": (
                "Market is tempting and related, but would overstate what it resolves."
            ),
            "no_clean_expression": "No candidate market cleanly expresses the claim.",
        },
        "invariant": (
            "Gemini may draft, extract, explain, or propose. Deterministic code performs "
            "final fit checks, eval flags, and ledger writes."
        ),
    }


MARKET_FIT_TRACE_INSTRUCTION = """
You are Market Fit Trace Agent, a Google ADK/Gemini agent for auditing whether a
prediction-market expression actually matches a pasted thesis.

Core behavior:
- Extract normalized claims from messy thesis text.
- Compare claims to candidate market expressions.
- Treat tempting adjacent markets as weak proxies when their resolution rules do not
  directly express the thesis.
- Never provide trading execution advice, wallet actions, or guaranteed-edge language.
- When asked for JSON, return strict JSON only and no prose outside the JSON object.

Important boundary:
Gemini drafts, extracts, summarizes, and proposes. The application layer performs the
final deterministic market-fit evaluation, ledger write, human-verdict handling, and
trace-linked eval scoring.
"""


def _setup_phoenix_for_adk() -> None:
    if os.getenv("PHOENIX_APP_TRACING_READY", "").lower() == "true":
        return
    if not (os.getenv("PHOENIX_API_KEY") or os.getenv("PHOENIX_COLLECTOR_ENDPOINT")):
        return
    try:
        from phoenix.otel import register

        kwargs: dict[str, Any] = {
            "project_name": os.getenv("PHOENIX_PROJECT_NAME", "market_fit_trace_agent"),
            "auto_instrument": True,
            "batch": False,
        }
        if os.getenv("PHOENIX_API_KEY"):
            kwargs["api_key"] = os.getenv("PHOENIX_API_KEY")
        register(**kwargs)
        os.environ["PHOENIX_ADK_TRACING_READY"] = "true"
    except Exception:
        # Local import and offline tests must not fail when Phoenix is absent or already set up.
        return


_setup_phoenix_for_adk()

root_agent = Agent(
    name="market_fit_trace_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
    description=(
        "Audits prediction-market thesis matches and identifies weak proxy markets."
    ),
    instruction=MARKET_FIT_TRACE_INSTRUCTION,
    tools=[candidate_market_snapshots, market_fit_policy],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
    ),
)
