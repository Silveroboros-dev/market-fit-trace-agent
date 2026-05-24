# Three-Minute Demo Script

Target length: 2:45 to 3:00.

## 0:00-0:20 Problem

Agents can find related prediction markets, but related is not the same as correct. In event-risk workflows, the dangerous failure is a tempting weak proxy presented as a clean market expression.

## 0:20-0:45 System

This is Market Fit Trace Agent. Gemini extracts the thesis, classifies candidate market fit, records the claim lifecycle through a Ledger MCP, and Arize Phoenix traces and evaluates every step.

## 0:45-1:30 First Run

Show:

- pasted source/thesis;
- normalized claim;
- candidate market;
- fit explanation;
- one overconfident or weak recommendation;
- Phoenix eval flagging false strong recommendation or weak proxy failure.

## 1:30-2:00 Human Review

Show:

- human rejects or downgrades the fit;
- corrected fit class becomes `weak_proxy` or `no_clean_expression`;
- Ledger MCP records the verdict;
- UI updates the lifecycle.

## 2:00-2:40 Self-Improvement

Show:

- agent queries Phoenix MCP for the failed trace/eval;
- agent summarizes why the first run failed;
- second run revises or removes the overclaim;
- eval summary improves.

## 2:40-3:00 Why It Matters

Close:

> Market Fit Trace Agent turns agents from answer generators into auditable collaborators for high-stakes market judgment. The user does not just see an answer. They see the claim, the market fit, the rejected weak proxies, the human verdict, the trace, and whether the next run improved.

## Demo Must Show

- hosted app;
- Gemini agent behavior;
- Ledger MCP write;
- Phoenix trace link;
- eval result;
- human correction;
- before/after improvement.
