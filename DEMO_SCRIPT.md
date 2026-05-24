# Three-Minute Demo Script

Target length: 2:45 to 3:00.

## 0:00-0:20 Problem

A related prediction market is not always a correct expression of a thesis. The
dangerous failure is a tempting weak proxy presented as a clean market fit.

## 0:20-0:40 Product

Market Fit Trace Agent audits thesis-to-market fit and catches weak proxies before
users trust them.

## 0:40-1:15 First Run

Show:

- pasted source/thesis;
- Gemini extraction into a normalized claim;
- candidate market;
- over-strong fit;
- trace-linked eval flagging false strong recommendation / weak-proxy risk.

## 1:15-1:45 Phoenix Proof

Show:

- Phoenix trace link from the run;
- `fit_eval_run` span;
- eval annotations such as `false_strong_recommendation` and `weak_proxy_detected`;
- trace ID matching the run.

## 1:45-2:15 Phoenix MCP Improve Step

Show:

- click **Inspect trace and rerun**;
- improve response or UI evidence with `inspection_source: phoenix_mcp`;
- improve response or UI evidence with `fallback_used: false`;
- agent reruns with failed trace/eval context.

## 2:15-2:40 Second Run

Show:

- classification downgrades to `weak_proxy`;
- false-strong eval clears;
- ledger records trace inspection and updated run.

## 2:40-3:00 Close

Close:

> Market Fit Trace Agent is a trace-backed market-fit audit, not trading advice
> and not generic claim checking. Gemini proposes, deterministic code verifies,
> Phoenix exposes the failure, Phoenix MCP feeds the correction, and the ledger
> records the lifecycle.

## Demo Must Show

- hosted app;
- Gemini agent behavior;
- Phoenix trace before the final minute;
- `fit_eval_run` span or eval annotations;
- `inspection_source: phoenix_mcp`;
- `fallback_used: false`;
- before/after improvement;
- Ledger MCP lifecycle event;
- no wallet, trading automation, or investment advice.
