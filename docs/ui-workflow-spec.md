# UI Workflow Specification

This document is the product contract for the FastAPI demo UI. It prevents the
run workspace, candidate triage queue, human review, promotion, and strict eval
surfaces from borrowing state from each other.

## Surfaces

### Current Run Workspace

The top workspace is bound only to the current `/api/runs` result.

It may show:

- the source text entered by the user;
- the normalized claim returned for that run;
- the bounded retrieved market context for that run, using strict golden
  fixture context when the source text exactly matches a promoted golden;
- the deterministic market-fit decision;
- the Phoenix trace link, run ID, prompt version, and deterministic eval result;
- run-level human verdict controls.

It must not show an LLM candidate triage suggestion unless a candidate packet is
explicitly bound to the current run.

### Existing Candidate Queue

The candidate queue is a separate review surface for exported retrieval
candidate packets. Candidate packets are selected explicitly by `case_id`.

It may show:

- `source.json`;
- `retrieval_result.json`;
- `market_snapshots.jsonl`;
- `llm_review_suggestion.json`;
- Phoenix candidate Dataset metadata;
- `review_decision.json`;
- promotion status derived from human review.

It must not be treated as the current run unless a user explicitly selects a
candidate packet.

## Binding Rules

1. A current run is identified by `run_id`.
2. A candidate packet is identified by `case_id`.
3. The UI must not silently map a current run to the first available candidate.
4. The UI must not open candidate triage for a different `case_id` from the
   source text currently shown in the run workspace.
5. If no candidate packet is bound to the current run, the current-run triage
   gate must say that candidate triage is unavailable for this run.
6. Browsing existing candidate packets must be labeled as browsing an existing
   queue, not as triaging the current run.

## Workflow Contract

The intended governance flow is:

```text
current run source text
-> bounded retrieved markets shown on the run screen
-> deterministic policy/eval shown on the run screen
-> optional export as candidate packet outside this UI
-> optional llm_review_suggestion.json for that candidate packet
-> Phoenix candidate Dataset metadata mirror
-> human review_decision.json
-> promoted frozen fixture only if human status is promote
-> deterministic strict eval
```

## Acceptance Criteria

### AC-1: Current Run Markets Are Visible

After a run completes, the run screen must show the actual retrieved market rows
from `run.market_context`, not only the count.

### AC-2: No Implicit Candidate Triage

If a current run has no bound candidate packet, the run screen must not offer a
button that opens `llm_review_suggestion.json` for any existing candidate.

### AC-3: No Silent Candidate Switch

Opening or browsing the candidate queue from the run screen must not set
`state.workflow.screen = "triage"` and must not select `demo-hormuz-candidate`
or any other candidate automatically.

### AC-4: Explicit Candidate Selection

The candidate queue must start with no selected candidate unless a user has
already selected one. The user must choose a `case_id` before candidate packet
details, LLM triage, or review console content appears.

### AC-5: Human Review Authority

Run-level verdict controls are not promotion decisions. Candidate promotion
status is shown only in the existing candidate queue and is derived from
candidate human review status.

### AC-6: Strict Eval Boundary

No UI action mutates promoted fixture `expected_outputs.jsonl` files. Strict
eval remains deterministic and fixture-backed.

### AC-7: Run-Scoped Eval Metrics

The eval/trace panel must identify the active `run_id`, Phoenix `trace_id`,
prompt version, and fit class. Metric cards in that panel must be rendered from
the current `/api/runs` or `/api/runs/{run_id}/improve` response, not from the
candidate Dataset export.

### AC-8: Dataset Totals Are Labeled Global

The existing candidate queue may show Phoenix candidate Dataset totals, but the
cards must be labeled as Dataset-wide and independent from the active run.
Starting a new run or trace-inspection rerun must clear any selected existing
candidate packet so stale candidate metadata cannot look attached to the new
thesis.

### AC-9: Exact Golden Replay Uses Frozen Fixture Context

When the current run source text exactly matches a strict promoted golden, the
UI-backed `/api/runs` path must use the golden's frozen market fixture context
instead of the generic demo seed market list. First run and trace-inspected rerun
must both show only market IDs listed by that golden's expected fit metadata.

### AC-10: Strict Golden Loader Is Manual

The UI may offer a `Load strict golden` control that fills the source-text box
with exact promoted-golden text. Selecting a golden must not auto-run the agent,
open candidate triage, open human review, or promote anything. If the loaded text
is edited, the UI must warn that exact golden replay may no longer apply.
