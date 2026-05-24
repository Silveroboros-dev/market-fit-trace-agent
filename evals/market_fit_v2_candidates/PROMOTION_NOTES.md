# Market Fit V2 Promotion Notes

Status: staged candidate pack with deterministic classifier coverage.

Do not promote more examples until the `promote_first` cases have reviewed
market snapshots and the remaining partial market-rule captures are resolved.

## Promotion Rule

A case can become a formal golden only when:

- exact source text is frozen;
- at least one candidate market page has been re-opened, or no-market status has
  been confirmed;
- market resolution rules are copied from the public page or API;
- expected fit class is reviewed against entity, event, metric, and horizon;
- the case passes in the candidate eval command; and
- the explanation requirements reject tempting but wrong markets without advice.

## Current Baseline

Command:

```bash
make evals-candidates
```

Current baseline after classifier work: 16/16 pass.

Remaining risk: most market snapshots are verified from public page text, but
the US-Iran permanent-peace market still needs a cleaner specific-outcome rule
capture before promotion into the default golden suite.

## Market Snapshot Status

| Market | Verification Status | Promotion Note |
|---|---|---|
| `pm_gpt56_release_bucket` | verified page text | Good direct-market candidate for `eval_v2_001`. |
| `pm_gpt56_released_by_june_30_2026` | verified search page text | Useful supporting binary market; rules still less rich than the bucket market. |
| `pm_claude_5_released_by` | verified page text | Good naming/version mismatch market for `eval_v2_002`. |
| `pm_hormuz_traffic_normal_end_june_2026` | verified page text | Good objective proxy using ship-transit threshold. |
| `pm_us_iran_permanent_peace_deal_by` | partially verified page text | Useful but stronger than the source claim; keep indirect. |
| `pm_amazon_2026_capex_above` | verified page text | Good weak-proxy example for aggregate AI spend claims. |
| `pm_30y_mortgage_rate_hit_2026` | verified page text | Good weak-proxy example for housing-overpricing claims. |
| `pm_fed_rate_cuts_2026_count` | verified page text | Best indirect market for the no-cuts-until-2028 case because it only covers 2026. |
| `pm_fed_rate_cut_by_2026_meeting` | verified page text | Supporting horizon-mismatch market only, not a separate direct golden. |

## Case Triage

| Case | Topic | Expected Class | Status | Reason |
|---|---|---:|---|---|
| `eval_v2_001` | GPT-5.6 June release | `direct` | `promote_first` | Strong direct market candidate; verify exact Polymarket rules. |
| `eval_v2_002` | Claude 4.8 Opus | `indirect` | `promote_first` | Good naming/horizon mismatch case. |
| `eval_v2_003` | Iran/Hormuz proposal | `indirect` | `promote_first` | Good outcome-proxy case; verify Hormuz traffic rules. |
| `eval_v2_004` | Iran negotiation conditions | `indirect` | `promote_first` | Good granular-source vs broad-market case. |
| `eval_v2_005` | Gemini distribution vs benchmarks | `no_clean_expression` | `promote_first` | Strong benchmark-proxy rejection case. |
| `eval_v2_006` | AMD Helios/MI450X | `no_clean_expression` | `backlog` | Useful but securities-adjacent and needs better market search. |
| `eval_v2_007` | AMD/TSMC/Intel foundry | `no_clean_expression` | `backlog` | Good supply-chain case, but not demo-critical. |
| `eval_v2_008` | AI export controls | `no_clean_expression` | `backlog` | Useful policy case; needs independent market search. |
| `eval_v2_009` | Anthropic-SpaceX compute contract | `no_clean_expression` | `backlog` | Interesting but alleged leak creates verification risk. |
| `eval_v2_010` | AI VC/capex/ROI | `weak_proxy` | `promote_first` | Strong wrong-metric weak-proxy case. |
| `eval_v2_011` | SIBYL memory | `no_clean_expression` | `promote_first` | Good niche AI product no-market case. |
| `eval_v2_012` | Housing overpricing | `weak_proxy` | `promote_first` | Strong macro wrong-metric weak-proxy case. |
| `eval_v2_013` | No Fed cuts until 2028 | `indirect` | `promote_first` | Clean horizon-mismatch indirect case. |
| `eval_v2_014` | Fiscal limits to rate policy | `no_clean_expression` | `backlog` | Good academic causal case but less judge-visible. |
| `eval_v2_015` | Agentic AI vocabulary shift | `no_clean_expression` | `backlog` | Product-relevant, but broad and hard to resolve. |
| `eval_v2_016` | AI fluency in reviews | `no_clean_expression` | `promote_first` | Clear no-market workplace AI case from major outlet. |

## Next Build Tasks

1. Re-open the specific US-Iran permanent-peace outcome page, or keep it partial.
2. Decide whether `eval_v2_006` through `eval_v2_009` should stay backlog or be
   promoted as no-market/no-clean-expression examples.
3. Promote only cases with reviewed market snapshots into a formal `v2` golden
   suite; keep `make evals-candidates` non-CI until then.
