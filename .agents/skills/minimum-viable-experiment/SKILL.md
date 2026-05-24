---
name: minimum-viable-experiment
description: Design the smallest code spike, curl command, or benchmark that validates a risky technical assumption.
---

# Minimum Viable Experiment

Use this skill when an idea depends on uncertain API behavior, model performance, latency, schema stability, retrieval quality, or integration feasibility.

## Required output

1. Assumption to test
2. Minimal experiment
3. Input fixture
4. Command or script
5. Pass/fail criterion
6. Result interpretation
7. Fallback if it fails

## Rules

- Do not build product code.
- Keep the experiment as small as possible.
- Prefer local fixtures unless live API behavior is the uncertainty.
- Make the output repeatable.
- Save results if they support a README or demo claim.

