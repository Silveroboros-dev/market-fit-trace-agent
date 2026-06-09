# Repair-Discovery Loop State

## Scope

Bounded, deterministic, offline repair-discovery loop over the four committed post-patch Stress-40 runs and the Governance-50 goldens. It runs no new Gemini calls, runs no new Stress-40 loops, and writes no prompts, policy code, strict goldens, or expected-output fixtures.

- Schema version: `repair_loop_v0`
- Applies changes: `False`
- Runs new Gemini calls: `False`
- Runs new Stress-40 loops: `False`
- Writes prompts: `False`
- Writes policy code: `False`
- Writes strict expected labels: `False`
- Deterministic run-invariant: `True`
- Deterministic direct false positives (all runs): `0`

## Verdict

**Top candidate:** `event_stage_mismatch`

**Verdict:** `no_go` — ship decision `candidate_only` (`candidate_only / no_go_for_shipping`)

NO-GO for shipping. The top guard reduces no direct false positives (no real danger to remove) and violates safety invariants (gov_001_invariant, no_gemini_owned_final_class, twin_safety). It only nudges deterministic classes toward a debatable synthetic stress label that matches Gemini's advisory call, contradicting the gov_001 hero golden and damaging correctly classified twins. Keep candidate-only.

## Stage 1 — Explorer: Ranked Candidates

Axes: dangerousness (direct false positives dominate), demo value, stability, testability.

| Rank | Family | Review cands | Direct FP | Dangerousness | Demo | Stability | Testability | Score |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `event_stage_mismatch` | 4 | 0 | 4 | 6 | 1.00 | 1.00 | 7.50 |
| 2 | `composite_thesis` | 2 | 0 | 2 | 2 | 1.00 | 1.00 | 3.50 |
| 3 | `horizon_mismatch` | 2 | 0 | 2 | 2 | 1.00 | 1.00 | 3.50 |
| 4 | `metric_mismatch` | 2 | 0 | 2 | 2 | 1.00 | 1.00 | 3.50 |
| 5 | `causal_mechanism` | 1 | 0 | 1 | 1 | 1.00 | 1.00 | 2.00 |

## Stage 2 — Implementer: Drafted Patch Plan (not applied)

- Candidate family: `event_stage_mismatch`
- Applied: `False`
- Prompt target: `app/prompts.py`
- Deterministic guard candidate: `event_stage_alignment_guard` -> `app/policy/fit.py`
- Predicted relabel: `indirect` -> `weak_proxy` for `event_stage_mismatch`
- Predicted affected cases: `stress_es_anthropic_ipo_rumor_vs_no_ipo_008`, `stress_es_databricks_pricing_vs_cap_006`, `stress_es_openai_board_vs_ipo_007`, `stress_es_openai_filing_vs_completion_001`, `stress_es_openai_roadshow_vs_timing_002`, `stress_es_spacex_underwriters_vs_largest_004`, `stress_es_stripe_s1_vs_ipo_005`

> Prompt guardrail (proposed, unapplied): Before assigning `indirect` or stronger, verify that the market resolves the same event stage as the thesis. Preparation, confidential filing, roadshow, pricing, IPO completion, and post-IPO valuation are different stages. If stage differs materially, downgrade to `weak_proxy` or `no_clean_expression`.

## Stage 3 — Verifier: Shipping Gates

| Gate | Status | Detail |
| --- | --- | --- |
| `direct_false_positive_reduction` | FAIL | Deterministic direct false positives: 0 -> 0 (reduction 0). The guard reduces no direct false positives; there are none to reduce. |
| `twin_safety` | FAIL | 3 correctly classified 'good twin' case(s) would be downgraded as collateral; the guard cannot separate them from the bad twins by claim text. |
| `tpu_hero_invariant` | PASS | The guard scope is IPO event-stage; it touches no TPU governance anchor or TPU stress case, so the TPU hero is preserved. |
| `gov_001_invariant` | FAIL | gov_001 golden-labels the filing-vs-completion thesis 'indirect'. The guard would downgrade 'indirect' -> 'weak_proxy', regressing gov_001 and 8 hero-cluster 'indirect' golden(s). |
| `no_auto_promotion` | PASS | The plan is unapplied and every output stays under evals/repair_loop/; nothing is promoted to strict goldens. |
| `no_gemini_owned_final_class` | FAIL | On 4 case(s) the guard makes the deterministic class adopt Gemini's advisory label; that lets the model own the final class. |
| `overclaim` | PASS | Confirmed direct-band overclaims: 0 -> 0. The guard introduces none; there are none to retire, so this is no shipping justification. The debatable strong-over-weak/no band is review evidence, not a confirmed overclaim. |

- Reduces real danger (direct FP or overclaim): `False`
- Safety invariants hold: `False`
- Blocking gates: `direct_false_positive_reduction`, `gov_001_invariant`, `no_gemini_owned_final_class`, `twin_safety`

## How To Read This Loop

- The deterministic gate is the classifier of record and shows zero direct false positives across all four runs. There is no overclaim to retire.
- The top guard would only move `indirect` review candidates toward a debatable synthetic `weak_proxy`/`no_clean_expression` label, which happens to match Gemini's advisory call.
- That move contradicts the gov_001 hero golden (`indirect`) and downgrades correctly classified good twins, so the loop emits NO-GO and keeps the candidate review-only.
