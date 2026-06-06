# Market Fit Governance 50

This folder contains the Phoenix-facing governance dataset for the hackathon
demo. It is intentionally not a strict golden pack.

The goal is to show that trace failures become reviewed eval memory:

```text
trace / candidate packet
-> failure-mode attribution
-> governed row with truth_scope
-> policy experiment on rows with usable expected labels
```

## Phoenix Artifacts

- Governance Dataset:
  `https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo1`
- Policy Experiment subset:
  `https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo2/compare?experimentId=RXhwZXJpbWVudDo3`

## Truth Scopes

Rows are intentionally mixed-scope:

| truth_scope | Meaning | Strict metric eligible |
|---|---|---:|
| `strict_golden` | Locked local fixture truth from promoted eval packs. | yes |
| `failure_mode_golden` | Usable expected behavior for one failure mode, but not full strict truth. | no |
| `reviewed_candidate` | Human-reviewed candidate evidence. | no |
| `draft_candidate` | Trace-backed or retrieval-backed row awaiting review. | no |
| `trace_repair_case` | Transition eval proving trace-informed repair. | no |

Not all governance rows are strict goldens. Strict accuracy is computed only on
`strict_golden` rows. Governance coverage includes all 50 rows.

## Hero Cluster

The demo cluster is `ai_startup_ipo_stage_mismatch`.

It contains 12 rows centered on OpenAI, Anthropic, and SpaceX. The key failure
class is confusing filing/preparation, valuation, and IPO-completion markets.

The hero row is:

```text
gov_001_ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1
```

Expected behavior:

```text
IPO-completion markets may be adjacent evidence for OpenAI filing/preparation,
but they are not a direct expression of confidential filing or preparation.
```

## Files

- `governance_examples.jsonl`: 50 flattened Phoenix governance rows.
- `governance_summary.json`: row counts, truth-scope counts, hero-cluster count.
- `phoenix_dataset_result.json`: latest Phoenix Dataset export result.
- `phoenix_experiment_result.json`: latest Phoenix Experiment result.
- `demo-script.md`: judge-facing two-minute walkthrough.

## Commands

Build the manifest:

```bash
make governance-50
```

Export the 50-row governance dataset to Phoenix:

```bash
make phoenix-export-governance
```

Run the policy experiment over rows with usable expected labels:

```bash
make phoenix-experiment-governance
```

## Latest Observed Result

- Governance rows: `50`
- Hero-cluster rows: `12`
- Experiment-eligible rows: `26`
- Strict metric rows: `19`
- Governance experiment subset fit-class accuracy: `1.0`
- Strict-only fit-class accuracy: `1.0`
- False-strong recommendation rate: `0.0`
- Stage-mismatch direct false positives: `0`

## Boundary

Phoenix is the judging surface for trace review, annotations, datasets, and
experiments. Repo fixtures remain canonical strict truth. Gemini may propose
labels and explanations; deterministic code scores the policy; human review
locks truth scope and expected behavior.
