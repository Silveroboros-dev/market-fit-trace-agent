from __future__ import annotations

import json

from app.models import CandidateMarket, NormalizedClaim


def build_claim_extraction_prompt(thesis: str, prompt_version: str) -> str:
    return f"""
You are MarketFitTraceAgent. Extract a normalized prediction-market thesis.
Return only JSON with keys: claim_text, entities, horizon, stance, confidence,
reasoning_summary.
Prompt version: {prompt_version}
Thesis:
{thesis}
"""


def build_market_fit_prompt(
    *,
    claim: NormalizedClaim,
    markets: list[CandidateMarket],
    prompt_version: str,
    prior_failure_summary: str | None,
) -> str:
    return f"""
Classify which prediction-market expression best fits the normalized claim.
Allowed semantic_fit_class values: direct, indirect, weak_proxy, no_clean_expression.
Do not overclaim adjacent markets. Return only JSON matching this shape:
recommended_market_id, semantic_fit_class, fit_reason, captures, misses, rejected_markets.
Prompt version: {prompt_version}
Prior failed trace summary: {prior_failure_summary or "none"}
Claim: {claim.model_dump_json()}
Candidate markets: {json.dumps([m.model_dump() for m in markets])}
"""
