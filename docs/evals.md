# Evals

Market Fit Trace Agent uses deterministic evals to prove its core trust claim:
the agent must not turn a tempting adjacent prediction market into a clean
recommendation when the market does not actually express the thesis.

## Commands

Strict local baseline:

```bash
make evals
```

Strict promoted v2 suite:

```bash
make evals-v2
```

Live ADK/Gemini + Phoenix replay:

```bash
make evals-live
make phoenix-check
```

Candidate-pack reports:

```bash
make evals-candidates
make evals-candidates-v3
```

Golden/candidate intake gate:

```bash
make intake-goldens
```

## Eval Packs

| Pack | Role | Strict? |
| --- | --- | --- |
| `evals/market_fit_v1` | Original 10-case baseline covering direct, indirect, weak proxy, and no-clean-expression cases. | Yes |
| `evals/market_fit_v2` | Promoted second suite focused on weak proxies, no-clean-expression, horizon mismatch, and platform mismatch. | Yes |
| `evals/market_fit_v2_candidates` | Staged mining pass. Useful for coverage review, not formal proof. | No |
| `evals/market_fit_v3_candidates` | Second staged mining pass after deduplication. Useful for coverage review, not formal proof. | No |

Candidate packs run with `--allow-failures`. They are not formal goldens until
market snapshots, expected labels, and source provenance are reviewed.

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
- Grok-sourced rows that still require independent review.

Structural errors block promotion. Warnings are review signals: they are expected
for candidate packs and for promoted rows that still exist in archived candidate
folders.

## Demo-Supported Claims

The evals support these README/Devpost claims:

- The agent distinguishes `direct`, `indirect`, `weak_proxy`, and
  `no_clean_expression`.
- The agent catches false strong recommendations.
- Weak proxy cases stay visible through trace-linked eval metrics.
- Baseline examples can be replayed through live ADK/Gemini and Phoenix.
- Candidate rows are not treated as goldens just because an external tool found them.
