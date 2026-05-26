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
