# Market Fit Trace Agent

_A Gemini + Phoenix agent that audits whether a thesis has a clean prediction-market expression._

Market Fit Trace Agent helps analysts test whether a messy investment, technology, or
market thesis can be expressed through an existing prediction market without creating
a false sense of precision.

Gemini, running through Google ADK, drafts a normalized claim: entities, horizon,
stance, and target outcome. The app retrieves a bounded set of relevant current
Polymarket markets from recent snapshots, then deterministic policy code classifies
the fit as `direct`, `indirect`, `weak_proxy`, or `no_clean_expression`.

The Arize/Phoenix integration is not just logging. Phoenix/OpenInference traces expose
why a market-fit judgment failed, and the improve step uses Phoenix MCP trace context
to rerun the agent with that failure in context.

Market fit here means **prediction-market fit**: whether a market cleanly
expresses the user's thesis.

Selected Rapid track: **Arize**.

## Project Artifacts

- Public repository: [github.com/Silveroboros-dev/market-fit-trace-agent](https://github.com/Silveroboros-dev/market-fit-trace-agent)
- Phoenix trace proof: [v1 trace audit](evals/market_fit_v1/v1_trace_audit.md)
- Phoenix live trace:
  [latest checked trace](https://app.phoenix.arize.com/s/rukar570/traces/1bd413f984576d145b2dd41b32dc6507)
- License: Apache-2.0

## Partner Integration

Phoenix MCP is the partner integration for the Arize track:

- Phoenix/OpenInference traces capture Google ADK, Gemini, and product-level spans.
- Phoenix span annotations record trace-linked evals such as `false_strong_recommendation`
  and `weak_proxy_detected`.
- Phoenix MCP is used during the improve step to inspect failed trace/eval context.
- The local Ledger MCP records claim lifecycle events and optional human verdicts;
  it is a project-local support tool, not the sponsor integration.

This maps to the official Arize guidance for code-owned agent runtime, OpenInference
instrumentation, Phoenix traces, Phoenix MCP runtime introspection, trace evals, and
observability-driven improvement:
[official Arize track guidance](https://rapid-agent.devpost.com/details/arize-resources).

## Phoenix Value Proof: Pass Conditions

The Arize/Phoenix proof passes if:

1. `make evals-live` sends golden cases through live Google ADK/Gemini.
2. Phoenix receives traces for the run.
3. The trace contains ADK/Gemini spans and product-level market-fit spans.
4. A `fit_eval_run` span or equivalent eval span is visible.
5. The trace includes `schema_valid`, `false_strong_recommendation`,
   `weak_proxy_detected`, and `unsupported_implication` annotations or verified
   trace-linked eval fields.
6. The improve step uses Phoenix MCP trace context in live mode.
7. The improve response reports `inspection_source: phoenix_mcp` and
   `fallback_used: false`.
8. The second run downgrades the tempting market to `weak_proxy` and clears the
   false-strong eval.
9. The ledger records both the initial run and the trace-informed rerun.

## Demo Story

The seed demo starts with this thesis:

> Google TPU progress means Gemini closes the frontier-model gap in 2026.

A tempting prediction market appears relevant:

> Gemini becomes #1 on a public model leaderboard.

The first run overstates the fit by treating an adjacent market as stronger evidence
than it deserves. A trace-linked eval flags the false strong recommendation.
Phoenix/OpenInference traces show the failure context. The improve step uses Phoenix
MCP inspection and reruns the mission. The second run correctly classifies the market
as `weak_proxy`.

## Why It Matters

Prediction markets are useful only when the market cleanly expresses the thesis.
Many tempting markets are weak proxies: they look relevant but encode the wrong
horizon, platform, entity, metric, or causal mechanism.

Market Fit Trace Agent makes this failure inspectable and correctable. It does not
just recommend a market; it explains whether the fit is direct, indirect, weak, or
absent, records optional human review, and uses Phoenix traces to improve the next run.

## What It Does

1. Accepts a messy thesis or source text.
2. Uses Google ADK/Gemini to normalize the claim: entities, horizon, stance, and
   target outcome.
3. Retrieves a bounded set of relevant current Polymarket markets from recent
   market snapshots.
4. Classifies fit as `direct`, `indirect`, `weak_proxy`, or `no_clean_expression`.
5. Explains tempting rejected markets so adjacency is not mistaken for clean exposure.
6. Records optional human verdicts in a public-safe Ledger MCP lifecycle store.
7. Sends ADK/Gemini and product-level OpenInference spans to Phoenix.
8. Runs trace-linked deterministic evals for false strong recommendations and weak proxies.
9. Uses Phoenix MCP trace inspection to improve a second run.

## Architecture

```text
thesis / source text
  -> Google ADK / Gemini proposal
  -> schema validation
  -> bounded Polymarket market retrieval
  -> deterministic market-fit policy
  -> optional human verdict
  -> Ledger MCP lifecycle record
  -> Phoenix / OpenInference trace + eval annotation
  -> Phoenix MCP inspection
  -> improved second run
```

There is one deployable ADK agent. The FastAPI app is the audited workflow controller
around that agent: it validates schemas, applies deterministic market-fit policy,
writes ledger records, runs evals, and handles optional human verdicts.

Key files:

- `market_fit_adk/agent.py`: deployable Google ADK `root_agent` in the official ADK shape.
- `app/adk_runtime.py`: runner that calls the deployable ADK `root_agent` for JSON proposals.
- `app/agent.py`: compatibility wrapper around the workflow controller.
- `app/workflow.py`: product workflow and deterministic audit loop.
- `app/market_provider.py`: fixture and PolyData market providers.
- `app/tracing.py`: OpenInference/Phoenix tracing setup.
- `app/phoenix_mcp.py`: Phoenix MCP trace-inspection bridge.
- `app/evals.py`: deterministic fit and weak-proxy evals.
- `mcp/ledger_server.py`: project-local Ledger MCP lifecycle tools.
- `scripts/smoke_polydata.py`: optional live PolyData retrieval smoke check.
- `scripts/export_retrieval_candidate.py`: export live retrievals into candidate future goldens.
- `docs/golden-promotion.md`: live-retrieval to strict-golden promotion process.
- `evals/`: baseline goldens, promoted goldens, draft eval packs, and intake report.

The trust boundary is explicit: Gemini drafts, extracts, summarizes, and proposes.
Deterministic code classifies, scores, records, and gates the final market-fit
judgment.

## Responsibility Boundary

| Layer | Responsibility | Does not do |
|---|---|---|
| Google ADK / Gemini | Drafts normalized claim, entities, horizon, stance, and market-fit proposal | Final trust decision |
| Deterministic policy | Classifies fit, scores evals, enforces weak-proxy logic | Open-ended reasoning |
| Phoenix / OpenInference | Captures traces, spans, annotations, and failure context | Policy enforcement |
| Phoenix MCP | Retrieves failed trace/eval context for improvement | Guarantees correctness by itself |
| Ledger MCP | Records lifecycle events and optional human verdicts | Sponsor integration |

## Quickstart

Local reproducible demo, no live credentials required:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make test
make evals
make api
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

ADK local runner against the real `root_agent`:

```bash
make adk-run
```

ADK web UI for local agent inspection:

```bash
make adk-web
```

## Live Sponsor Path

Configure `.env` for Google ADK/Gemini and Phoenix:

Google auth mode A: AI Studio API key:

```bash
GOOGLE_ADK_ENABLED=true
GOOGLE_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-3.5-flash
```

Google auth mode B: Vertex AI / Cloud Run:

```bash
GOOGLE_ADK_ENABLED=true
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash
```

Phoenix:

```bash
PHOENIX_PROJECT_NAME=market_fit_trace_agent
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space-name/v1/traces
PHOENIX_BASE_URL=https://app.phoenix.arize.com/s/your-space-name
PHOENIX_API_KEY=your-phoenix-api-key
PHOENIX_MCP_ENABLED=true
```

Then run:

```bash
make smoke-adk-live
make evals-live
make phoenix-check
```

In submission/live mode, the improve step uses Phoenix MCP to inspect trace/eval
context. For local offline reproduction without Phoenix credentials, the app falls
back to the saved trace-linked eval record so reviewers can still exercise the same
product path.

For the exact Phoenix proof path, see [docs/phoenix-value-proof.md](docs/phoenix-value-proof.md).

## Example Output

```json
{
  "claim": "Google TPU progress means Gemini closes the frontier-model gap in 2026",
  "candidate_market": "Gemini becomes #1 on a public model leaderboard",
  "fit": "weak_proxy",
  "reason": "The market captures leaderboard rank, not the broader frontier-model gap thesis.",
  "evals": {
    "false_strong_recommendation": false,
    "weak_proxy_detected": true
  }
}
```

## 90-Second Demo Script

1. Open the hosted demo.
2. Use the default TPU/Gemini thesis.
3. Click **Run agent**.
4. Show the first-run market-fit judgment and trace-linked eval warning.
5. Open the Phoenix trace and show the eval span/annotations.
6. Click **Inspect trace and rerun**.
7. Show the second run downgrades the market to `weak_proxy`.
8. Show ledger events for initial run, trace inspection, and improved run.

## Evals

Core deterministic eval:

```bash
make evals
```

Promoted second golden suite:

```bash
make evals-v2
```

Live ADK/Gemini + Phoenix eval:

```bash
make evals-live
```

Golden pack coverage includes:

- direct fit;
- indirect fit;
- weak proxy detection;
- no clean expression;
- false strong recommendation prevention;
- horizon mismatch;
- platform mismatch;
- tempting wrong-market examples.

Advanced eval maintenance:

```bash
make evals-candidates
make evals-candidates-v3
make intake-goldens
make smoke-polydata
make export-retrieval-candidate
make phoenix-export-candidates
make phoenix-sync-goldens
make phoenix-experiment-goldens
```

`make intake-goldens` scans all eval packs for structural gaps, duplicate
source URLs/status IDs, near-duplicate source text, unsafe expected-output
assumptions, and market IDs referenced without frozen snapshots. It writes
`evals/golden_intake_report.md`.

For full eval-pack details, see [docs/evals.md](docs/evals.md).

Live data creates candidate evidence. Frozen snapshots create eval truth. Phoenix
connects the two by making failures inspectable and promotable. Optional PolyData
mode retrieves bounded current-market context; strict evals and the stable Phoenix
proof path replay frozen fixtures.

`make phoenix-export-candidates` mirrors live retrieval candidate packets into a
Phoenix Dataset review queue named `market_fit_candidate_cases`. Those rows are
pending evidence for human review, not strict eval truth. If Phoenix credentials
are unavailable, the command writes a local dry-run JSON report instead of
promoting candidates.

`make phoenix-sync-goldens` mirrors promoted frozen fixtures into
`market_fit_promoted_goldens_v1`. `make phoenix-experiment-goldens` compares
current deterministic policy output against those expected labels with code
evaluators. Repo fixtures remain canonical; Phoenix Datasets/Experiments are an
inspection and comparison surface, not a replacement source of truth.

## MCP

This project uses two MCP surfaces:

### Phoenix MCP

Arize partner integration. Used by the improve step to inspect failed trace/eval
context and rerun with the failure in context.

Phoenix MCP config example:

```text
mcp/phoenix_mcp_config.example.json
```

### Ledger MCP

Project-local lifecycle store. Records claim lifecycle events and optional human
verdicts when users provide them.

Run locally:

```bash
python mcp/ledger_server.py
```

## API

- `POST /api/runs`: run the agent.
- `POST /api/verdicts`: record `verify`, `reject`, `needs_review`, or `corrected`.
- `POST /api/runs/{run_id}/improve`: inspect failed trace/eval and rerun.
- `GET /api/ledger/{claim_id}`: return lifecycle events.
- `GET /api/markets`: return the current bounded market set or replay fixtures.

## Deployment

This repo includes two deployment paths:

- ADK agent API server on Cloud Run.
- FastAPI demo UI/API on Cloud Run.

See [docs/deploy-cloud-run.md](docs/deploy-cloud-run.md) for full commands.

## Known Limitations

- Dynamic retrieval is bounded by recent market snapshots and liquidity filters;
  formal evals replay frozen fixtures.
- PolyData live mode currently treats missing resolution rules as a conservative
  fit risk, so clean direct-fit claims should remain fixture-backed or human-verified.
- The app audits fit quality; it does not give trading advice or execute trades.
- Draft eval rows mined with external tools are not goldens until independently
  reviewed and promoted.
- Phoenix MCP is the live sponsor path; the local fallback is only for offline
  reproduction without Phoenix credentials.
- Next Arize extension: promoted live retrieval candidates can become Phoenix
  Datasets, and policy/prompt versions can be compared as Phoenix Experiments.
  The current submission keeps strict evals local and deterministic to preserve
  the trust boundary.

## Public Boundary

This repo is intentionally narrow. It includes the demo app, public-safe schemas,
a small Ledger MCP, seed examples, eval harnesses, Phoenix proof docs, and Cloud
Run deployment scaffolding. It does not include proprietary Epistemic Ledger
architecture, commercial scoring logic, private data, trading automation, or
investment advice.

## License

Apache-2.0. See [LICENSE](LICENSE).
