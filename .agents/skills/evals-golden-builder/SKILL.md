---
name: evals-golden-builder
description: Create or improve golden test cases and evals for extraction, grounding, policy evaluation, false positive prevention, and demo claims.
---

# Evals Golden Builder

Build evals that prove the system's core trust claim.

## Required Output

1. Claim being evaluated
2. Golden examples needed
3. Fixture schema
4. Expected outputs
5. Negative/adversarial cases
6. Eval command
7. Pass/fail threshold
8. README/demo claim supported by this eval

## Rules

- Include both happy-path and adversarial cases.
- Test false positives, missing evidence, ambiguous evidence, and conflicting evidence.
- Keep evals deterministic where possible.
- If an LLM judge is used, separate model judgment from deterministic pass/fail logic.
- Link every public demo claim to at least one eval or fixture.

