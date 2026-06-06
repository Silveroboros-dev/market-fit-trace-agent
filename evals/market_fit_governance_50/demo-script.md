# Governance 50 Demo Script

This is the Governance 50 segment of the final hackathon demo. For the full
trace-repair -> governance -> experiment sequence, use:

```text
docs/final-demo-script.md
```

## Two-Minute Walkthrough

Open:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo1
```

Say:

```text
This is the Market Fit Governance 50 dataset. It is not pretending all 50 rows
are strict goldens. Each row has a truth_scope, so Phoenix can show strict
fixtures, reviewed candidates, draft candidates, and trace-repair cases in one
production-style review surface.
```

In the `Examples` tab, search:

```text
ai_startup_ipo_stage_mismatch
```

Say:

```text
This search reveals the hero failure cluster: AI-startup IPO stage mismatch.
The cluster collects OpenAI, Anthropic, and SpaceX examples where an agent can
confuse filing, preparation, valuation, and IPO completion.
```

Open the first row:

```text
gov_001_ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1
```

Point out:

```text
fit_class = indirect
truth_scope = failure_mode_golden
failure_modes = event_stage_mismatch, horizon_mismatch
actual_behavior = the live run recommended a December IPO-completion market
expected_behavior = IPO-completion markets are adjacent evidence, not direct
evidence of confidential filing or preparation
```

Say:

```text
This is the failure we want the system to remember. A high-quality source says
OpenAI is preparing a confidential IPO filing. A nearby market asks about IPO
completion or valuation. Those are related, but they are not the same contract.
```

Point to the nearby contrast rows:

```text
gov_003 SpaceX: direct when the market resolves on the same IPO-cap claim
gov_004 Anthropic: direct when the market resolves on the same valuation claim
gov_002 Anthropic: weak_proxy when valuation news is matched to a no-IPO timing market
```

Say:

```text
This is why it is a cluster, not a single anecdote. The repeated policy question
is whether entity, event stage, metric, and horizon are aligned. The system
accepts direct matches when they align and downgrades adjacent markets when they
do not.
```

Then open:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo2/compare?experimentId=RXhwZXJpbWVudDo3
```

Say:

```text
The experiment runs only on rows with usable expected labels. Strict metrics
exclude weak and draft rows. Governance metrics still count all 50 rows as
review coverage.
```

Close with:

```text
The point is not that live retrieval is always right. The point is that Phoenix
makes the failure visible, the row reviewable, the failure mode reusable, and the
policy change measurable.
```

## What Not To Claim

Do not say every row is a strict golden.

Do not say Phoenix decides market fit.

Do not say Gemini locks expected labels.

Do not say live PolyData retrieval mutates strict eval truth.

Do not present IPO filing/preparation and IPO completion as the same event.

## Fallback If Phoenix UI Is Slow

Use local artifacts:

```text
evals/market_fit_governance_50/governance_summary.json
evals/market_fit_governance_50/phoenix_dataset_result.json
evals/market_fit_governance_50/phoenix_experiment_result.json
```

The same counts and URLs are recorded there.

To print the cluster rows locally:

```bash
jq -r 'select(.hero_cluster=="ai_startup_ipo_stage_mismatch") | [.governance_id,.truth_scope,.fit_class,(.failure_modes|join(","))] | @tsv' evals/market_fit_governance_50/governance_examples.jsonl
```
