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
1:05-2:35 Governance 50 + Experiment evidence
2:35-3:00 stress-to-policy-review close
```

## Framing

The core improvement proof is the live trace-repair loop in Section 1: Phoenix MCP
exposes a false-strong recommendation and deterministic policy repairs it.
Governance 50 in Section 2 is supporting governance and review-memory evidence:
it shows the same truth-boundary discipline holding on curated rows.

Stress-40 is appendix evidence that the same Phoenix-traced harness holds the
boundary across many adversarial cases. It is not the core improvement proof, and
its Gemini advisory numbers are shown as variance, not as a win. See
`evals/stress_test_v1/STRESS_40_APPENDIX.md`.

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

## 2. Governance 50 + Experiment Evidence

Open the Governance Dataset:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo1
```

Say:

```text
Governance 50 is the review-memory surface behind that boundary: a
Phoenix-visible dataset with strict goldens, failure-mode goldens, reviewed
candidates, draft candidates, and a trace-repair case.
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

We do not let the agent silently rewrite truth. It turns failures into
reviewable artifacts, proposes a patch, reruns stress, and shows whether the
patch helped.
```

Show the generated policy-review batch if there is enough screen time:

```text
evals/policy_review_batches/2026-06-08/POLICY_REVIEW.md
evals/policy_review_batches/2026-06-08/POLICY_CHANGE_PROPOSAL.md
```

Say:

```text
The core improvement proof is the trace-repair loop you just saw: Phoenix MCP
exposed a false-strong and deterministic policy repaired it. Stress-40 is appendix
evidence that the same harness holds that boundary at scale.

Across four committed post-patch runs, with no new model calls in this demo, the
deterministic class is identical on all 40 cases in every run, and deterministic
direct false positives stay at zero. Gemini advisory mismatches swing run to run
(17, 17, 16, 21 of 40) because the model is only the proposer. Eleven cases per
run are deterministic strong-over-weak/no review candidates, not false positives,
and none are promoted automatically. A reviewer decides whether each cluster needs
more rules, stays candidate-only, becomes a strict golden candidate, or is
disregarded. See evals/stress_test_v1/STRESS_40_APPENDIX.md.
```

## What To Use In The Final Demo

Use these three main surfaces:

```text
1. Product/API trace-repair run for the single failure-to-repair loop.
2. Phoenix Dataset market_fit_governance_50 for governed eval memory.
3. Phoenix Experiment for deterministic policy comparison on eligible rows.
```

Use this local artifact only as the closing proof of the failure-to-policy-review
loop:

```text
4. evals/policy_review_batches/2026-06-08/POLICY_REVIEW.md
5. evals/policy_review_batches/2026-06-08/POLICY_CHANGE_PROPOSAL.md
6. evals/stress_test_v1/STRESS_40_APPENDIX.md (deterministic stability + advisory variance)
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

Do not say the policy-review batch mutates policy code or promotes strict
goldens. It is a candidate-only human review artifact.

Do not say the current evals prove Gemini extraction quality. They prove
deterministic market-fit policy behavior and trace-backed repair; Gemini proposal
quality is trace-visible and a separate future eval target.
