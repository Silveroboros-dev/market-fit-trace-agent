# Final Demo Script

This is the recommended 3-minute hackathon video script. The goal is to show one
loop:

```text
trace -> failure signal -> Phoenix MCP inspection -> deterministic repair -> governed eval memory
```

Target timing:

```text
0:00-0:20 opening claim
0:20-1:05 trace repair proof
1:05-2:35 Governance 50 + Experiment proof
2:35-3:00 close
```

## 0. Opening Frame

Say:

```text
Prediction markets are unit tests for beliefs: they force claims about the world
into resolvable form. Epistemic Ledger asks whether a claim has a good test, and
Market Fit Trace Agent catches the dangerous failure: using the wrong test
because it looks related.

Phoenix made that failure observable. Failed traces expose policy blind spots we
had not encoded yet, Phoenix MCP turns them into repair context, and
deterministic policy corrects the next run. The north star is keeping
prediction-market false positives close to zero.
```

## 1. Trace Repair Proof

Start from the default fixture-backed demo path:

```bash
make api
```

Use the default TPU/Gemini thesis:

```text
Google TPU progress means Gemini closes the frontier-model gap in 2026.
```

Say:

```text
The tempting market is a Gemini leaderboard market. It is related, but it is not
a clean expression of the TPU infrastructure thesis. The first run is expected
to overstate the fit.
```

Show:

```text
first run: false strong recommendation
Phoenix trace/eval context: weak proxy and causal-mechanism mismatch are visible
Phoenix MCP inspection: failed trace context is retrieved
second run: deterministic repair gate downgrades to weak_proxy
fallback_used = false
```

Say:

```text
This is the runtime loop: a trace exposes the failure, Phoenix MCP retrieves the
context, and deterministic policy repairs the next run.
```

## 2. Governance 50 + Experiment Proof

Open the Governance Dataset:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo1
```

Say:

```text
The same loop is now scaled into Governance 50: a Phoenix-visible eval-memory
surface with strict goldens, failure-mode goldens, reviewed candidates, draft
candidates, and a trace-repair case.
```

In the `Examples` tab, search:

```text
ai_startup_ipo_stage_mismatch
```

Say:

```text
This is the hero failure cluster: OpenAI, Anthropic, and SpaceX IPO cases where
an agent can confuse filing, preparation, valuation, and IPO completion.
```

Open the OpenAI hero row:

```text
gov_001_ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1
```

Point out:

```text
fit_class = indirect
truth_scope = failure_mode_golden
failure_modes = event_stage_mismatch, horizon_mismatch
expected_behavior = IPO-completion markets are adjacent evidence, not direct
evidence of confidential filing or preparation
```

Say:

```text
The source says OpenAI is preparing a confidential IPO filing. The tempting
market asks about IPO completion or valuation. Related is not the same as
resolved by the same contract.
```

Open the Phoenix Experiment:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo2/compare?experimentId=RXhwZXJpbWVudDo3
```

Say:

```text
This experiment is the scored view of Governance 50. It runs only rows with
usable expected labels, so review-only data stays visible without polluting
strict accuracy.
```

Point out:

```text
main governance rows = 50
experiment rows = 26
strict metric rows = 19
false strong recommendation rate = 0
stage-mismatch direct false positives = 0
```

Say:

```text
This unites the review surface and the policy surface: 50 governed rows, 26
scored rows, 19 strict rows, and zero direct false positives on the stage-mismatch
case.
```

## 3. Close

Say:

```text
The product claim is simple: trace failures become reviewed eval memory, and eval
memory becomes deterministic policy pressure. That is how this agent keeps
prediction-market false positives close to zero.
```

## What To Use In The Final Demo

Use these three surfaces only:

```text
1. Product/API trace-repair run for the single failure-to-repair loop.
2. Phoenix Dataset market_fit_governance_50 for governed eval memory.
3. Phoenix Experiment for deterministic policy comparison on eligible rows.
```

Do not show `make api-live` in the 3-minute video. Refer to live PolyData as the
candidate-evidence path only if asked.

## What Not To Claim

Do not say all 50 rows are strict goldens.

Do not say Phoenix decides market fit.

Do not say Gemini locks expected labels.

Do not say live PolyData retrieval mutates strict eval truth.

Do not say Phoenix automatically discovered the IPO cluster through embeddings in
this version. The current demo exposes a repo-governed cluster through Phoenix
Dataset search and Experiment comparison.

Do not say the current evals prove Gemini extraction quality. They prove
deterministic market-fit policy behavior and trace-backed repair; Gemini proposal
quality is trace-visible and a separate future eval target.
