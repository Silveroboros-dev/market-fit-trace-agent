# Execution Plans

Use this file for complex features, significant refactors, or tasks expected to touch more than 3 files.

Do not create an execution plan for small bug fixes or simple edits.

## Template

### Goal

What outcome this plan must achieve.

### Current Repo Facts

Concrete facts from files, commands, tests, docs, or observed behavior.

### Files To Change

Expected files or directories and why they need to change.

### Test Strategy

Commands, smoke tests, evals, or manual checks that prove the change.

### Risks

Integration, scope, reliability, UX, security, or demo risks.

### Rollback/Fallback

The cheapest way to recover if the plan fails.

### Definition Of Done

Observable completion criteria.

## 2026-05-23 ADK / Phoenix Integration Upgrade

### Goal

Move the LLM proposal layer from direct Google GenAI SDK calls to Google ADK, and make the Arize/Phoenix integration visible enough for a judge to inspect ADK/Gemini spans, product spans, eval outputs, and trace-inspection behavior.

### Current Repo Facts

- `app/agent.py` currently defines `GeminiClient` with `google.genai.Client`.
- `app/tracing.py` already registers Phoenix tracing when Phoenix env vars are present and creates manual product spans.
- `app/phoenix_mcp.py` has a best-effort Phoenix MCP bridge with local fallback.
- `scripts/run_evals.py` and tests cover the weak-proxy first-run/improved-second-run behavior.
- Official Phoenix docs now provide a Google ADK integration through `openinference-instrumentation-google-adk`.

### Files To Change

- `pyproject.toml`: replace raw GenAI dependency with ADK and OpenInference ADK/MCP instrumentation.
- `app/config.py`: add ADK/Gemini env settings and keep Vertex settings for deployment.
- `app/tracing.py`: explicitly instrument Google ADK and MCP when installed.
- `app/adk_runtime.py`: new ADK-backed JSON proposal runtime with deterministic fallback.
- `app/agent.py`: consume ADK runtime instead of raw GenAI client.
- `scripts/smoke_arize_adk.py`: add a smoke command that proves ADK/Phoenix wiring locally.
- `README.md` and `.env.example`: document ADK/Phoenix setup and the remaining live Phoenix check.
- Tests: add focused tests for ADK fallback behavior without credentials.

### Test Strategy

- `uv run --python 3.11 --extra dev ruff check .`
- `uv run --python 3.11 --extra dev pytest`
- `uv run --python 3.11 python scripts/run_evals.py`
- `uv run --python 3.11 python scripts/smoke_arize_adk.py --offline`

### Risks

- Live Phoenix Cloud trace export cannot be proven without valid `PHOENIX_API_KEY` and endpoint.
- Live ADK model calls cannot be proven without valid Google credentials.
- Phoenix MCP tool names may drift; the bridge must list tools before calling specific trace tools.

### Rollback/Fallback

Keep deterministic local extraction/classification as the fallback. If ADK import or credentials fail, local tests and demo still run, but README and UI must clearly label this as fallback behavior.

### Definition Of Done

- The repo imports and runs with `google-adk` installed.
- ADK instrumentation is configured in the tracing setup.
- The agent model/runtime is labelled ADK-backed in run records.
- Tests, lint, evals, and offline smoke pass.
- README describes the live Phoenix credential check needed before submission.

## 2026-05-23 Market Fit V2 Candidate Promotion

### Goal

Turn the staged `market_fit_v2_candidates` pack into a disciplined promotion
queue: verify the first candidate market snapshots where possible, add
deterministic classifier coverage for the first promotion batch, and preserve the
passing `market_fit_v1` suite.

### Current Repo Facts

- `make evals` passes 10/10 on `market_fit_v1`.
- `make evals-candidates` runs `market_fit_v2_candidates` with
  `--allow-failures` and currently reports 7/16 passing.
- `evals/market_fit_v2_candidates/PROMOTION_NOTES.md` marks 10
  `promote_first` cases.
- `app/agent.py` uses ADK/Gemini for traceable proposals but deterministic
  application code makes final fit decisions.
- The v2 candidate market snapshots are currently based on user-provided Grok
  search output and are explicitly not formal goldens yet.

### Files To Change

- `evals/market_fit_v2_candidates/market_snapshots.jsonl`: add verification
  notes/status for promotion-first market pages.
- `evals/market_fit_v2_candidates/PROMOTION_NOTES.md`: update baseline and
  verification status after changes.
- `app/agent.py`: add narrow deterministic extraction/classification coverage
  for the promotion-first v2 cases.
- Possibly `scripts/run_evals.py`: only if the candidate runner needs better
  reporting for promotion status.

### Test Strategy

- `python3 -c` JSONL validation for v2 candidate files.
- `uv run --python 3.11 --extra dev ruff check app/agent.py scripts/run_evals.py`
- `make evals`
- `make evals-candidates`

### Risks

- Polymarket pages are dynamic and may not expose exact rules to static tools;
  mark verification status honestly instead of pretending.
- Overfitting deterministic rules can make the demo look brittle; keep rules
  narrow and tied to fixture-visible mechanism.
- Expanding candidate coverage must not break `market_fit_v1`.

### Rollback/Fallback

Keep v2 as a candidate pack with `--allow-failures`. If classifier coverage
becomes noisy, revert only the v2-specific rules and leave the pack as backlog.

### Definition Of Done

- Promotion-first cases have explicit verification status.
- Candidate pack has a higher passing baseline without weakening v1.
- v1 still passes 10/10.
- Any unverified market evidence is clearly labeled as candidate-only.
