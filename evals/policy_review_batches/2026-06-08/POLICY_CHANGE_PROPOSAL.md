# Policy Change Proposal

Generated at UTC: `2026-06-09T05:47:03.813631+00:00`
Candidate date: `2026-06-08`
Source summary: `evals/failure_candidates/2026-06-08`

## Scope

This is an autonomous proposal artifact generated from clustered candidate failures. It proposes prompt and deterministic-policy changes for human review, but applies none of them.

- Candidate failures reviewed: `19`
- Failure families: `7`
- Writes prompt code: `False`
- Writes policy code: `False`
- Writes strict expected labels: `False`
- Review options: `approve_prompt_only_patch`, `approve_deterministic_guard`, `keep_candidate_only`, `disregard`

## Recommended Sequence

1. Review this proposal as a human-owned patch plan.
2. Approve prompt-only guardrails first, because they are lower risk.
3. Use deterministic guards only for families with repeated policy misses.
4. Rerun stress and full tests before any promotion to strict goldens.

## Priority Families

| Family | Candidates | Policy misses | First action |
| --- | ---: | ---: | --- |
| `composite_thesis` | 3 | 2 | `deterministic_guard_review` |
| `inverse_framing` | 3 | 2 | `deterministic_guard_review` |
| `entity_mismatch` | 2 | 2 | `deterministic_guard_review` |
| `event_stage_mismatch` | 4 | 1 | `prompt_only_patch` |
| `horizon_mismatch` | 3 | 1 | `prompt_only_patch` |
| `causal_mechanism` | 2 | 1 | `prompt_only_patch` |
| `metric_mismatch` | 2 | 0 | `prompt_only_patch` |

## Positive Signals

These families produced Gemini advisory mismatches, but the deterministic gate matched the synthetic expected labels. They are prompt-noise candidates, not evidence that final policy is broken.

| Family | Candidates | Policy misses | Interpretation |
| --- | ---: | ---: | --- |
| `metric_mismatch` | 2 | 0 | Deterministic policy already handled this family in the stress batch. A prompt-only guard may still reduce Gemini advisory noise. |

## Prompt Proposal

Target file for human-approved patch: `app/prompts.py`

Add an explicit market-fit checklist before Gemini assigns `direct`, `indirect`, `weak_proxy`, or `no_clean_expression`.

### `composite_thesis`

For compound claims, list every material condition and check whether the market resolves all of them. If it resolves only one component, classify as partial coverage and avoid strong fit labels.

### `inverse_framing`

If a binary market is framed opposite to the thesis, explicitly identify which outcome supports the thesis before assigning fit. Inverse framing is review guidance, not automatic direct evidence.

### `entity_mismatch`

Verify entity, product family, and version. Same ecosystem or supplier relationship is not enough when the market resolves a different company, model, product version, or venue.

### `event_stage_mismatch`

Before assigning `indirect` or stronger, verify that the market resolves the same event stage as the thesis. Preparation, confidential filing, roadshow, pricing, IPO completion, and post-IPO valuation are different stages. If stage differs materially, downgrade to `weak_proxy` or `no_clean_expression`.

### `horizon_mismatch`

Check whether the thesis horizon overlaps the market close date and resolution window. If the market resolves a materially different year, quarter, or milestone window, do not treat entity/topic overlap as enough for `indirect`.

### `causal_mechanism`

Identify whether the market resolves the thesis outcome or merely one input in a causal chain. Hardware, funding, regulation, rates, and energy costs require an explicit bridge before `indirect`.

### `metric_mismatch`

Check whether the market resolution metric is the thesis metric. Revenue, users, margin, benchmark scores, valuation, release timing, and share price are separate metrics; evidence for one is not resolution of another.

## Deterministic Guard Candidates

These are review candidates for `app/policy/fit.py`. They are not implemented by this script. Prefer prompt-only patches for families where deterministic policy already matched most synthetic labels.

| Family | Guard candidate | Target | Proposed behavior |
| --- | --- | --- | --- |
| `composite_thesis` | `compound_claim_coverage_guard` | `app/policy/fit.py` | Detect material conjunctions in the claim. If a market resolves only one component, label the case as partial coverage and route to review unless local policy has a specific exception. |
| `inverse_framing` | `outcome_polarity_guard` | `app/policy/fit.py` | When market wording is inverse to the thesis, require a supporting outcome and polarity explanation. Do not upgrade fit only because the opposite outcome could be useful. |
| `entity_mismatch` | `entity_version_alignment_guard` | `app/policy/fit.py` | Compare named companies, model families, and versions between claim and market. Cap fit when only ecosystem adjacency is present. |
| `event_stage_mismatch` | `event_stage_alignment_guard` | `app/policy/fit.py` | Detect mismatched IPO/startup stages in claim and resolution rules. If the claim is about filing/preparation and the market resolves completion or valuation, cap fit at `weak_proxy` or `no_clean_expression` depending on horizon. |
| `horizon_mismatch` | `horizon_alignment_guard` | `app/policy/fit.py` | Extract obvious years, quarters, and deadline phrases from claim and resolution text. If they do not overlap, cap fit below `indirect` unless the market tests a named intermediate milestone. |
| `causal_mechanism` | `causal_bridge_guard` | `app/policy/fit.py` | Treat infrastructure, funding, regulation, rates, and cost inputs as weak-proxy candidates unless the resolution rule directly tests the downstream thesis outcome. |
| `metric_mismatch` | `resolution_metric_guard` | `app/policy/fit.py` | Identify metric families such as valuation, revenue, users, margin, release timing, benchmark, and share price. Prevent raw term overlap from producing `indirect` when metric families differ. |

## Evidence Links

### `composite_thesis`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_ct_ai_coding_bar_002` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/a07ea87787fc2178f0901dc4bf89eeda) |
| `stress_ct_crypto_etf_regulation_004` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/4e5cb852d41f4ba75b2367cf484d8e66) |
| `stress_ct_us_china_ai_trade_005` | `no_clean_expression` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/8910dc881d3e2a5aee50f24d5671eeb8) |

### `inverse_framing`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_if_anthropic_ipo_momentum_vs_no_ipo_001` | `weak_proxy` | `indirect` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/1cb22bb86d474309efd70d1c8cc52579) |
| `stress_if_fed_hold_vs_cut_003` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/63e1ecb1a93150e4d85cb96d7691e8b2) |
| `stress_if_housing_crash_vs_price_up_002` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/5ddad0765058cdf52ea3c30ac791997d) |

### `entity_mismatch`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_em_claude_48_vs_claude_5_001` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/f928b75b9d2a22c6697c79d31fbe1c9e) |
| `stress_em_microsoft_copilot_vs_openai_005` | `weak_proxy` | `no_clean_expression` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/9889813463b0ebbf756ddb0f28d49f03) |

### `event_stage_mismatch`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_es_anthropic_ipo_rumor_vs_no_ipo_008` | `no_clean_expression` | `indirect` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ea2b6c7c3643c69d5a49ee6c94d9563f) |
| `stress_es_databricks_pricing_vs_cap_006` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/275c514bf626f6d6e9f3d98957b14736) |
| `stress_es_openai_roadshow_vs_timing_002` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/ea2cb5d431bbf432e9dcd4a2fd8206fe) |
| `stress_es_spacex_underwriters_vs_largest_004` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/4c9ed979c88721d6e77190abf64608b1) |

### `horizon_mismatch`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_hm_climate_2050_vs_carbon_2026_003` | `no_clean_expression` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/79439a909b61fe11278a289e8b97b250) |
| `stress_hm_fed_2028_vs_2026_cuts_001` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/f68836dd3fce65e2150b8f140c81382d) |
| `stress_hm_fusion_2035_vs_2026_005` | `indirect` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/992ea5eafb67fc6d8865918a63afa7f0) |

### `causal_mechanism`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_cm_energy_cost_vs_ai_scaling_006` | `no_clean_expression` | `weak_proxy` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/22fb866607f49840d1f03a21c094a4df) |
| `stress_cm_vc_funding_vs_capex_002` | `weak_proxy` | `no_clean_expression` | `no_clean_expression` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/604a99b52abac250ceb4bce8d50cfd49) |

### `metric_mismatch`

| Case | Expected | Gemini | Deterministic | Trace |
| --- | --- | --- | --- | --- |
| `stress_mm_anthropic_revenue_vs_valuation_001` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/315e82dde8c35b341a649f24a25a570f) |
| `stress_mm_meta_users_vs_revenue_004` | `indirect` | `weak_proxy` | `indirect` | [trace](https://app.phoenix.arize.com/s/rukar570/traces/b39452d9c60807b7345d6ae4b77979ec) |

## Test Plan

- `make test`
- `make run-stress-40`
- `make policy-review-batch`
- `python scripts/build_policy_change_proposal.py`
- Compare new stress_summary.json against the committed baseline.
- Promote only reviewed cases; do not mutate expected_outputs.jsonl here.

## Human Review Decision

- `approve_prompt_only_patch`: implement only the prompt guardrail text.
- `approve_deterministic_guard`: implement a scoped deterministic guard and targeted tests.
- `keep_candidate_only`: keep the evidence but do not change product behavior.
- `disregard`: reject the family or individual cases as synthetic noise.

This proposal does not apply changes. A reviewer must decide which families become patches, which become candidate-only memory, and which get disregarded.
