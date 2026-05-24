# Market Fit V2 Candidate Pack

This folder stages candidate eval fixtures discovered from public X posts and
public prediction-market searches on May 23, 2026.

Status: candidate pack, not default goldens.

Use this pack to expand `market_fit_v1` after market pages and resolution rules
are independently re-checked. The current source is user-provided Grok output
with exact post text and candidate market notes.

## Contents

- `examples.jsonl`: source posts and provenance.
- `expected_outputs.jsonl`: proposed normalized thesis and expected fit class.
- `market_snapshots.jsonl`: public candidate markets cited by the source review.
- `dropped_cases.md`: excluded cases and rationale.

## Current Triage

- 16 retained source examples.
- 9 source examples have no candidate market and are expected to exercise
  `no_clean_expression`.
- 2 examples are expected `weak_proxy`.
- 4 examples are expected `indirect`.
- 1 example is expected `direct`.

The low direct count is intentional. This pack is strongest for the product's
core claim: tempting market expressions often fail on horizon, metric, entity, or
causal mechanism.

## Before Promoting To Goldens

1. Re-open each market URL and freeze exact resolution rules.
2. Replace approximate prices with API or page snapshots.
3. Confirm source text is still public or keep the frozen text as user-provided.
4. Run the pack separately with:

```bash
make evals-candidates
```

This target is intentionally non-CI: it reports pass/fail rows but exits 0 while
the pack is still being promoted.

5. Only then decide whether to merge cases into the default `market_fit_v1`
   golden suite or create a formal `market_fit_v2`.
