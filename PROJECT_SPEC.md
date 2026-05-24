# Project Spec

## Decision

Build **Market Fit Trace Agent** for the Rapid Agent Hackathon Arize track.

Do not submit a fork of Epistemic Ledger. Submit a new, narrow, public, open-source project created during the contest period.

## Problem

Prediction-market users see messy theses in posts, articles, and notes. The hard question is not only "is there a related market?" The harder question is:

> Does this market actually express the claim, or is it a tempting weak proxy?

Agents can overstate weak fits. That destroys trust. The project makes this failure visible, correctable, and improvable.

## Target User

Primary user:

- analyst, founder, investor, operator, or prediction-market power user;
- sees public signals and wants to map them to event-risk markets without fake precision.

Hackathon framing:

> Beyond chatbot: an agent that does market-fit judgment under human and observability control.

## Demo Scenario

User pastes a thesis:

> Google TPU claims mean Gemini will close the gap with frontier models this year. Find the best prediction-market expression and tell me whether the market is a clean fit.

First run:

- agent extracts the thesis;
- agent finds a tempting model-ranking market;
- agent overstates it as a strong fit or nearly direct fit;
- Phoenix eval flags it as false strong recommendation / weak proxy;
- human rejects or downgrades the fit.

Second run:

- agent queries Phoenix MCP for the failed trace/eval;
- agent revises its instruction or output;
- agent classifies the market as weak proxy or no-clean expression;
- ledger records the correction and improved result.

## Core Workflow

1. Paste thesis/source.
2. Extract normalized claim, entities, horizon, stance.
3. Retrieve or load candidate markets.
4. Classify market fit:
   - `direct`
   - `indirect`
   - `weak_proxy`
   - `no_clean_expression`
5. Explain what the market captures and misses.
6. Ask for human verdict:
   - verify
   - reject
   - needs review
   - corrected claim/fit
7. Write lifecycle event through Ledger MCP.
8. Emit trace spans to Phoenix.
9. Run evals on trace/output.
10. Inspect failed trace through Phoenix MCP and rerun.

## Visible Trace Spans

- `user_goal_received`
- `source_ingested`
- `claim_extracted`
- `candidate_markets_loaded`
- `market_fit_classified`
- `rejected_markets_explained`
- `ledger_claim_proposed`
- `grounding_eval_run`
- `fit_eval_run`
- `human_verdict_recorded`
- `phoenix_trace_inspected`
- `claim_revised`

## Evals

Minimum demo evals:

- schema validity;
- fit class accuracy;
- false strong recommendation;
- weak proxy detection;
- no-clean precision;
- unsupported implication;
- explanation overclaiming;
- missing human verification.

The demo only needs one obvious failure and one obvious improvement, but the code should support a small seed set.

## MVP UI

One screen is enough:

- left: thesis/source input and run button;
- center: extracted claim, candidate market, fit class, rejected markets, human verdict buttons;
- right: eval summary, Phoenix trace link, before/after comparison.

## Out Of Scope

- full Epistemic Ledger product;
- full market graph;
- karma/trust economics;
- production auth;
- payment or trading;
- account-aware exposure;
- 50+ evals;
- complex multi-agent hierarchy;
- beautiful dashboard beyond a clear demo workflow.

## Acceptance Criteria

Competitive submission requires:

- hosted app works;
- public repo installs from README;
- Gemini agent performs a multi-step task;
- Phoenix MCP integration is meaningful;
- Phoenix trace is visible;
- at least one eval catches a real market-fit failure;
- human verdict changes claim/fit status;
- Ledger MCP records claim lifecycle;
- second run improves after trace inspection;
- demo explains all of this in under 3 minutes.
