# Implementation Plan

## Phase 1: Thin Vertical Slice

Goal:

One thesis -> one market-fit judgment -> optional human verdict -> one ledger write.

Tasks:

- initialize new public repo;
- choose FastAPI + Streamlit or FastAPI + Next.js;
- implement Gemini-backed claim extraction;
- load a small fixed market snapshot from JSON;
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

## Phase 4.5: Bounded Dynamic Market Retrieval

Goal:

Make the answer space stronger without scanning the whole market universe for
every user request.

Tasks:

- read recent Polymarket market snapshots from the PolyData / poly-data-explorer
  surface when credentials are present;
- start with a simple universe filter: open markets with liquidity, open
  interest, or volume proxy above USD 10,000;
- narrow the search space with taxonomy/category buckets, embeddings, or
  similarity indexes instead of scanning all markets per request;
- pass only the bounded relevant market set to the fit reasoner;
- freeze the retrieved market set and rules for formal eval replay;
- evaluate retrieval quality separately from final fit classification.

Pass condition:

The app can fetch a current bounded market set for a thesis in live mode, while
strict evals remain replayable from frozen fixtures.

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
- broad live market integration before bounded retrieval works;
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
- one optional human correction;
- one improved second run.
