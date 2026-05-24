# Market Fit Eval v1

This eval package tests the Market Fit Trace Agent baseline loop:

> messy source signal -> normalized market thesis -> frozen market context -> fit class -> rejected-market explanation -> trace-linked eval

The seed set target is **10 examples**. Do not fabricate seed examples here; populate the JSONL files from the public posts, excerpts, and theses selected for annotation.

Current seed progress: **10 / 10 examples populated**.

Trace replay status: **10 / 10 examples passed in live ADK mode with Phoenix trace URLs**.
See `v1_trace_audit.md`.

## Source Of Truth

Versioned JSONL files in this directory are the source of truth. Spreadsheet or Notion annotation can be used temporarily, but labels must be exported here before they count.

## Files

| File | Purpose |
| --- | --- |
| `examples.jsonl` | User input, provenance, source-signal metadata, context, and snapshot refs. |
| `expected_outputs.jsonl` | Gold thesis, fit labels, market IDs, explanation constraints, and draft-contract requirements. |
| `market_snapshots.jsonl` | Frozen market facts used by retrieval and scoring. |
| `market_rules_snapshots.jsonl` | Frozen descriptions, resolution rules, sources, and ambiguity flags. |
| `candidate_sets.jsonl` | Top retrieved candidates, tempting wrong markets, and no-market evidence per example. |
| `label_guide.md` | Human labeling rules. |
| `scoring_rubric.md` | Automated and human scoring rules. |
| `rejected_markets_notes.md` | Notes on tempting but wrong markets. |
| `adjudication_log.md` | Hard-case disagreements and final decisions. |
| `v1_trace_audit.md` | Replay audit showing the original 10 goldens pass through live ADK/Gemini and Phoenix traces. |
| `schemas/` | JSON schemas for the core artifacts. |

## Quick Start

Run the deterministic baseline eval:

```bash
make evals
```

Run the same baseline through live ADK/Gemini and Phoenix tracing:

```bash
make evals-live
```

Verify the latest Phoenix trace has the expected eval span and annotations:

```bash
make phoenix-check
```

## Annotation Order

1. Freeze or manually record the relevant market and market-rules snapshot.
2. Add one line to `examples.jsonl`.
3. Add the retrieved or manually reviewed candidate set to `candidate_sets.jsonl`.
4. Add the gold label to `expected_outputs.jsonl`.
5. Record why tempting markets are wrong in `rejected_markets_notes.md`.
6. Run `make evals`; for trace replay evidence, also run `make evals-live` and `make phoenix-check`.

## Seed Set Target

The first 10 examples should include:

| Case | Count |
| --- | ---: |
| Direct expression | 2 |
| Indirect expression | 2 |
| Weak proxy | 2 |
| No clean expression | 2 |
| Ambiguous / overbroad / resolution-risk | 2 |

At least six of the ten should include plausible wrong markets. At least two should require the system to say no clean expression exists.

Current provisional mix:

| Example | Source | Fit |
| --- | --- | --- |
| `eval_001` | Patrick Collison / Link CLI | `no_clean_expression` |
| `eval_002` | Kashyap Sriram / USD swap lines | `no_clean_expression` |
| `eval_003` | Ethan Mollick / AI research agents | `no_clean_expression` |
| `eval_004` | Pedro Domingos / multi-agent coordination | `no_clean_expression` |
| `eval_005` | Pankaj Kumar / Gemini 3.2/3.5 leaks | `indirect` |
| `eval_006` | Neo / SpaceX IPO timeline | `direct` |
| `eval_007` | AIM Investments / Anthropic valuation | `direct` |
| `eval_008` | SerPAI / Google TPU claims | `weak_proxy` |
| `eval_009` | User note / Anthropic IPO momentum | `weak_proxy` |
| `eval_010` | Techno Optimist / Putnam AI result | `indirect` |

## Locking Rule

After `market_fit_v1` is locked, do not silently edit labels. If labels need correction, create a new version such as `market_fit_v1_1` or record the adjudication explicitly.
