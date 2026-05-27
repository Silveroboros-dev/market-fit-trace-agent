# Phoenix Value Proof

This document is the repeatable proof path for the Arize/Phoenix part of the
Rapid submission.

## Claim

Market Fit Trace Agent gets value from Phoenix because the trace is part of the
agent's correction loop, not only backend logging.

Phoenix is used to make a bad first market-fit judgment visible, inspectable,
and correctable. The agent does not silently rewrite history: the failed first
run, eval annotations, trace inspection, and improved second run are all visible
as artifacts.

## Proof Artifacts

- Live replay command: `make evals-live`
- Phoenix check command: `make phoenix-check`
- Captured audit artifact: `evals/market_fit_v1/v1_trace_audit.md`
- Phoenix MCP config example: `mcp/phoenix_mcp_config.example.json`
- Phoenix Dataset/Experiment artifact:
  `evals/market_fit_v1/phoenix_experiment_result.json`
- Promoted-golden Dataset sync artifact:
  `evals/market_fit_v1/phoenix_promoted_goldens_dataset_result.json`
- Demo run path: `POST /api/runs` -> `POST /api/runs/{run_id}/improve`
- Public trace link for submission:
  `https://app.phoenix.arize.com/s/rukar570/traces/1bd413f984576d145b2dd41b32dc6507`

## Phoenix Dataset / Experiment Spike

This is a small Arize extension, not the core proof path. The stable Phoenix
proof still depends on trace/eval/MCP improvement. The Dataset/Experiment spike
shows that promoted local goldens can also be mirrored into Phoenix and measured
with Phoenix Experiments.

Commands:

```bash
make phoenix-export-candidates
make phoenix-sync-goldens
make phoenix-experiment-goldens
```

Candidate-review Dataset result:

- Dataset: `market_fit_candidate_cases`
- Dataset ID: `RGF0YXNldDoz`
- Latest observed Dataset version ID: `RGF0YXNldFZlcnNpb246OQ==`
- Local artifact:
  `evals/retrieval_candidates/phoenix_candidate_review_dataset_result.json`
- Candidate rows: `5`
- Review status counts: `pending=4`, `needs_more_rules=1`
- Boundary: candidate rows are trace-backed evidence, not strict eval truth.

Observed result:

- Dataset: `market_fit_promoted_goldens_v1`
- Dataset ID: `RGF0YXNldDo0`
- Dataset version ID: `RGF0YXNldFZlcnNpb246NQ==`
- Dataset URL:
  `https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo0`
- Experiment: `current-policy-market_fit_v1-96bedcd`
- Experiment ID: `RXhwZXJpbWVudDo0`
- Experiment URL:
  `https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo0/compare?experimentId=RXhwZXJpbWVudDo0`
- Commit SHA: `96bedcd36783909da1f3a037cba4130ad1554747`
- Eval pack: `market_fit_v1`
- Cases: `10`
- Passed: `10`
- Fit-class accuracy: `1.0`
- Exact market-ID match rate: `0.8`
- Acceptable market match rate: `1.0`
- False-strong recommendation rate: `0.0`
- Weak-proxy detected rate: `0.2`
- Unsupported implication rate: `0.0`
- No-clean-expression false positives: `0 / 4`
- Eval-metrics pass rate: `1.0`

Boundary:

- Local frozen fixtures remain the strict eval source of truth.
- Phoenix Dataset mirrors promoted cases for comparison and inspection.
- Phoenix Experiment compares current policy output against expected labels.
- Experiment metrics are code evaluators, not LLM-as-judge decisions.
- Strict Phoenix experiments use fixture markets, not live PolyData retrieval.

## Product Flow

```text
messy thesis
-> Google ADK / Gemini proposal
-> deterministic market-fit policy check
-> Phoenix/OpenInference trace
-> trace-linked eval annotations
-> Phoenix MCP trace inspection in live mode
-> improved second run
-> ledger record of both attempts
```

In live submission mode, the improve step uses Phoenix MCP to inspect the failed
trace/eval context. For offline local reproduction without Phoenix credentials,
the app can replay the same trace-linked eval record through a deterministic
fallback.

The key architecture claim is:

- Gemini proposes.
- Deterministic code verifies.
- Phoenix makes the failure visible and usable for improvement.
- The ledger records the lifecycle.

## Pass Conditions

The Phoenix value proof passes only if all are true:

1. `make evals-live` runs the v1 golden pack through live ADK/Gemini.
2. A Phoenix trace is created for at least one demo or eval run.
3. The trace has a visible `fit_eval_run` span or equivalent product-level eval
   span.
4. The trace includes `schema_valid`, `false_strong_recommendation`,
   `weak_proxy_detected`, and `unsupported_implication` annotations or verified
   trace-linked eval fields.
5. The improve step reads trace/eval context through Phoenix MCP in live mode.
6. The improve response reports `inspection_source: phoenix_mcp`.
7. The improve response reports `fallback_used: false`.
8. The second run changes an over-strong recommendation into `weak_proxy` on
   the seed demo.
9. The false-strong eval clears after the second run.
10. The ledger records both the initial run and the trace-informed rerun.
11. The same `run_id`, `trace_id`, and `case_id` are visible across the app
    response, Phoenix trace, `fit_eval_run` span, eval annotation record, ledger
    event, and `/api/runs/{run_id}/improve` response. For manual UI demos, use
    `manual_demo_seed` as the case identity.

## Fail Conditions

The Phoenix value proof fails if any of the following are true:

- No Phoenix trace is created for the live run.
- The Phoenix trace is stale or does not match the current `run_id` / `trace_id`.
- The live improve step uses `local_eval_fallback`.
- Phoenix contains generic ADK/Gemini spans but no product-level eval span.
- Required eval annotations are only present in local files and not visible
  through Phoenix or `make phoenix-check`.
- The second run changes text but does not change the fit classification or
  clear the false-strong eval.

## Prerequisites

Configure `.env` with live Google and Phoenix credentials:

```bash
GOOGLE_ADK_ENABLED=true
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash

PHOENIX_PROJECT_NAME=market_fit_trace_agent
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space>/v1/traces
PHOENIX_BASE_URL=https://app.phoenix.arize.com/s/<space>
PHOENIX_API_KEY=...
PHOENIX_MCP_ENABLED=true
```

Create Phoenix annotation configs once per Phoenix workspace:

```bash
make phoenix-ensure
```

## Endpoint Configuration Notes

Phoenix uses two endpoint concepts in this repo:

- `PHOENIX_BASE_URL`: Phoenix application/API base URL used for trace lookup,
  annotation setup, and Phoenix MCP.
- `PHOENIX_COLLECTOR_ENDPOINT`: trace collection endpoint used by the tracing
  setup.

This repo expects `PHOENIX_COLLECTOR_ENDPOINT` to match the code path in
`app/tracing.py` and `market_fit_adk/agent.py`. If using direct OTLP collection,
include `/v1/traces`. If using Phoenix wrapper defaults from a workspace setup,
use the endpoint shape expected by that wrapper and confirm with
`make phoenix-check`.

## Phoenix MCP Configuration

The example MCP config is checked in at:

```text
mcp/phoenix_mcp_config.example.json
```

It configures the Phoenix MCP server with `PHOENIX_BASE_URL` and
`PHOENIX_API_KEY`. The app-level subprocess mode enables this path with:

```bash
PHOENIX_MCP_ENABLED=true
PHOENIX_MCP_COMMAND=npx
PHOENIX_MCP_ARGS="-y,@arizeai/phoenix-mcp@latest"
```

`PHOENIX_MCP_ARGS` is comma-separated because `app/config.py` parses it into an
argv list for the subprocess call.

## Baseline Trace Replay

Replay the original 10 v1 goldens through live ADK/Gemini and Phoenix:

```bash
make evals-live
make phoenix-check
```

Expected `make evals-live` result:

```json
{
  "status": "passed",
  "mode": "live",
  "eval_pack": "market_fit_v1",
  "case_count": 10,
  "passed_count": 10
}
```

`make phoenix-check` must verify:

- the inspected trace is in project `market_fit_trace_agent`;
- the requested or latest relevant trace exists;
- the trace contains the required product-level eval span;
- the required annotation configs exist;
- the required eval annotations exist on the eval span;
- no required annotations are missing.

It should confirm required spans and annotations rather than a fixed span count:

```json
{
  "status": "ok",
  "project": "market_fit_trace_agent",
  "trace_found": true,
  "required_spans_found": ["fit_eval_run"],
  "required_spans_missing": [],
  "required_annotations_found": [
    "schema_valid",
    "false_strong_recommendation",
    "weak_proxy_detected",
    "unsupported_implication"
  ],
  "required_annotations_missing": []
}
```

The captured v1 replay artifact is:

```text
evals/market_fit_v1/v1_trace_audit.md
```

In this repo, eval outcomes are written as Phoenix annotations when Phoenix
credentials are configured, not only as local JSON fields. `make phoenix-check`
verifies those annotations on the `fit_eval_run` span.

## Demo Trace-Improvement Path

Start the local app:

```bash
make api
```

Open:

```text
http://127.0.0.1:8000
```

Use the default demo thesis:

```text
Google TPU claims mean Gemini will close the gap with frontier models this year.
Find the best prediction-market expression and tell me whether the market is a
clean fit.
```

Demo steps:

1. Click **Run agent** with `First run`.
2. Show the agent extracted a thesis and found a tempting related market.
3. Show the eval panel: false-strong / weak-proxy metrics are attached to the run.
4. Open the Phoenix trace link and show the `fit_eval_run` span.
5. Click **Inspect trace and rerun**.
6. Show the second run downgrades the tempting market to `weak_proxy`.
7. Show the ledger events include the trace inspection and updated run.

Expected product behavior:

```text
before: tempting adjacent market overstates fit
after: weak_proxy classification, false-strong eval clears
```

Expected improve response shape for the live proof:

```json
{
  "before_run_id": "run_...",
  "after_run_id": "run_...",
  "before_trace_id": "trace_...",
  "after_trace_id": "trace_...",
  "inspection_source": "phoenix_mcp",
  "fallback_used": false,
  "before_fit": "indirect",
  "after_fit": "weak_proxy",
  "false_strong_recommendation_before": true,
  "false_strong_recommendation_after": false
}
```

If `inspection_source` is `local_eval_fallback`, the Arize/Phoenix live proof has
not passed. The fallback only proves offline reproducibility.

## 90-Second Judge Demo Script

1. Start with the default thesis:
   `Google TPU claims mean Gemini will close the gap with frontier models this year.`
2. Click **Run agent**.
3. Show the first run:
   normalized thesis, tempting related market, first-run fit classification, and
   eval warning for false-strong / weak-proxy risk.
4. Open the Phoenix trace:
   show the `fit_eval_run` span and annotations for `false_strong_recommendation`
   and `weak_proxy_detected`.
5. Click **Inspect trace and rerun**.
6. Show the second run:
   classification changes to `weak_proxy`, false-strong eval clears, and the
   ledger records trace inspection plus the updated run.
7. Close with:
   Phoenix did not merely log the run. It supplied the failure context that the
   agent used to improve the next run.

## Responsibility Boundary

| Layer | Responsibility | Does Not Do |
|---|---|---|
| Gemini / ADK | Draft normalized claim, entities, horizon, stance, and market-fit proposal | Make final trust decision |
| Deterministic policy | Enforce market-fit classification rules and eval pass/fail | Generate open-ended reasoning |
| Phoenix / OpenInference | Capture spans, eval annotations, trace links, and failure context | Replace policy enforcement |
| Phoenix MCP | Retrieve trace/span/annotation context for the improve step | Guarantee correctness by itself |
| Ledger MCP | Record claim lifecycle and optional human verdicts | Act as the sponsor MCP integration |

## Phoenix MCP vs OpenInference MCP Tracing

Phoenix MCP and OpenInference MCP tracing are different integration layers:

- Phoenix MCP lets the app inspect Phoenix project data such as traces, spans,
  annotations, prompts, datasets, and experiments.
- OpenInference MCP tracing propagates trace context across MCP client/server
  boundaries. It does not create useful telemetry unless the client/server code
  also emits spans.

This proof relies on Phoenix/OpenInference-compatible spans for the agent run
and Phoenix MCP trace inspection for the live improve step.

## Failure / Fallback Behavior

The local fallback is only an offline reproduction path.

If `PHOENIX_MCP_ENABLED=true` and Phoenix MCP returns trace data, the inspection
source is `phoenix_mcp`. If a reviewer cannot configure Phoenix MCP locally, the
app can still replay the trace-linked eval record as `local_eval_fallback` so the
UI and eval path remain reproducible.

Do not present the fallback as equivalent sponsor integration. The submission
proof path is Phoenix MCP in live mode.

## Non-Claims

Do not claim:

- Phoenix replaces the policy layer;
- Gemini alone makes the final trust decision;
- the app gives trading or execution advice;
- draft eval rows become strict goldens because Grok or another external tool found them.
