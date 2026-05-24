# Project: Google Cloud Rapid Agent Hackathon Prototype

## Objective

Build a working prototype that proves:

1. Messy prediction-market evidence can become structured, auditable market-fit signals.
2. Gemini may extract, summarize, explain, or propose.
3. Deterministic code performs final policy/evaluation decisions.
4. The Arize/Phoenix track demo is replayable from fixtures and supported by tests/evals.

## Architecture rules

- LLMs do not make final decisions.
- Separate extraction, normalization, verification, policy evaluation, and audit output.
- Every important result must link to evidence, fixture, or source text.
- Prefer one strong end-to-end demo flow over broad unfinished infrastructure.
- Stub integrations that are not central to the judging claim.
- Avoid complex async/stateful flows unless they directly improve the demo.

## Complexity discipline

Treat complexity as a cost. Every service, dependency, state transition, async boundary, agent loop, database, and external API adds failure risk.

Before adding complexity, answer:

- What visible user or judge value does this create?
- What simpler design would prove the same claim?
- What is the cheapest experiment that validates the risky assumption?
- What is the fallback if this fails during the demo?

Prefer architectures with clear causal flow:
input evidence -> extracted signal -> normalized claim -> deterministic verification -> audit output.

## Definition of done

A feature is done only when:

- It runs from a documented command.
- It has a smoke test, unit test, or eval.
- Failure modes are visible.
- The demo path works from a clean checkout.
- README/demo claims match actual behavior.

## Output rules

For planning:
Assumptions -> Recommendation -> Risks -> Cheapest validation test.

For implementation:
Changed files -> Commands run -> Test result -> Remaining risks.
