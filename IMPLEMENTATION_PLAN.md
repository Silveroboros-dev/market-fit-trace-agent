# Implementation Plan

## Phase 1: Thin Vertical Slice

Goal:

One thesis -> one market-fit judgment -> one human verdict -> one ledger write.

Tasks:

- initialize new public repo;
- choose FastAPI + Streamlit or FastAPI + Next.js;
- implement Gemini-backed claim extraction;
- load a small fixed candidate market set from JSON;
- classify fit as direct, indirect, weak proxy, or no clean expression;
- implement Ledger MCP with the smallest useful tools;
- show result and verdict buttons in UI.

Pass condition:

A judge can paste a thesis and see one claim lifecycle.

## Phase 2: Arize-First Instrumentation

Goal:

Every important step appears in Phoenix.

Tasks:

- add OpenInference instrumentation;
- send traces to Phoenix Cloud or self-hosted Phoenix;
- configure Phoenix MCP;
- store `phoenix_trace_id` in agent run records;
- show Phoenix trace link in the UI.

Pass condition:

The same run is inspectable in the app and Phoenix.

## Phase 3: Evals

Goal:

The system catches epistemic market-fit failures.

Tasks:

- create 10 to 20 seed examples;
- add deterministic schema and fit checks;
- add false strong recommendation metric;
- add weak proxy and no-clean checks;
- store eval summary per run;
- surface eval status in UI.

Pass condition:

At least one bad recommendation is visibly caught.

## Phase 4: Self-Improvement Loop

Goal:

The agent uses observability data to improve a second run.

Tasks:

- query Phoenix MCP for failed trace/eval;
- summarize failure cause;
- revise extraction or fit-classification instruction;
- rerun on same thesis;
- show before/after improvement.

Pass condition:

The demo shows a metric moving in the right direction.

## Phase 5: Packaging

Goal:

Submission is credible and testable.

Tasks:

- public GitHub repo;
- OSI-approved license;
- README with setup and env vars;
- hosted Cloud Run URL;
- seed demo data;
- 3-minute video;
- Devpost writeup;
- selected track: Arize.

## Cut Line

Cut aggressively:

- more than 2 agents;
- full Polymarket live integration if snapshots are enough;
- full auth;
- production database migrations if a simple SQLite/Postgres demo works;
- fancy analytics dashboard;
- complete Epistemic Ledger schema;
- 50 evals;
- trading/execution features.

Keep:

- one clear workflow;
- one Phoenix trace;
- one partner MCP use;
- one internal Ledger MCP;
- one bad fit caught;
- one human correction;
- one improved second run.
