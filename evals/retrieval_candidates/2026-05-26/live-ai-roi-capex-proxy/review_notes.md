# Retrieval Candidate: live-ai-roi-capex-proxy

## Human Review

- Expected fit class: `no_clean_expression` for the current live retrieval
  packet.
- Best market id: none.
- Acceptable market ids: none.
- Adjacent / tempting wrong market ids: `pm_amazon_2026_capex_above` from the
  deterministic policy branch, but that ID is not present in the current live
  PolyData retrieval packet.
- Review note: Human review decided this packet should be treated as
  `no_clean_expression`. The normalized thesis is an aggregate AI funding /
  capex / ROI claim, while the retrieved live market set contains unrelated
  politics, election, shipping, and sports markets with missing rules. The new
  workflow guard correctly rejects the absent `pm_amazon_2026_capex_above`
  recommendation instead of allowing a fixture-style market ID to escape into
  live PolyData mode.

## Observed Evidence

- Candidate source retrieval id: `retr_4203d095d1b58bd5`
- Agent normalized-claim retrieval id: `retr_c46ba9222684390f`
- Snapshot id: `polydata_polymarket_2026-05-24 00:00:00+00:00`
- Agent run id after guard: `run_a5ae2a2e8eae`
- Phoenix trace id after guard: `4de1ef62e2b2bd400d1becd4f3583644`
- Guarded fit class: `no_clean_expression`
- Guarded recommended market id: none
- Rejected absent market id: `pm_amazon_2026_capex_above`
- Live retrieved market ids from the agent run:
  `616906`, `2086885`, `2086888`, `2086878`, `906973`
- Live rules status: all missing

Do not promote this candidate until source provenance, frozen markets,
rules status, and expected labels have been reviewed.
