# Market Fit V3 Promotion Notes

Status: staged candidate pack.

## Current Baseline

Command:

```bash
make evals-candidates-v3
```

Expected after deterministic classifier intake: 14/14 candidate pass.

## Promotion Rule

A v3 case can become a formal golden only when:

- exact source text is frozen;
- duplicate status is checked against v1 and v2;
- any candidate market has verified resolution rules;
- expected fit class is reviewed against entity, event, metric, and horizon;
- the case passes the candidate eval command; and
- explanation requirements reject tempting but wrong markets without advice.

## Case Triage

| Case | Topic | Expected Class | Status | Reason |
|---|---|---:|---|---|
| `eval_v3_001` | Iran ceasefire extension package | `indirect` | `promote_later` | Good multi-part diplomacy vs stronger peace market case. |
| `eval_v3_002` | Iran draft peace announcement | `indirect` | `promote_later` | Good draft/24-hour horizon mismatch. |
| `eval_v3_003` | Iran framework memorandum | `indirect` | `promote_later` | Good framework-vs-final-deal distinction. |
| `eval_v3_004` | Claude 4.8 in Google Vertex | `indirect` | `promote_later` | Good platform availability vs public Claude 5 market case. |
| `eval_v3_005` | GPT-5.6 Pro vs Mythos parity | `no_clean_expression` | `promote_later` | Strong benchmark/performance-parity no-market case. |
| `eval_v3_006` | GPT-5 benchmark curve | `no_clean_expression` | `backlog` | Useful benchmark-claim negative. |
| `eval_v3_007` | Frontier models required in verticals | `no_clean_expression` | `backlog` | Broad but useful causal/adoption negative. |
| `eval_v3_008` | Boomer housing supply | `no_clean_expression` | `backlog` | Clear demographic causal thesis without clean market. |
| `eval_v3_009` | Iran war, gas prices, House control | `no_clean_expression` | `promote_later` | Good conditional multi-causal election proxy rejection. |
| `eval_v3_010` | Tokenized stocks liquidity | `no_clean_expression` | `backlog` | Crypto market-structure thesis needs better market search. |
| `eval_v3_011` | SOL usage/PMF thesis | `no_clean_expression` | `backlog` | Qualitative price-adjacent crypto thesis. |
| `eval_v3_012` | AI spend and model pricing | `weak_proxy` | `promote_later` | Good Amazon-capex wrong-metric proxy case. |
| `eval_v3_013` | Central banks should hike | `no_clean_expression` | `backlog` | Policy recommendation, not a clean event claim. |
| `eval_v3_014` | AntFleet code review finding | `no_clean_expression` | `backlog` | Specific benchmark/security claim without public market. |

## Next Build Tasks

1. Verify whether any retained `no_clean_expression` cases have real Kalshi or
   Manifold markets before promotion.
2. Keep the three new Iran examples as candidate-only until the US-Iran
   permanent-peace market has exact specific-outcome rules captured.
3. Do not mine another broad batch until v2 and selected v3 cases are promoted
   or deliberately rejected.
