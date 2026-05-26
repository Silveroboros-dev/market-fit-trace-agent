# Retrieval Candidate: live-ai-roi-capex-proxy

## Human Review

- Expected fit class: TODO - likely `weak_proxy` if an Amazon capex market is
  later retrieved and rules are captured; otherwise likely `no_clean_expression`
  for the current live packet.
- Best market id: TODO - do not use `pm_amazon_2026_capex_above` unless a
  matching live/frozen market snapshot is added.
- Acceptable market ids: TODO
- Adjacent / tempting wrong market ids: `pm_amazon_2026_capex_above` from the
  policy proposal, but that ID is not present in the current live PolyData
  retrieval packet.
- Review note: This is a high-value retrieval/policy mismatch candidate. The
  agent normalized the source into an aggregate AI funding / capex / ROI thesis
  and proposed Amazon capex as `weak_proxy`. However, the live PolyData retrieved
  market set contains numeric market IDs for unrelated politics, election,
  shipping, and sports markets, and every retrieved market has
  `rules_status=missing`. Before promotion, a reviewer should decide whether
  this case is primarily a weak-proxy golden, a no-clean-expression golden, or a
  retrieval-quality regression case.

## Observed Evidence

- Candidate source retrieval id: `retr_4203d095d1b58bd5`
- Agent normalized-claim retrieval id: `retr_c46ba9222684390f`
- Snapshot id: `polydata_polymarket_2026-05-24 00:00:00+00:00`
- Agent run id: `run_a025f7338a5b`
- Phoenix trace id: `ec50287531f168441836c38e0bda989e`
- Proposed fit class: `weak_proxy`
- Proposed market id: `pm_amazon_2026_capex_above`
- Live retrieved market ids from the agent run:
  `616906`, `2086885`, `2086888`, `2086878`, `906973`
- Live rules status: all missing

## Review Questions

1. Should this become a weak-proxy golden after a real Amazon capex market is
   retrieved and frozen?
2. Should this instead become a no-clean-expression golden because the current
   live packet contains no usable market expression?
3. Should the retrieval layer add a guard that rejects recommendations whose
   `recommended_market_id` is absent from the retrieved live market set?

Do not promote this candidate until source provenance, frozen markets,
rules status, and expected labels have been reviewed.
