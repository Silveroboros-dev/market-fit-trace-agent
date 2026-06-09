# Top Candidate NO-GO: `event_stage_mismatch`

## Decision

- Verdict: `no_go`
- Ship decision: `candidate_only` (`candidate_only / no_go_for_shipping`)
- Reduces real danger: `False`
- Safety invariants hold: `False`

NO-GO for shipping. The top guard reduces no direct false positives (no real danger to remove) and violates safety invariants (gov_001_invariant, no_gemini_owned_final_class, twin_safety). It only nudges deterministic classes toward a debatable synthetic stress label that matches Gemini's advisory call, contradicting the gov_001 hero golden and damaging correctly classified twins. Keep candidate-only.

## Why This Candidate Ranked First

- Review candidates: `4`
- Direct false positives in family: `0`
- Hero-cluster overlap: `True`
- Dangerousness / demo / stability / testability: `4` / `6` / `1.00` / `1.00`

## Drafted Patch Plan (NOT applied)

This plan is a proposal only. `applied = False`. No prompt, policy, golden, or expected-output file is modified by this loop.

### Prompt guardrail candidate

Target (human-approved patch only): `app/prompts.py`

Before assigning `indirect` or stronger, verify that the market resolves the same event stage as the thesis. Preparation, confidential filing, roadshow, pricing, IPO completion, and post-IPO valuation are different stages. If stage differs materially, downgrade to `weak_proxy` or `no_clean_expression`.

### Deterministic guard candidate

- Name: `event_stage_alignment_guard`
- Target (human-approved patch only): `app/policy/fit.py`
- Proposed behavior: Detect mismatched IPO/startup stages in claim and resolution rules. If the claim is about filing/preparation and the market resolves completion or valuation, cap fit at `weak_proxy` or `no_clean_expression` depending on horizon.

- Prior review direction: Strengthen stage-awareness checks. Distinguish preparation, filing, roadshow, pricing, completion, and post-event valuation before assigning indirect or stronger fit.

### Predicted effect on committed rows

- Relabel: `indirect` -> `weak_proxy`
- Affected cases: `stress_es_anthropic_ipo_rumor_vs_no_ipo_008`, `stress_es_databricks_pricing_vs_cap_006`, `stress_es_openai_board_vs_ipo_007`, `stress_es_openai_filing_vs_completion_001`, `stress_es_openai_roadshow_vs_timing_002`, `stress_es_spacex_underwriters_vs_largest_004`, `stress_es_stripe_s1_vs_ipo_005`

## Gate Results

| Gate | Status | Detail |
| --- | --- | --- |
| `direct_false_positive_reduction` | FAIL | Deterministic direct false positives: 0 -> 0 (reduction 0). The guard reduces no direct false positives; there are none to reduce. |
| `twin_safety` | FAIL | 3 correctly classified 'good twin' case(s) would be downgraded as collateral; the guard cannot separate them from the bad twins by claim text. |
| `tpu_hero_invariant` | PASS | The guard scope is IPO event-stage; it touches no TPU governance anchor or TPU stress case, so the TPU hero is preserved. |
| `gov_001_invariant` | FAIL | gov_001 golden-labels the filing-vs-completion thesis 'indirect'. The guard would downgrade 'indirect' -> 'weak_proxy', regressing gov_001 and 8 hero-cluster 'indirect' golden(s). |
| `no_auto_promotion` | PASS | The plan is unapplied and every output stays under evals/repair_loop/; nothing is promoted to strict goldens. |
| `no_gemini_owned_final_class` | FAIL | On 4 case(s) the guard makes the deterministic class adopt Gemini's advisory label; that lets the model own the final class. |
| `overclaim` | PASS | Confirmed direct-band overclaims: 0 -> 0. The guard introduces none; there are none to retire, so this is no shipping justification. The debatable strong-over-weak/no band is review evidence, not a confirmed overclaim. |

## Remaining Risks / Follow-ups

- The four event-stage review candidates remain candidate-only evidence in Phoenix; they are not promoted to strict goldens.
- If a future run shows a deterministic *direct* false positive in this family, re-run this loop: the danger gate would then have something real to reduce.
- Any guard must be twin-safe (preserve the good `indirect` twins) and must not regress the gov_001 hero golden before it can ship.
- The deterministic gate stays the classifier of record; Gemini remains advisory and must never own the final class.
