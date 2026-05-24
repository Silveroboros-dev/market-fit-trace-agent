---
name: api-spike-benchmark
description: Design and implement the smallest code spike to verify uncertain API, SDK, model, database, latency, or integration behavior.
---

# API Spike Benchmark

Create the smallest reproducible test for an uncertain technical assumption.

## Required Output

1. Assumption being tested
2. Minimal test design
3. Files/scripts to create or modify
4. Command to run
5. Expected pass/fail signal
6. Result interpretation
7. Fallback if the test fails

## Rules

- Do not build full product code.
- Do not hide uncertainty behind architecture diagrams.
- Use fixtures or mock data unless real API access is required.
- Prefer one script that can be run from the command line.
- Save results in a clear location if useful, e.g. `spikes/results/`.

