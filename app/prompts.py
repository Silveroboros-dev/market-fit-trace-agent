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

Before assigning the fit class, apply this market-fit checklist. Use it for
calibration; do not turn every mismatch into no_clean_expression.
1. Entity/product/version: does the market resolve the same entity, product
   family, and version, or only an adjacent ecosystem actor?
2. Event stage: identify whether the claim is about preparation, filing,
   roadshow, pricing, completion, or post-event valuation.
3. Metric: identify the market's resolution metric, such as valuation, revenue,
   users, margin, benchmark, release timing, ranking, or share price.
4. Horizon: compare the claim horizon with the market close date and resolution
   window.
5. Compound coverage: if the claim has multiple material conditions, list which
   conditions the market resolves and which it misses.
6. Causal bridge: if the market tests an input such as hardware, funding,
   regulation, rates, or energy cost, decide whether that input is central
   evidence or only a loose proxy.
7. Outcome polarity: if the market is framed opposite to the thesis, identify
   the supporting outcome. Inverse framing alone must never be direct.

Class calibration:
- direct: use only when the market outcome would resolve the claim on the same
  entity, event stage, metric, and horizon.
- indirect: use when the market resolves a central event, milestone, or material
  component that would strongly update the claim, but does not fully resolve
  every condition. For example, an IPO-completion market can be indirect evidence
  for a same-company IPO roadshow thesis when the horizon overlaps.
- weak_proxy: use when the market is adjacent evidence that plausibly updates the
  thesis but can move for unrelated reasons. Examples include early preparation
  with no timeline, valuation momentum, supplier/customer adoption, hardware
  inputs, funding, regulation, rates, or energy costs.
- no_clean_expression: use when the market cannot materially test the thesis
  because the entity, event, metric, horizon, or supporting outcome is too
  different to support a defensible inference.

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
