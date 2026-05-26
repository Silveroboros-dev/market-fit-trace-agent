# Retrieval Candidate: live-solana-fundamentals-price-proxy

## Human Review

- Human review status: pending
- Reviewer note: 
- Candidate fit hypothesis: no clean expression, or retrieval miss pending better crypto routing
- Candidate best market id: none observed
- Candidate adjacent / tempting wrong market ids: 2086878, 2289144, 553857, 2086886, 2087250

## Observed Live Run

- Run id: run_85efee67d1cf
- Phoenix trace id: f1263a3e02e0e89d7c9bd34fd552174b
- Agent-time retrieval id: retr_c61003542c14c520
- Snapshot id: polydata_polymarket_2026-05-24 00:00:00+00:00
- As-of timestamp: 2026-05-24 00:00:00+00:00
- Proposed fit class: no_clean_expression
- Recommended market id: none
- Eval flags: false_strong_recommendation=false; weak_proxy_detected=false; unsupported_implication=false
- Rules status: missing for exported live market rules

## Review Note

This is a useful candidate for separating price proxies from broad crypto-fundamental theses. The thesis is about Solana usage, product-market fit, speed, efficiency, UX, and resilience despite SOL price weakness. The observed live run did not recommend a market, and the fit reason says no supplied market resolves those fundamentals together.

The packet should stay in the candidate review queue until a reviewer decides whether the correct lesson is true `no_clean_expression` or a retrieval-quality issue. If PolyData can retrieve Solana-specific price or ETF-style markets in a later snapshot, those should be reviewed as weak proxies rather than clean expressions of the fundamentals thesis.

Do not promote this candidate until source provenance, frozen markets,
rules status, and expected labels have been reviewed.
