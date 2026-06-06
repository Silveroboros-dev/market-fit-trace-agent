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
recommended_market_id, semantic_fit_class, fit_reason, captures, misses, rejected_markets,
advisory_inverse_market_check.

The `advisory_inverse_market_check` field is review guidance, not a truth label.
Use it when a binary market's opposite outcome may express the thesis better than
the market title's Yes outcome. For example, a thesis about the Fed holding rates
steady may make a rate-cut market worth inspecting because the No outcome could be
thesis-supporting. Do not use this advisory field to force semantic_fit_class to
direct. Shape:
{{
  "could_be_useful": true | false,
  "candidate_market_ids": ["market_id"],
  "supporting_outcome": "No | n/a",
  "rationale": "short human-review note"
}}
Prompt version: {prompt_version}
Prior failed trace summary: {prior_failure_summary or "none"}
Claim: {claim.model_dump_json()}
Candidate markets: {json.dumps([m.model_dump() for m in markets])}
"""
