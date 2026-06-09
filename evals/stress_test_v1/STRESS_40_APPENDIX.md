# Stress-40 Appendix: Deterministic Stability and Advisory Variance

## Scope

Offline appendix evidence summarizing four committed post-patch Stress-40 runs. It runs no new model calls and writes no prompts, policy code, or strict expected labels.

Stress-40 is appendix evidence, not the core improvement proof. The core improvement proof is the TPU Phoenix MCP trace-repair loop. Governance 50 is supporting governance and review-memory evidence. This appendix shows that the same Phoenix-traced harness holds the deterministic boundary across many adversarial cases.

- Runs summarized: `4`
- Cases per run: `[40, 40, 40, 40]`
- Runs new Gemini calls: `False`
- Writes prompts: `False`
- Writes policy code: `False`
- Writes strict expected labels: `False`

## Gemini Advisory Variance (the model proposer)

Gemini proposes; deterministic policy disposes. These advisory mismatches are model-side variance and never override the deterministic class.

| Run | Cases | Proposals present | Missing | Advisory mismatches | Mismatch rate |
| --- | --- | --- | --- | --- | --- |
| `run_1` | 40 | 40 | 0 | 17 | 0.4250 |
| `run_2` | 40 | 39 | 1 | 17 | 0.4359 |
| `run_3` | 40 | 40 | 0 | 16 | 0.4000 |
| `run_4` | 40 | 40 | 0 | 21 | 0.5250 |

## Deterministic Stability (the classifier of record)

- Distinct cases: `40`
- Present in all runs: `40`
- Identical deterministic class across all runs: `40` of `40`
- Cases with non-identical deterministic class across runs: `0`

The deterministic class is run-invariant: every case resolves to the same final class on every run. All run-to-run movement is Gemini advisory, not the classifier of record.

## Deterministic Safety Decomposition (per run)

| Run | Match | Under-call (safe) | Strong-over-weak/no (review) | Direct false positive |
| --- | --- | --- | --- | --- |
| `run_1` | 15 | 14 | 11 | 0 |
| `run_2` | 15 | 14 | 11 | 0 |
| `run_3` | 15 | 14 | 11 | 0 |
| `run_4` | 15 | 14 | 11 | 0 |

- Deterministic direct false positives (`deterministic_fit_class == direct` while `expected_fit_class != direct`): `0` across all runs.
- Under-calls are the safe, conservative direction (deterministic weaker than the synthetic label).

## Strong-Over-Weak/No Review Candidates

These cases returned a deterministic class stronger than a synthetic `weak_proxy` or `no_clean_expression` label (all `indirect` here). They are human-review candidates, explicitly NOT direct false positives, and none are promoted automatically. The deterministic gate is run-invariant, so this set is identical across all runs (trace link shown from run 1).

| Case | Family | Expected | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_es_openai_filing_vs_completion_001` | `event_stage_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/98c6785a6b7dfd5abcbce0fc969be913) |
| `stress_es_stripe_s1_vs_ipo_005` | `event_stage_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ae5468d636da8664847d922365f51a94) |
| `stress_es_openai_board_vs_ipo_007` | `event_stage_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/86ada84aded3c9829cf916cae8ddc47c) |
| `stress_es_anthropic_ipo_rumor_vs_no_ipo_008` | `event_stage_mismatch` | `no_clean_expression` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/66409a69c2992d6d26e1dedcfa2b780f) |
| `stress_mm_nvidia_margin_vs_share_price_005` | `metric_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/26a104b1cef8e785985a2c7fadd3c3c7) |
| `stress_mm_anthropic_headcount_vs_valuation_006` | `metric_mismatch` | `no_clean_expression` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/6b8f152af3b49bb97f31364d10ea5a5f) |
| `stress_hm_av_2030_vs_waymo_2026_002` | `horizon_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/3d76543762846e856a36e9aa47c2f73c) |
| `stress_hm_openai_q4_release_vs_june_market_004` | `horizon_mismatch` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ff1615abc6f48a53eb61e0e13c76770e) |
| `stress_cm_interest_rates_vs_housing_005` | `causal_mechanism` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/33172ddc302b90504db5e972427259d0) |
| `stress_ct_green_energy_storage_003` | `composite_thesis` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/7606b5ee846d494e858b444775fc9dde) |
| `stress_ct_us_china_ai_trade_005` | `composite_thesis` | `no_clean_expression` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/fa4cffdded7f483b601af247b85571ab) |

## How To Read This Appendix

- The deterministic gate is the classifier of record and is 100% stable across the four runs.
- Gemini advisory variance is the model proposer's noise. It is visible in Phoenix and never rewrites the final class.
- The strong-over-weak/no cases are candidate-only review items, not the zero direct false positives. A reviewer decides whether each needs more rules, stays candidate-only, becomes a strict golden candidate, or is disregarded.
