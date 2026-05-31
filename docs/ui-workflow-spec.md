# UI Workflow Specification

This document is the product contract for the FastAPI demo UI. It prevents the
run workspace, candidate triage queue, human review, promotion, and strict eval
surfaces from borrowing state from each other.

## Surfaces

### Current Run Workspace

The top workspace is bound only to the current `/api/runs` result.

It may show:

- the source text entered by the user;
- source-assisted candidate rows loaded from staged eval candidate packs, where
  the source text and provenance are the evidence anchor but proposed fit labels
  are not canonical truth;
- the normalized claim returned for that run;
- the bounded retrieved market context for that run, using strict golden
  fixture context when the source text exactly matches a promoted golden;
- the deterministic market-fit decision;
- supporting outcome and polarity when the recommended binary market is an
  inverse expression of the thesis, e.g. `supporting_outcome=No`;
- the Phoenix trace link, run ID, prompt version, and deterministic eval result;
- a run-level reviewer recommendation draft that is local/read-only and does
  not write ledger events, Dataset rows, candidate review files, or strict
  expected labels;
- an optional current-run candidate packet created explicitly from the current
  run, if the user asks for LLM triage or promotion review.

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
7. A current-run candidate packet is identified by `case_id` and must be created
   explicitly from the active `run_id`; it is not inferred from the existing
   candidate queue.
8. Human review in the UI writes only candidate review status after the
   explicit candidate review gate. A `promote` review means eligible for later
   frozen strict-golden promotion; it does not directly mutate strict expected
   labels.
9. A source-assisted input row is identified by `source_case_key`
   (`pack::example_id`) and may prefill source text and provenance only. Its
   proposed expected fit is advisory until a current run, candidate packet, and
   human review exist.
10. A current-run reviewer recommendation is identified by the active `run_id`
    only and is a local draft. It must not call `/api/verdicts`, write
    `human_verdict_recorded`, create `review_decision.json`, or affect
    promotion eligibility.

## Workflow Contract

The intended governance flow is:

```text
current run source text
-> optional source-assisted source/provenance row
-> bounded retrieved markets shown on the run screen
-> deterministic policy/eval shown on the run screen
-> optional export as current-run candidate packet
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

Run-level reviewer recommendations are read-only drafts, not persisted human
verdicts or promotion decisions. Candidate promotion status is shown only in the
existing candidate queue and is derived from candidate human review status.

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

### AC-11: Trace-Inspected Runs Require Phoenix Inspection

The normal UI must not let users choose `v2_trace_inspected` as a first run.
Trace-inspected reruns must be created only through
`/api/runs/{run_id}/improve`, after the first run has produced a trace and eval
failure context and Phoenix MCP can inspect that trace. The normal UI must not
silently use `local_eval_fallback` as if it were sponsor trace inspection.
Developer-only controls may exist elsewhere, but the judge demo path is:

```text
Run agent -> inspect Phoenix trace -> rerun
```

### AC-12: Candidate Packet Shows Source, Normalization, Eval Trace

Every candidate packet detail view must show the initial source text, normalized
thesis, run ID, Phoenix trace ID or trace link, fit class, eval metrics, and
failure summary when present. These fields must come from that packet's
`run_result.json` or Dataset row, not from the active run unless the packet was
explicitly created from that run.

### AC-13: Current Run Can Create Advisory Candidate Triage

After a current run completes, the UI may ask whether to create a candidate
packet and run LLM triage. If the user says yes, the app must write a candidate
packet for the active `run_id`, write `llm_review_suggestion.json`, bind the
advisory scores to the active current-run market rows, and label the suggestion
as advisory. This action must not open the candidate promotion-review console.

### AC-14: LLM Triage Includes Market Ranking Scores

The LLM triage view must show one numeric advisory ranking score per retrieved
market. These scores are review-priority hints only and must not be rendered as
strict fit labels, best-market truth, or CI pass/fail.

### AC-15: Human Promotion Review Target Is Explicit

When the UI asks whether to review a thesis for promotion, it must state that
the review writes `review_decision.json` for the candidate packet. `promote`
means eligible for a later explicit frozen strict-golden promotion; the UI must
also state that it does not mutate `expected_outputs.jsonl`.

### AC-16: Source-Assisted Candidate Loader Preserves Truth Boundary

The UI may offer a `Load source-assisted candidate` control backed by staged
candidate eval packs. Selecting a row must fill the source-text box with exact
saved source text and show source provenance, but it must not auto-run the
agent, open triage, open human review, or treat proposed expected labels as
strict truth. If a source-assisted row is exported as a current-run candidate
packet, `source.json` must preserve the source-assisted pack, `example_id`,
provenance, and truth-scope metadata.

### AC-17: Missing Phoenix MCP Is a Visible Failed Dependency

If `/api/runs/{run_id}/improve` cannot obtain real Phoenix MCP inspection, the
normal UI must show an explicit unavailable/error state and must not create a
second `v2_trace_inspected` run from `local_eval_fallback`. Offline fallback may
exist only as an explicit developer/test opt-in, never as the default user path.

### AC-18: Candidate Review Console Requires Explicit Review Yes

The current-run LLM triage question and the candidate promotion-review question
are separate gates. Answering yes to `Run LLM triage suggestion?` may score the
retrieved candidate markets, but it must not auto-scroll to or display the
candidate review console. The candidate queue/review workflow may open only
after the user answers yes to `Review candidate for promotion?`.

### AC-19: Current-Run Reviewer Notes Are Read-Only Drafts

The current-run workspace may let a user write a reviewer recommendation note
for reasoning during the demo, including inverse-market observations such as
`No` supporting a thesis. This note is local to the browser surface and must not
POST to `/api/verdicts`, append `human_verdict_recorded`, create
`review_decision.json`, or mutate Phoenix Dataset metadata. Persisted human
review happens only in the candidate review console after the explicit
promotion-review gate.

### AC-20: Inverse Direct Markets Show Supporting Outcome

If deterministic policy classifies an inverse binary market as `direct`, the UI
must show the `supporting_outcome` and `polarity` next to the recommended
market. A `No`-supports-thesis market must not be downgraded to `indirect`
solely because its displayed Yes outcome is the opposite of the thesis.
