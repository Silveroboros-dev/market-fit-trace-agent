# Arize / Phoenix Plan

## Track Decision

Use the Arize track.

Reason:

The project is fundamentally about making agentic judgment inspectable, evaluable, and improvable. Arize/Phoenix is a natural fit because the demo depends on traces, evals, and runtime introspection.

## Required Visible Use

The submission should visibly include:

- code-owned Gemini agent runtime;
- OpenInference tracing;
- Phoenix Cloud or self-hosted Phoenix;
- Phoenix MCP configured as a tool/server;
- evals on traces;
- second-run improvement using observability data.

## Trace Spans

Required spans:

- `user_goal_received`
- `source_ingested`
- `claim_extracted`
- `candidate_markets_loaded`
- `market_fit_classified`
- `rejected_markets_explained`
- `ledger_claim_proposed`
- `fit_eval_run`
- `human_verdict_recorded`
- `phoenix_trace_inspected`
- `claim_revised`

Span attributes should include:

- `run_id`
- `claim_id`
- `model`
- `prompt_version`
- `retrieval_version`
- `semantic_fit_class`
- `recommended_market_id`
- `false_strong_recommendation`
- `human_verdict`

## Evals

Minimum eval metrics:

- `schema_pass_rate`
- `fit_class_accuracy`
- `false_strong_recommendation_rate`
- `weak_proxy_precision`
- `no_clean_precision`
- `unsupported_implication_count`
- `human_verification_present`
- `second_run_improvement`

The strongest demo metric:

> false strong recommendation goes from 1 to 0 after Phoenix trace inspection.

## Phoenix MCP Use

The agent should use Phoenix MCP to:

1. retrieve failed trace/eval data;
2. summarize where the prior run overclaimed;
3. revise instructions or output;
4. rerun and compare results.

The demo should show this as a product behavior, not just background telemetry.

## Demo Failure Pattern

Use a weak-proxy case:

- thesis is about an underlying event or causal claim;
- candidate market is only adjacent;
- first run classifies it too strongly;
- eval flags false strong recommendation;
- human rejects/downgrades;
- second run marks it as weak proxy or no clean expression.

This is more aligned with Epistemic Ledger than a generic hallucination example.
