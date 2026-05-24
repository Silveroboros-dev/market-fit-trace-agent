---
name: epistemic-architecture-review
description: Stress-test a proposed architecture for feasibility, state complexity, API assumptions, failure modes, and value-to-complexity ratio.
---

# Epistemic Architecture Review

Use this skill before committing to core architecture, database choice, agent orchestration, MCP design, or Gemini integration.

## Required output

1. Core mechanism
2. Latent assumptions
3. API/data constraints
4. State and integration complexity
5. Value-to-complexity ratio
6. Strongest counter-architecture
7. Falsification test
8. Proceed / pivot / defer recommendation

## Rules

- Translate vague concepts into concrete data flow.
- Flag undocumented API assumptions.
- Identify ornamental architecture.
- Prefer a small vertical slice over a broad platform.
- End with the cheapest test that reduces the biggest uncertainty.

