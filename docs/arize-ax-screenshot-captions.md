# Arize AX Screenshot Captions

These captions are for optional Arize AX evidence. Phoenix MCP remains the canonical trace-repair proof path; AX shows that the same ADK/product trace shape can be exported to Arize AX when configured.

## Live AX Run

- AX project: `market_fit_trace_agent`
- Run ID: `run_cc0185ec3368`
- Trace ID: `2591c4e3bd6363b8cc0456ec98eafce4`
- Created at: `2026-05-31T18:14:47Z`
- Market provider: `polydata`
- Snapshot: `polydata_polymarket_2026-05-31 03:00:00+00:00`
- Universe count: `508`
- Returned markets: `6`
- Deterministic policy span: `deterministic_market_fit_policy`

## Caption: Trace Tree

Arize AX receives the opt-in ADK/product trace for Market Fit Trace Agent. The trace tree shows the product-level run span, Gemini/ADK model-call spans, market retrieval, deterministic market-fit classification, and eval logging in one observable flow.

## Caption: Live Market Retrieval

This run used live PolyData retrieval, not frozen fixtures. The `market_retrieval_run` span records `market_data_mode=polydata`, `returned_count=6`, and the PolyData snapshot ID, proving that the candidate markets were retrieved from the live provider path before policy evaluation.

## Caption: Gemini / ADK Spans

The Gemini calls appear as ADK/OpenInference spans under `invocation [market_fit_trace_agent]`, `agent_run [market_fit_trace_agent]`, and `call_llm`. These spans show where Gemini extracts or proposes, while deterministic code remains responsible for final policy decisions.

## Caption: Deterministic Policy Boundary

The `execute_tool market_fit_policy` span is not a Gemini call. It is the deterministic policy tool that converts candidate market evidence into one of the governed fit classes: `direct`, `indirect`, `weak_proxy`, or `no_clean_expression`.

## Caption: Decision / Eval

The downstream classification for this live AX run is `weak_proxy`. AX is useful here as an enterprise observability mirror, while Phoenix MCP remains the demo-critical mechanism for trace inspection and deterministic repair.

## Short Devpost Caption

Optional Arize AX export shows the same ADK/product trace shape used by the Phoenix demo. In this live run, `market_retrieval_run` used `market_data_mode=polydata`, returned six bounded markets, and the deterministic policy classified the best retrieved market as `weak_proxy`.
