# Stress Gemini Failure Candidate

This packet is candidate-only. It does not mutate strict goldens or policy code.

## Failure Signal

- Case: `stress_ct_us_china_ai_trade_005`
- Family: `composite_thesis`
- Expected fit: `no_clean_expression`
- Gemini advisory fit: `weak_proxy`
- Deterministic fit: `indirect`
- Phoenix trace: https://app.phoenix.arize.com/s/rukar570/traces/8910dc881d3e2a5aee50f24d5671eeb8

## Human Review Outcomes

- `needs_more_rules`: treat this as a real policy/prompt gap and write a targeted rule proposal.
- `candidate_only`: keep as stress evidence, but do not promote to a strict golden.
- `promote_to_strict_golden_candidate`: only after a reviewer converts the
  synthetic setup into a defensible frozen eval case.
- `disregard`: drop as synthetic noise or an unrealistic trap.

## Proposed Gap

Gemini advisory classification disagreed with a synthetic expected label. Human review should decide whether this is a real policy blind spot, a prompt issue, or synthetic noise to disregard.

Do not apply this automatically.
