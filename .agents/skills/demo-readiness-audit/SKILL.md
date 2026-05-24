---
name: demo-readiness-audit
description: Audit whether a hackathon prototype is demo-ready, replayable, judge-readable, and supported by tests or evidence.
---

# Demo Readiness Audit

Audit the project as if it will be judged today.

## Required Output

1. Demo story in one paragraph
2. Exact demo path
3. Commands that must work
4. Claims supported by working software
5. Claims not yet supported
6. Fragile setup points
7. Judge confusion risks
8. Final fix list in priority order

## Rules

- Be strict. A feature that cannot be shown reliably does not count.
- Check README, setup, scripts, fixtures, tests, and visible UI/API behavior.
- Prefer fixing demo-breaking issues over adding features.
- Identify any claim that sounds better than the implementation.

