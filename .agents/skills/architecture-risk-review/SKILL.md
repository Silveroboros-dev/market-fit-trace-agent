---
name: architecture-risk-review
description: Review a proposed architecture for API limits, integration risk, over-engineering, missing tests, and hackathon feasibility. Use before committing to core system design.
---

# Architecture Risk Review

Review the proposed design as a senior software architect.

## Required Output

1. Architectural assumptions
2. Data and logic flow
3. Highest-risk integration points
4. Over-engineering or under-engineering warning
5. Strongest competing architecture
6. Cheapest validation test
7. Decision rule
8. Confidence level

## Rules

- Separate API/data constraints from application architecture and hackathon strategy.
- Do not accept vague claims such as "agentic", "real-time", "auditable", or "scalable" without implementation meaning.
- If API behavior is unknown, propose a spike test.
- Prefer a vertical slice that can be demoed over a broad platform that cannot be finished.
- End with a concrete proceed/pivot/defer recommendation.

