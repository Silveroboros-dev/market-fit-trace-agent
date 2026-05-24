# Market Fit V2 Golden Suite

This is the promoted second golden suite for Market Fit Trace Agent.

Unlike `market_fit_v2_candidates` and `market_fit_v3_candidates`, this suite is
strict: `make evals-v2` exits non-zero on any failed row.

## Purpose

The suite proves the core trust claim:

> The agent should avoid over-recommending tempting prediction markets when the
> source thesis differs by horizon, metric, platform, mechanism, or causal chain.

## Coverage

- Fed horizon mismatch: 2026 rate-cut market vs no-cuts-until-2028 thesis.
- AI capex/ROI weak proxy: Amazon capex vs aggregate VC/burn/ROI thesis.
- Housing weak proxy: mortgage-rate threshold vs overpricing claim.
- Claude platform mismatch: Claude 5 public release vs Claude 4.8 in Vertex.
- AI model parity no-clean case: GPT-5.6 Pro vs Mythos performance parity.
- Conditional politics no-clean case: Iran/gas/House causal chain.
- AI spend/model-pricing weak proxy: Amazon capex vs global spend and pricing.

## Command

```bash
make evals-v2
```

Pass threshold: 100%.
