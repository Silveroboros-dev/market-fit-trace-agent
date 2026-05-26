# Golden Promotion Process

Live market retrieval and strict evals are separate loops.

```text
Live data creates candidate evidence.
Frozen snapshots create eval truth.
```

## Market Data Modes

- `fixture`: deterministic replay, strict evals, and the stable Phoenix proof path.
- `polydata`: bounded current-market product mode.

The product may retrieve current markets. Strict evals must not call live market
APIs.

## Promotion Flow

```text
live run / Phoenix trace / human review
  -> candidate eval row
  -> frozen market snapshot
  -> frozen rules snapshot or explicit rules_status=missing
  -> expected fit label
  -> intake gate
  -> promoted golden pack
```

A live run may become a candidate golden only when:

1. The source thesis is public-safe and has provenance.
2. The retrieval result includes `mode`, `snapshot_id`, `as_of_ts`,
   `retrieval_id`, filters, and candidate market IDs.
3. Candidate markets are frozen into `market_snapshots.jsonl`.
4. Available resolution rules are frozen into `market_rules_snapshots.jsonl`.
5. If rules are unavailable, `rules_status = "missing"` is recorded and treated
   as a fit-risk signal.
6. A human reviewer assigns the expected fit behavior.
7. The row passes `make intake-goldens`.
8. The row is promoted into a versioned eval pack.

## Candidate Export Command

Use the export command to freeze live retrieval context for later review:

```bash
make export-retrieval-candidate
```

The command writes:

```text
evals/retrieval_candidates/YYYY-MM-DD/<case_id>/
  source.json
  retrieval_result.json
  market_snapshots.jsonl
  market_rules_snapshots.jsonl
  review_notes.md
```

The exported directory is not a golden. It is a candidate review packet.

For trace-backed review packets, run the exporter with the agent pass enabled:

```bash
uv run --python 3.11 python scripts/export_retrieval_candidate.py --run-agent
```

That adds:

```text
run_result.json
ledger_store.json
```

`run_result.json` includes the normalized claim, proposed fit class, recommended
market, eval metrics, run ID, and Phoenix trace ID/URL when Phoenix is configured.

## Phoenix Candidate Review Dataset

Candidate packets can be mirrored into a Phoenix Dataset review queue:

```bash
make phoenix-export-candidates
```

The dataset is named `market_fit_candidate_cases` by default. It is a review
queue, not eval truth. Rows include:

- source text and case ID;
- retrieval ID, snapshot ID, `as_of_ts`, and candidate market IDs;
- rules-status summary;
- proposed fit class and recommended market when `run_result.json` exists;
- Phoenix trace ID/URL when the candidate was exported with `--run-agent`;
- `human_review_status = pending`;
- `reviewer_note = ""`;
- recommended action such as `needs_more_rules` or
  `review_for_weak_proxy_golden`.

This gives reviewers one Phoenix surface for deciding whether a live retrieval
is a useful future golden. Human review still decides promotion.

If Phoenix credentials are unavailable, the command writes the same candidate
row shape to a local JSON dry-run report and marks the missing configuration.
Dry-run rows are still candidate evidence only and do not include strict
expected labels.

Observed MVP result:

- Dataset: `market_fit_candidate_cases`
- Dataset URL:
  `https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDoz`
- Local result artifact:
  `evals/retrieval_candidates/phoenix_candidate_review_dataset_result.json`
- Candidate count: `1`
- Run-backed count: `1`
- Pending review count: `1`
- Current recommended action: `needs_more_rules`

The observed candidate is intentionally not promoted. It demonstrates the review
queue: live retrieval found relevant markets, the agent proposed an `indirect`
fit, Phoenix recorded the trace, and the Dataset row tells the reviewer that
missing rules must be resolved before promotion.

Pass/fail threshold for promotion:

- source provenance is public-safe;
- retrieval provenance is present;
- market snapshots are frozen;
- rules are frozen or explicitly marked `rules_status = "missing"`;
- expected fit behavior is human-reviewed;
- `make intake-goldens` passes after the row is moved into a candidate pack.

## Cadence

Use monthly review for normal market evolution, plus event-driven review when:

- a Phoenix trace reveals a new failure mode;
- a market category changes materially;
- a new domain is added;
- a reviewer finds a high-value weak proxy;
- current market evolution makes old examples less representative.

## Non-Goals

Do not automatically promote live runs into strict goldens.

Do not make the stable Phoenix proof depend on current Polymarket data.

Do not treat retrieval success as market-fit correctness. PolyData retrieves
market context; Market Fit Trace Agent classifies fit.
