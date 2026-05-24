# Market Fit V3 Candidate Pack

This folder stages the novel examples from the second Grok mining pass supplied
on May 23, 2026.

Status: candidate pack, not default goldens.

## Intake Decision

- 14 novel source examples retained.
- 15 repeated or lower-value examples dropped because they duplicate v2 sources
  or test the same market-fit failure mode with less clarity.
- This pack intentionally emphasizes hard negative and proxy cases. The mining
  pass did not produce enough clean new direct markets to justify forcing a
  balanced distribution.

## Contents

- `examples.jsonl`: retained source posts and provenance.
- `expected_outputs.jsonl`: expected normalized thesis and fit class.
- `market_snapshots.jsonl`: reused public candidate market snapshots needed by
  retained examples.
- `dropped_cases.md`: duplicates and rejected rows from the supplied batch.
- `PROMOTION_NOTES.md`: promotion gate and next review tasks.

Run separately with:

```bash
make evals-candidates-v3
```

This target is intentionally non-CI while the pack is staged.
