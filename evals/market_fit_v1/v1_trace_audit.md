# Market Fit v1 Trace Audit

Date: 2026-05-24

Purpose: re-run the original 10 baseline goldens through the current ADK/Phoenix
trace pipeline after Phoenix MCP and trace-linked evals were integrated.

## Result

Decision: keep `market_fit_v1` as baseline goldens.

The live ADK run passed all 10 cases and emitted Phoenix trace URLs for every
case. The latest trace was verified with `make phoenix-check`, including a
`fit_eval_run` span and Phoenix span annotations for the core eval metrics.

Commands run:

```bash
cd /Users/rk/Desktop/rapid-epistemic-trace-agent-package
make evals
make evals-live
make phoenix-check
```

Live eval summary:

```json
{
  "status": "passed",
  "mode": "live",
  "eval_pack": "market_fit_v1",
  "case_count": 10,
  "passed_count": 10
}
```

Phoenix check summary:

```json
{
  "status": "ok",
  "project": "market_fit_trace_agent",
  "trace_id": "060fa5c70fe034b0b32ebf4ddda4f5e4",
  "trace_found": true,
  "fit_eval_span_id": "715b0d5559bce1f2",
  "required_spans_found": ["fit_eval_run"],
  "required_spans_missing": [],
  "required_annotations_found": [
    "schema_valid",
    "false_strong_recommendation",
    "weak_proxy_detected",
    "unsupported_implication"
  ],
  "required_annotations_missing": []
}
```

The exact span count is intentionally not a pass condition; instrumentation
changes can add or remove spans without invalidating the proof.

## Live Trace Rows

| Case | Expected | Actual | Market | Eval flags | Phoenix trace | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| `eval_001` | `no_clean_expression` | `no_clean_expression` | none | pass | https://app.phoenix.arize.com/s/rukar570/traces/1b9d85081244713a135072ff633aa876 | keep |
| `eval_002` | `no_clean_expression` | `no_clean_expression` | none | pass | https://app.phoenix.arize.com/s/rukar570/traces/d1089e889e18d1c1dfb52fd121cd92d6 | keep |
| `eval_003` | `no_clean_expression` | `no_clean_expression` | none | pass | https://app.phoenix.arize.com/s/rukar570/traces/21d0fa901ab66b2e0cd7152c46dfbfb5 | keep |
| `eval_004` | `no_clean_expression` | `no_clean_expression` | none | pass | https://app.phoenix.arize.com/s/rukar570/traces/fabdd7de63d888abed99ecc74b60c583 | keep |
| `eval_005` | `indirect` | `indirect` | `polymarket_gemini_3_2_june_30_2026` | pass | https://app.phoenix.arize.com/s/rukar570/traces/aa03c8d9cd45bf3715c2ae34dbe278be | keep |
| `eval_006` | `direct` | `direct` | `polymarket_largest_ipo_2026_spacex` | pass | https://app.phoenix.arize.com/s/rukar570/traces/ac3c6d29674762a605bbe8777b6fa066 | keep |
| `eval_007` | `direct` | `direct` | `polymarket_anthropic_500b_valuation_2026` | pass | https://app.phoenix.arize.com/s/rukar570/traces/a825d91b3e2597cc7241bef05c023c3e | keep |
| `eval_008` | `weak_proxy` | `weak_proxy` | `polymarket_best_ai_model_google_end_june_2026` | weak proxy detected | https://app.phoenix.arize.com/s/rukar570/traces/35193bc0ec394ff6b78bd2980ff070bb | keep |
| `eval_009` | `weak_proxy` | `weak_proxy` | `polymarket_anthropic_no_ipo_june_30_2026` | weak proxy detected | https://app.phoenix.arize.com/s/rukar570/traces/d0e4e39bc521a2123616d6893ed6ef54 | keep |
| `eval_010` | `indirect` | `indirect` | `polymarket_ai_wins_imo_gold_2026` | pass | https://app.phoenix.arize.com/s/rukar570/traces/060fa5c70fe034b0b32ebf4ddda4f5e4 | keep |

## What This Supports

This audit supports the demo claim that the baseline evals were not merely
pre-Phoenix fixtures. They were replayed through the current live ADK/Gemini
path, emitted Phoenix traces, and produced trace-linked eval annotations.

The two weak-proxy cases, `eval_008` and `eval_009`, remain the most useful v1
demo cases because they show the product's core trust boundary: tempting adjacent
markets are not allowed to become strong recommendations.
