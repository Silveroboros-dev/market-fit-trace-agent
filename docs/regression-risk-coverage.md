# Regression-Risk Coverage Audit: Market-Fit Policy With Live PolyData Retrieval

Status: audit only. No candidates are promoted by this document.

## Purpose

Live PolyData retrieval makes Market Fit Trace Agent more useful, but it changes
the risk profile of the deterministic fit policy. Frozen evals still protect the
strict product claim. Live retrieval adds current, bounded market context with
different IDs, missing rules, event/market grouping, fresh prices, and ranking
noise.

This report maps the highest-risk policy behaviors to existing protective
goldens and missing candidate coverage.

## Files Inspected

- `app/policy/fit.py`
- `app/market_provider.py`
- `evals/market_fit_v1/examples.jsonl`
- `evals/market_fit_v1/expected_outputs.jsonl`
- `evals/market_fit_v1/market_snapshots.jsonl`
- `evals/market_fit_v2/examples.jsonl`
- `evals/market_fit_v2/expected_outputs.jsonl`
- `evals/market_fit_v2/market_snapshots.jsonl`
- `evals/market_fit_v2_candidates/README.md`
- `evals/market_fit_v2_candidates/PROMOTION_NOTES.md`
- `evals/market_fit_v2_candidates/expected_outputs.jsonl`
- `evals/market_fit_v3_candidates/README.md`
- `evals/market_fit_v3_candidates/PROMOTION_NOTES.md`
- `evals/market_fit_v3_candidates/expected_outputs.jsonl`
- `evals/retrieval_candidates/2026-05-26/demo-hormuz-candidate/*`

## Key Architecture Boundary

Live retrieval and strict eval truth remain separate:

```text
PolyData live retrieval -> candidate evidence
Frozen repo fixtures -> strict eval truth
Human review -> promotion decision
```

This audit does not create expected labels and does not promote candidates.

## Risk Matrix

| Risk Area | Affected Rule Or Behavior | Existing Protective Golden Cases | Missing Coverage | Proposed Candidate Thesis | Live Retrieval Or Frozen Fixture Needed | Priority |
|---|---|---|---|---|---|---|
| Live market ID namespace mismatch | `fit.py` has hard-coded fixture market IDs such as `pm_hormuz_traffic_normal_end_june_2026`, `pm_us_iran_permanent_peace_by`, `polymarket_*`; PolyData currently returns live numeric IDs such as `2155023`. A pattern branch can recommend a fixture ID that is absent from the live candidate set. | Fixture goldens protect static IDs: `eval_005`, `eval_006`, `eval_007`, `eval_010`; `test_missing_recommended_market_is_guarded_to_no_clean_expression` now checks that absent recommended IDs are downgraded to `no_clean_expression`. | Still missing a promoted golden with reviewed live market rules; the guard is covered as workflow behavior, not strict market-fit truth. | "AI IS EATING 80% OF GLOBAL VC FUNDING..." live packet showed a fixture-style Amazon capex ID absent from live PolyData retrieval; current reviewed candidate outcome is `no_clean_expression`. | Live retrieval candidate first; freeze the retrieval packet before turning into a strict golden. | P0 |
| Missing resolution rules in live candidates | `PolyDataMarketProvider._row_to_candidate_market()` sets `resolution_rules=""` and adds `missing_resolution_rules`. The fallback `_score_markets()` still scores title/description/tags and can classify `indirect` from overlap even when rules are missing. | Weak-proxy fixture cases: `eval_008`, `eval_009`, `eval_v2_010`, `eval_v2_012`, `eval_v3_012`. No-clean fixture cases reject benchmark/no-market claims. | No strict case requires conservative behavior when all retrieved candidates have `rules_status=missing`. | "A market looks relevant from title/tags, but resolution rules are unavailable." Use a live PolyData packet where all rules are missing and require reviewer status `needs_more_rules` before promotion. | Live retrieval candidate; later frozen fixture with explicit `rules_status=missing`. | P0 |
| Lexical-overlap fallback overstates fit | If no hard-coded pattern matches, `_score_markets()` ranks by token overlap across title, description, rules, and tags. If best score is at least 2, the policy returns `indirect`. Live retrieval can produce high-overlap wrong markets. | `eval_003`, `eval_004`, `eval_008`, `eval_009`; v2/v3 capex, mortgage, Claude, benchmark, and Iran proxy cases. | Missing generic live-retrieval case where high token overlap is caused by tags/category rather than resolution target. | "Iran ceasefire extension causes oil volatility" with live markets about Hormuz traffic, uranium enrichment, or Trump announcements. The correct label may be weak proxy or no clean expression after human review. | Live retrieval candidate; freeze selected markets and rules before strict eval. | P0 |
| Event-level relevance hides market-level mismatch | `market_provider.py` preserves event/market fields in description, but `_source_url()` derives an event URL and policy scoring does not distinguish parent event relevance from specific market question. | v1 wrong-market cases around Chatbot Arena/IMO; v2/v3 Claude and Iran cases partly protect market-specific mismatch. | No live candidate where a parent event is relevant but the selected market question is the wrong outcome within the event. | "US-Iran deal includes sanctions relief" while retrieved event contains markets for Hormuz traffic, uranium enrichment, and Trump announcement. | Live retrieval candidate with event_id/event_slug and specific market_id frozen. | P0 |
| Strong direct classification from phrase branch | Branches such as `gpt-5.6` and SpaceX/Anthropic direct cases return `direct` without checking whether the retrieved live market's rules are present, current, open, or same market family. | Direct goldens: `eval_006`, `eval_007`, v2 candidate `eval_v2_001`. | No live case where phrase branch is direct but PolyData retrieves a related market with missing/partial rules or different date bucket. | "GPT-5.6 by June 30" when PolyData returns a bucketed GPT release market plus another binary market. Verify direct/indirect based on frozen rules. | Live retrieval candidate, then frozen fixture. | P1 |
| Horizon mismatch with live current markets | Policy has hard-coded horizon distinctions for Gemini, Fed cuts, Claude, and Iran draft/final claims. Live retrieval ranking can surface markets with close dates that look close but do not match the claim horizon. | `eval_005`, `eval_v2_013`, `eval_v3_002`, `eval_v3_003`, `eval_v3_004`. | Missing live case where current close date is near but not enough: e.g. May 31 vs June 30, 2026. | "Strait of Hormuz traffic returns to normal by end of June" while retrieval includes May 31 traffic-count markets and June 30 announcement markets. | Live retrieval candidate; freeze close dates and rules. | P1 |
| Wrong metric / causal proxy under high liquidity | PolyData ranking includes volume boost. High-volume markets may dominate even when they resolve the wrong metric. | `eval_v2_010` Amazon capex weak proxy, `eval_v2_012` mortgage-rate weak proxy, `eval_v3_012` global AI spending weak proxy. | Missing live case proving high liquidity must not upgrade a wrong metric to indirect/direct. | "AI capex proves enterprise AI ROI is bad" with high-volume hyperscaler capex markets. | Live retrieval candidate or frozen fixture from existing v2/v3 candidates after review. | P1 |
| Open/closed/current-market filtering drift | `PolyDataMarketProvider.retrieve()` filters `closed`, `archived`, `active`, and `days_to_close` when fields exist. If provider columns change or fields are absent, stale markets can remain. | `tests/test_market_provider.py` likely protects provider mode basics, but current promoted goldens are fixture-only and do not protect live status drift. | No candidate asserts behavior when status fields are missing, false, string-encoded, or stale. | "Fed cut by next meeting" with one active and one closed/stale market in the retrieval packet. | Frozen provider fixture is enough; no live API needed after capturing representative rows. | P1 |
| Candidate-market set too small or too broad | PolyData uses `top_k`, `max_k`, min volume, taxonomy confidence, and optional L1 allowlist. A relevant low-volume niche market can be excluded, or a broad high-volume market can crowd it out. | No strict goldens cover retrieval quality; strict evals intentionally bypass live APIs. | Need retrieval-candidate review cases, not strict eval pass/fail yet. | "Workplace AI fluency performance reviews" where no good market exists but generic AI adoption markets may appear. | Live retrieval candidate for reviewer queue; not strict eval unless a market context is frozen. | P2 |
| No-clean-expression false positives from live tags | Fallback returns no clean expression only when no scored market or score below 2. Live taxonomy tags can add enough overlap to push broad narrative claims into `indirect`. | `eval_001`-`eval_004`, `eval_v3_005`, `eval_v3_007`, `eval_v3_008`, `eval_v3_010`, `eval_v3_011`, `eval_v3_013`, `eval_v3_014`. | Missing live retrieval examples for broad no-objective-resolution claims with many overlapping taxonomy tags. | "Agentic AI has shifted from demos to workflow infrastructure" with live AI markets retrieved by taxonomy. | Live retrieval candidate; freeze the returned context before promotion. | P1 |
| Weak-proxy detection depends on risk tags | `evaluate_fit()` flags weak proxies using `market.known_fit_risks` containing `"weak_proxy"`. Live PolyData markets get generic risks like `dynamic_polydata_retrieval` and `missing_resolution_rules`, not domain-specific weak-proxy risks. | Fixture weak-proxy cases protect known IDs with `MARKET_FIT_RISKS`. | Live PolyData candidates may not set domain-specific weak-proxy risk tags, so eval flags can under-report weak-proxy failures. | "Amazon capex as proxy for global AI ROI" using a live PolyData Amazon capex market. Compare eval metrics against frozen weak-proxy expectation. | Live retrieval candidate, then frozen fixture with reviewed `known_fit_risks`. | P0 |
| Multi-condition diplomatic package collapsed into one market | Several Iran branches distinguish temporary ceasefire, draft peace, framework memorandum, Hormuz reopening, blocked funds, and permanent peace. Live retrieval may return one best market that captures only one component. | v2/v3 Iran candidates: `eval_v2_003`, `eval_v2_004`, `eval_v3_001`, `eval_v3_002`, `eval_v3_003`; retrieval candidate `demo-hormuz-candidate`. | Need one live-retrieval packet with all relevant current Iran/Hormuz markets and reviewed expected behavior. | "The US and Iran extend a ceasefire, partially reopen Hormuz, unfreeze assets, and ease sanctions by July 2026." | Live retrieval candidate already exists in rough form; needs human review and frozen rules before promotion. | P0 |
| Human-review boundary not visible in strict reports | Candidate Dataset rows are pending evidence; promoted Dataset rows contain expected labels. Risk is conceptual regression: candidate rows accidentally acquire expected labels or are treated as truth. | `tests/test_candidate_review_dataset.py`; `tests/test_promoted_goldens_dataset.py`; docs/golden-promotion.md. | Need periodic audit that candidate rows still lack `expected_*` fields after exporter changes. | Use current `demo-hormuz-candidate` candidate packet as a standing candidate-export regression check. | Frozen local candidate packet is enough; no live retrieval needed. | P1 |

## Highest-Priority Candidate Goldens To Create Next

These are not labels. They are candidate-golden proposals for human review.

| Candidate | Why It Matters | Proposed Source Thesis | Retrieval Need | Suggested Review Outcome To Decide |
|---|---|---|---|---|
| Live Hormuz multi-market packet | Tests numeric live IDs, missing rules, event/market mismatch, and multi-condition diplomacy. | "US and Iran will extend a ceasefire, reopen Hormuz, unfreeze assets, and ease sanctions by July 2026." | Live PolyData packet already exists; needs rules capture. | Decide between `indirect` and `weak_proxy`; record tempting wrong markets. |
| Live Amazon capex / AI ROI packet | Tests high-liquidity wrong-metric retrieval and weak-proxy risk tags. | "AI spending and hyperscaler capex show poor enterprise ROI." | Live PolyData preferred; can start from v2/v3 frozen markets. | Likely weak proxy if only Amazon capex is available, but human review required. |
| Live no-objective AI adoption packet | Tests no-clean false positives from taxonomy tags. | "Agentic AI is shifting from demos to governed enterprise workflow infrastructure." | Live PolyData preferred to see what broad AI markets surface. | Likely no clean expression unless a specific deployment-count market exists. |
| Live event-vs-market mismatch packet | Tests whether event relevance overstates specific market fit. | "Iran sanctions relief is the decisive condition for peace." | Live PolyData event with multiple markets required. | Likely no clean expression or weak proxy unless a sanctions-specific market is returned. |
| Live closed/stale market fixture | Tests provider status filtering and stale data behavior. | "Fed cuts by the next FOMC meeting." | Frozen synthetic/provider fixture sufficient after observing field names. | Not a market-fit label first; provider regression test first. |

## Coverage Summary

Current promoted goldens cover the core semantic classes well:

- `direct`: `eval_006`, `eval_007`; v2 candidate `eval_v2_001`.
- `indirect`: `eval_005`, `eval_010`, `eval_v2_013`, `eval_v3_004`.
- `weak_proxy`: `eval_008`, `eval_009`, `eval_v2_010`, `eval_v2_012`,
  `eval_v3_012`.
- `no_clean_expression`: `eval_001`-`eval_004`, `eval_v3_005`, and many v2/v3
  candidate negatives.

The remaining gap is not the four-class taxonomy itself. The gap is live
retrieval interaction:

1. live numeric IDs versus fixture IDs;
2. missing resolution rules;
3. event-level relevance versus market-level question;
4. high-volume wrong metrics;
5. generic live risk tags that do not trigger weak-proxy eval metrics.

## Recommended Next Work

1. Use `make export-retrieval-candidate` on the Hormuz package thesis and freeze
   the exact live retrieved markets plus available rules.
2. Add a reviewer note deciding whether the current Hormuz candidate is
   `indirect`, `weak_proxy`, or `no_clean_expression`; do not promote before
   rules are captured.
3. Create one live Amazon capex / AI ROI retrieval candidate to test whether
   weak-proxy detection survives live PolyData IDs and generic risk tags.
4. Add a provider-level fixture test for stale/closed markets if PolyData field
   shapes remain stable.
5. Keep all new cases in candidate packs until expected labels are reviewed.

## Non-Changes

This audit did not modify production code.

This audit did not promote any candidate.

This audit did not create or change expected labels.

Strict evals remain fixture-based.
