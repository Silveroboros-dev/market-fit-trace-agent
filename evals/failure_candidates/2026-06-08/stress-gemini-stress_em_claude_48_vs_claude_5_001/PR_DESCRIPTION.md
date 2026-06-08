# Candidate Policy Proposal: stress_em_claude_48_vs_claude_5_001

## Problem

Gemini advisory classification returned `weak_proxy`
for a case constructed as `indirect`.

## Scope

- Truth scope: synthetic expected label.
- Human review required before promotion.
- Deterministic policy code is unchanged by this packet.

## Review Decision

Choose one: `needs_more_rules`, `candidate_only`,
`promote_to_strict_golden_candidate`, or `disregard`.
