# Evals

Market Fit Trace Agent uses deterministic evals to prove its core trust claim:
the agent must not turn a tempting adjacent prediction market into a clean
recommendation when the market does not actually express the thesis.

## Product Vs Eval Boundary

In production or live demo mode, the app should retrieve a bounded set of
relevant current Polymarket markets from recent market snapshots. It should not
scan the whole market universe for every user request. The retrieval layer can
use practical indexes such as taxonomy/category buckets, embeddings, similarity
edges, and liquidity filters.

Strict evals do not call live market APIs. They replay the same kind of market
data from frozen fixtures so regressions are meaningful.

The markets themselves are not being evaluated; they are the source context. What
we evaluate is:

- whether the retrieval layer fetched the right relevant markets;
- whether it included tempting-but-wrong markets when useful;
- whether the fit layer correctly labels the result as `direct`, `indirect`,
  `weak_proxy`, or `no_clean_expression`;
- whether the output avoids false strong recommendations and trading advice.

For the first dynamic retrieval version, use a simple market-universe rule:
include open markets whose liquidity/open-interest/volume proxy exceeds
USD 10,000, then narrow by taxonomy/category or semantic index before the agent
reasons about fit.

The implementation-facing retrieval contract is in
[poly-data-provider-contract.md](poly-data-provider-contract.md).

The live-retrieval to strict-golden promotion process is in
[golden-promotion.md](golden-promotion.md).

## Commands

Strict local baseline:

```bash
make evals
```

Strict promoted v2 suite:

```bash
make evals-v2
```

Strict live-promoted suite:

```bash
make evals-v4-live-promoted
```

Live ADK/Gemini + Phoenix replay:

```bash
make evals-live
make phoenix-check
```

Phoenix-MCP-gated trace repair proof:

```bash
make trace-repair
```

Draft eval-pack reports:

```bash
make evals-candidates
make evals-candidates-v3
```

Golden promotion intake gate:

```bash
make intake-goldens
```

Live retrieval candidate export:

```bash
make export-retrieval-candidate
```

## Eval Packs

| Pack | Role | Strict? |
| --- | --- | --- |
| `evals/market_fit_v1` | Original 10-case baseline covering direct, indirect, weak proxy, and no-clean-expression cases. | Yes |
| `evals/market_fit_v2` | Promoted second suite focused on weak proxies, no-clean-expression, horizon mismatch, and platform mismatch. | Yes |
| `evals/market_fit_v4_live_promoted` | Reviewed live PolyData retrieval candidates with frozen agent-run market sets and backfilled resolution rules. | Yes |
| `evals/trace_repair_v1` | Transition evals where the first run must fail, Phoenix MCP must retrieve trace/eval context, and the second run must repair through the deterministic trace cap. | No; separate repair proof |
| `evals/market_fit_v2_candidates` | Draft eval pack for coverage review and promotion work. | No |
| `evals/market_fit_v3_candidates` | Draft eval pack after deduplication. | No |

Draft eval packs run with `--allow-failures`. They are not formal goldens until
source provenance, frozen market snapshots, frozen rules, and expected labels are
reviewed.

These evals score deterministic market-fit policy behavior. Gemini extraction and
interpretation quality is captured in traces but is not the pass/fail authority
for the current strict suites; it should be evaluated separately when the next
stage focuses on model proposal quality.

## Frozen Fixtures

Formal eval rows need four things:

- source text and provenance;
- expected normalized thesis;
- frozen market snapshots and resolution rules;
- expected fit behavior, including tempting wrong markets.

`market_snapshots.jsonl` stores the market context visible at the snapshot time.
`market_rules_snapshots.jsonl` stores the resolution rules. `expected_outputs.jsonl`
stores the gold behavior.

Human judgment is required when promoting a draft row into a golden. Human
judgment is not required before every production recommendation.

## Eval Taxonomy

Strict correctness goldens assert the final answer for a frozen fixture. They
should pass on first deterministic replay.

Trace-repair cases assert a before/after transition. The first run is expected
to overstate fit in a specific, annotated way. Phoenix MCP inspection must
retrieve the failed trace/eval context, and only then may the deterministic
`trace_informed_false_strong_cap` downgrade the rerun to `weak_proxy`.

Live retrieval candidates are non-canonical evidence packets. They may become
strict goldens only after human review, frozen market snapshots, frozen rules,
and expected labels are written.

Source-assisted candidate rows in `evals/market_fit_v2_candidates` and
`evals/market_fit_v3_candidates` provide a lighter evidence anchor for UI
testing and review. Their source text and provenance can seed a fresh run, but
their proposed fit labels are not canonical truth and cannot mutate promoted
`expected_outputs.jsonl` files through the UI.

## Baseline Trace Replay

The original 10 v1 goldens were created before Phoenix MCP was integrated. They
were replayed through live ADK/Gemini and Phoenix on 2026-05-24:

```text
status: passed
mode: live
eval_pack: market_fit_v1
case_count: 10
passed_count: 10
```

The replay emitted Phoenix trace URLs for every case. The captured audit is in:

```text
evals/market_fit_v1/v1_trace_audit.md
```

## Golden Intake Gate

`make intake-goldens` writes:

```text
evals/golden_intake_report.md
```

It checks:

- required fixture fields;
- expected-output fit classes;
- safety expectations;
- market IDs referenced without frozen market snapshots;
- duplicate example IDs;
- duplicate source URLs and X status IDs;
- duplicate and near-duplicate source text;
- externally sourced rows that still require independent review.

Structural errors block promotion. Warnings are review signals: they are expected
for draft eval packs.

## Demo-Supported Claims

The evals support these README/Devpost claims:

- The agent distinguishes `direct`, `indirect`, `weak_proxy`, and
  `no_clean_expression`.
- The agent catches false strong recommendations.
- Weak proxy cases stay visible through trace-linked eval metrics.
- Baseline examples can be replayed through live ADK/Gemini and Phoenix.
- Draft eval rows are not treated as goldens just because an external tool found them.
