# Policy Review Batch

Generated at UTC: `2026-06-09T05:19:35.801525+00:00`
Candidate date: `2026-06-08`
Source directory: `evals/failure_candidates/2026-06-08`

## Scope

This artifact groups candidate-only failure packets into reviewable policy and prompt proposals. It is not a strict golden dataset and it does not mutate policy code.

- Failure candidates: `19`
- Failure families: `7`
- Writes strict expected labels: `False`
- Writes policy code: `False`
- Human review options: `needs_more_rules`, `candidate_only`, `promote_to_strict_golden_candidate`, `disregard`

## Family Summary

| Family | Candidates | Phoenix traces | Deterministic mismatches | Direction |
| --- | ---: | ---: | ---: | --- |
| `causal_mechanism` | 2 | 2 | 1 | Require a stated causal bridge. Inputs such as hardware, funding, regulation, rates, or energy costs should not become strong market-fit labels without a resolution rule that tests the downstream claim. |
| `composite_thesis` | 3 | 3 | 2 | Detect compound claims. Markets that resolve only one material component should be marked partial coverage and sent to review before promotion. |
| `entity_mismatch` | 2 | 2 | 2 | Tighten entity, product, and version matching. Same ecosystem is not enough when the market resolves a different company, model family, or version. |
| `event_stage_mismatch` | 4 | 4 | 1 | Strengthen stage-awareness checks. Distinguish preparation, filing, roadshow, pricing, completion, and post-event valuation before assigning indirect or stronger fit. |
| `horizon_mismatch` | 3 | 3 | 1 | Require explicit horizon alignment. A related market in the wrong year should stay weak_proxy or no_clean_expression unless the thesis clearly states an overlapping milestone. |
| `inverse_framing` | 3 | 3 | 2 | Add an outcome-polarity review cue. Inverted markets may be useful, but the system must state which outcome supports the thesis and avoid treating inverse framing as direct evidence. |
| `metric_mismatch` | 2 | 2 | 0 | Separate evidence metric from resolution metric. Growth, users, margins, or benchmarks may be evidence, but they do not resolve valuation, revenue, release, or price targets by themselves. |

## Top Repeated Patterns

| Count | Family | Expected | Gemini advisory | Deterministic |
| ---: | --- | --- | --- | --- |
| 3 | `event_stage_mismatch` | `indirect` | `weak_proxy` | `indirect` |
| 2 | `metric_mismatch` | `indirect` | `weak_proxy` | `indirect` |
| 1 | `causal_mechanism` | `no_clean_expression` | `weak_proxy` | `no_clean_expression` |
| 1 | `causal_mechanism` | `weak_proxy` | `no_clean_expression` | `no_clean_expression` |
| 1 | `composite_thesis` | `indirect` | `weak_proxy` | `indirect` |
| 1 | `composite_thesis` | `indirect` | `weak_proxy` | `no_clean_expression` |
| 1 | `composite_thesis` | `no_clean_expression` | `weak_proxy` | `indirect` |
| 1 | `entity_mismatch` | `indirect` | `weak_proxy` | `no_clean_expression` |

## Family Review Queues

### `causal_mechanism`

Candidates: `2`

Review direction: Require a stated causal bridge. Inputs such as hardware, funding, regulation, rates, or energy costs should not become strong market-fit labels without a resolution rule that tests the downstream claim.

Fit-class counts:

- Expected: `no_clean_expression`=1, `weak_proxy`=1
- Gemini advisory: `no_clean_expression`=1, `weak_proxy`=1
- Deterministic: `no_clean_expression`=2

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_cm_energy_cost_vs_ai_scaling_006` | `no_clean_expression` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/22fb866607f49840d1f03a21c094a4df) | Energy cost thesis is about economics of future model scale, not current leaderboard rankings. |
| `stress_cm_vc_funding_vs_capex_002` | `weak_proxy` | `no_clean_expression` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/604a99b52abac250ceb4bce8d50cfd49) | VC funding share and ROI concerns are about the entire AI ecosystem, not one company's capex. |

### `composite_thesis`

Candidates: `3`

Review direction: Detect compound claims. Markets that resolve only one material component should be marked partial coverage and sent to review before promotion.

Fit-class counts:

- Expected: `indirect`=2, `no_clean_expression`=1
- Gemini advisory: `weak_proxy`=3
- Deterministic: `indirect`=2, `no_clean_expression`=1

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_ct_ai_coding_bar_002` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/a07ea87787fc2178f0901dc4bf89eeda) | The market resolves only the bar exam half. The coding jobs half is unaddressed. Partial coverage of a compound thesis. |
| `stress_ct_crypto_etf_regulation_004` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/4e5cb852d41f4ba75b2367cf484d8e66) | ETF approval is the central claim, but custody rules are a material second condition that the market does not resolve. |
| `stress_ct_us_china_ai_trade_005` | `no_clean_expression` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/8910dc881d3e2a5aee50f24d5671eeb8) | Market resolves only the US action. The thesis requires both US restriction AND Chinese retaliation. Neither alone is the full claim. |

### `entity_mismatch`

Candidates: `2`

Review direction: Tighten entity, product, and version matching. Same ecosystem is not enough when the market resolves a different company, model family, or version.

Fit-class counts:

- Expected: `indirect`=1, `weak_proxy`=1
- Gemini advisory: `no_clean_expression`=1, `weak_proxy`=1
- Deterministic: `no_clean_expression`=2

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_em_claude_48_vs_claude_5_001` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/f928b75b9d2a22c6697c79d31fbe1c9e) | Same product family but different version. Claude 4.8 availability does not resolve Claude 5 release. |
| `stress_em_microsoft_copilot_vs_openai_005` | `weak_proxy` | `no_clean_expression` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/9889813463b0ebbf756ddb0f28d49f03) | Microsoft Copilot uses OpenAI models, so adoption may help OpenAI revenue, but it's a different entity and indirect causation. |

### `event_stage_mismatch`

Candidates: `4`

Review direction: Strengthen stage-awareness checks. Distinguish preparation, filing, roadshow, pricing, completion, and post-event valuation before assigning indirect or stronger fit.

Fit-class counts:

- Expected: `indirect`=3, `no_clean_expression`=1
- Gemini advisory: `indirect`=1, `weak_proxy`=3
- Deterministic: `indirect`=4

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_es_anthropic_ipo_rumor_vs_no_ipo_008` | `no_clean_expression` | `indirect` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ea2b6c7c3643c69d5a49ee6c94d9563f) | 18-month plan extends well beyond June 2026. The market's horizon does not match the thesis timeline. |
| `stress_es_databricks_pricing_vs_cap_006` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/275c514bf626f6d6e9f3d98957b14736) | Pricing range is strong evidence but the market resolves on a specific cap threshold, not the pricing event. |
| `stress_es_openai_roadshow_vs_timing_002` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ea2cb5d431bbf432e9dcd4a2fd8206fe) | Roadshow is strong directional evidence for IPO completion, but not the same event. Indirect, not direct. |
| `stress_es_spacex_underwriters_vs_largest_004` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/4c9ed979c88721d6e77190abf64608b1) | Hiring underwriters is strong preparation evidence, but does not guarantee completion or largest-IPO ranking. |

### `horizon_mismatch`

Candidates: `3`

Review direction: Require explicit horizon alignment. A related market in the wrong year should stay weak_proxy or no_clean_expression unless the thesis clearly states an overlapping milestone.

Fit-class counts:

- Expected: `indirect`=2, `no_clean_expression`=1
- Gemini advisory: `weak_proxy`=3
- Deterministic: `indirect`=1, `no_clean_expression`=2

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_hm_climate_2050_vs_carbon_2026_003` | `no_clean_expression` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/79439a909b61fe11278a289e8b97b250) | 2050 emissions target vs 2026 policy action. Extreme horizon mismatch plus different metric. |
| `stress_hm_fed_2028_vs_2026_cuts_001` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/f68836dd3fce65e2150b8f140c81382d) | Same institution, same action, but the thesis is about 2028. The 2026 market tests only part of the claim. |
| `stress_hm_fusion_2035_vs_2026_005` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/992ea5eafb67fc6d8865918a63afa7f0) | Net energy demo is an early milestone on the path to commercial grid connection, but 2035 vs 2026. |

### `inverse_framing`

Candidates: `3`

Review direction: Add an outcome-polarity review cue. Inverted markets may be useful, but the system must state which outcome supports the thesis and avoid treating inverse framing as direct evidence.

Fit-class counts:

- Expected: `indirect`=2, `weak_proxy`=1
- Gemini advisory: `indirect`=1, `weak_proxy`=2
- Deterministic: `indirect`=1, `no_clean_expression`=2

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_if_anthropic_ipo_momentum_vs_no_ipo_001` | `weak_proxy` | `indirect` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/1cb22bb86d474309efd70d1c8cc52579) | The market is framed as the ABSENCE of the event. Valuation momentum does not directly resolve IPO timing. |
| `stress_if_fed_hold_vs_cut_003` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/63e1ecb1a93150e4d85cb96d7691e8b2) | The thesis says NO cuts. The market asks about a specific cut. The No outcome supports the thesis but the framing is inverted. |
| `stress_if_housing_crash_vs_price_up_002` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/5ddad0765058cdf52ea3c30ac791997d) | Bearish thesis vs bullish market framing. The No outcome would support the thesis, but the market doesn't directly resolve overpricing. |

### `metric_mismatch`

Candidates: `2`

Review direction: Separate evidence metric from resolution metric. Growth, users, margins, or benchmarks may be evidence, but they do not resolve valuation, revenue, release, or price targets by themselves.

Fit-class counts:

- Expected: `indirect`=2
- Gemini advisory: `weak_proxy`=2
- Deterministic: `indirect`=2

| Case | Expected | Gemini | Deterministic | Trace | Trap |
| --- | --- | --- | --- | --- | --- |
| `stress_mm_anthropic_revenue_vs_valuation_001` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/315e82dde8c35b341a649f24a25a570f) | Revenue growth is strong evidence for valuation, but revenue ≠ valuation. Different metric. |
| `stress_mm_meta_users_vs_revenue_004` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/b39452d9c60807b7345d6ae4b77979ec) | User count is evidence for revenue potential, but users ≠ revenue. Monetization is uncertain. |

## Review Contract

- `needs_more_rules`: repeated failure looks real enough to write a targeted prompt or deterministic policy proposal.
- `candidate_only`: keep as stress evidence but do not promote to strict goldens.
- `promote_to_strict_golden_candidate`: reviewer believes the case can become a defensible frozen eval.
- `disregard`: synthetic trap is unrealistic, duplicate, malformed, or not useful.

No policy code, strict expected labels, or golden fixtures were mutated by this batch.
