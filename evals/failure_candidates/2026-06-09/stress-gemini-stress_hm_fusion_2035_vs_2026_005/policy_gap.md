# Stress Gemini Failure Candidate

This packet is candidate-only. It does not mutate strict goldens or policy code.

## Failure Signal

- Case: `stress_hm_fusion_2035_vs_2026_005`
- Family: `horizon_mismatch`
- Expected fit: `indirect`
- Gemini advisory fit: `weak_proxy`
- Deterministic fit: `no_clean_expression`
- Phoenix trace: https://app.phoenix.arize.com/s/rukar570/traces/6db01413475087fe0aa31a2d8ce01672

## Human Review Outcomes

- `needs_more_rules`: treat this as a real policy/prompt gap and write a targeted rule proposal.
- `candidate_only`: keep as stress evidence, but do not promote to a strict golden.
- `promote_to_strict_golden_candidate`: only after a reviewer converts the
  synthetic setup into a defensible frozen eval case.
- `disregard`: drop as synthetic noise or an unrealistic trap.

## Proposed Gap

Gemini advisory classification disagreed with a synthetic expected label. Human review should decide whether this is a real policy blind spot, a prompt issue, or synthetic noise to disregard.

Do not apply this automatically.
