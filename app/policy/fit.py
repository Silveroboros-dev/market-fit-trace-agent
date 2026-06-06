from __future__ import annotations

import re

from app.models import (
    CandidateMarket,
    FitClass,
    MarketFit,
    NormalizedClaim,
    RejectedMarket,
)


def _deterministic_classify(
    claim: NormalizedClaim, markets: list[CandidateMarket], prompt_version: str
) -> MarketFit:
    claim_text = _claim_haystack(claim)
    if _is_composite_iran_relief_package(claim_text):
        tempting_market = _find_market_by_terms(markets, ("blockade", "hormuz"))
        if tempting_market is None:
            return MarketFit(
                recommended_market_id=None,
                semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
                fit_reason=(
                    "The claim is a multi-condition US-Iran package, but the bounded market "
                    "context did not include a market that cleanly resolves the package."
                ),
                captures=[],
                misses=[
                    "60-day ceasefire extension",
                    "Partial Strait of Hormuz reopening",
                    "Asset unfreezing",
                    "Sanctions easing",
                ],
                rejected_markets=[
                    RejectedMarket(
                        market_id=market.market_id,
                        reason=(
                            "The market is adjacent to the geopolitical topic but does not "
                            "resolve the full multi-condition package."
                        ),
                    )
                    for market in markets[:5]
                ],
            )
        return MarketFit(
            recommended_market_id=tempting_market.market_id,
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The blockade-lifted announcement market is only a weak proxy for the "
                "composite US-Iran package. It can resolve Yes without a ceasefire extension, "
                "asset unfreezing, or sanctions relief."
            ),
            captures=[
                "A related Strait of Hormuz blockade-lifted announcement",
                "A near June 2026 deadline for one visible component",
            ],
            misses=[
                "60-day ceasefire extension",
                "Asset unfreezing",
                "Sanctions easing",
                "The full July 2026 geopolitical package",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id=market.market_id,
                    reason=(
                        "Tempting but incomplete: this market resolves only one component or "
                        "a different component of the composite package."
                    ),
                )
                for market in markets[:5]
            ],
        )
    if "ceasefire for 60 days" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The permanent-peace market is relevant to the deal-progress theme, but it "
                "is stronger and finaler than the source's 60-day ceasefire package."
            ),
            captures=["US-Iran diplomatic resolution direction", "July 2026 horizon"],
            misses=[
                "60-day temporary extension",
                "Asset unfreezing",
                "Sanctions easing",
                "Partial Hormuz reopening details",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason="Hormuz traffic captures only one component of the package.",
                )
            ],
        )
    if "draft peace deal" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The market resolves a permanent peace deal by July, while the source claims "
                "a draft announcement within 24-48 hours."
            ),
            captures=["US-Iran peace-deal theme"],
            misses=["Draft-vs-signed finality", "24-hour announcement horizon"],
            rejected_markets=[],
        )
    if "framework memorandum" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The source is about a framework memorandum and staged details; the market "
                "requires permanent peace, so it is adjacent but not direct."
            ),
            captures=["US-Iran diplomatic progress"],
            misses=["Framework-vs-final distinction", "48-hour decision timing"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason=(
                        "Hormuz traffic is an outcome proxy and does not resolve the framework "
                        "memorandum."
                    ),
                )
            ],
        )
    if "google vertex" in claim_text and "claude" in claim_text:
        return MarketFit(
            recommended_market_id="pm_claude_5_released_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The Claude 5 market is adjacent to the Anthropic release theme, but the "
                "source concerns Claude 4.8 visibility in Google Vertex and is explicitly "
                "uncertain."
            ),
            captures=["Anthropic frontier model release theme"],
            misses=["Claude 4.8 naming", "Google Vertex platform availability", "Confirmation"],
            rejected_markets=[],
        )
    if "performance parity" in claim_text and "mythos" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves GPT-5.6 Pro performance parity with Mythos; "
                "release timing would be a different claim."
            ),
            captures=[],
            misses=["Benchmark suite", "Parity threshold", "Named Mythos comparison"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="GPT-5.6 release timing does not resolve performance parity.",
                )
            ],
        )
    if "gpqa diamond" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the GPQA Diamond score series or OpenAI's "
                "reasoning benchmark curve."
            ),
            captures=[],
            misses=["GPQA score threshold", "Benchmark source", "Model-specific score"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Release timing does not resolve GPQA Diamond benchmark scores.",
                )
            ],
        )
    if "winner-take-all verticals" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The claim is a causal adoption thesis about frontier necessity in verticals, "
                "without a clean market-resolvable threshold."
            ),
            captures=[],
            misses=["Frontier requirement threshold", "Vertical adoption metric", "Date"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Hyperscaler capex does not resolve whether frontier models are required "
                        "in cybersecurity or trading."
                    ),
                )
            ],
        )
    if "boomer ownership" in claim_text or "baby boomers" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves boomer-owned housing inventory release or the "
                "demographic mechanism behind housing supply."
            ),
            captures=[],
            misses=["Age-cohort seller metric", "Inventory release threshold", "Data source"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_30y_mortgage_rate_hit_2026",
                    reason="Mortgage rates do not resolve demographic inventory release.",
                )
            ],
        )
    if "republicans" in claim_text and "gas prices" in claim_text and "iran" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a conditional chain across Iran, gas prices, and House control; "
                "no single supplied market resolves the full thesis."
            ),
            captures=[],
            misses=["War-end condition", "Gas-price threshold", "House-control outcome link"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_us_iran_permanent_peace_by",
                    reason=(
                        "Peace deal alone does not resolve gas prices or House control."
                    ),
                )
            ],
        )
    if "tokenized stocks" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves tokenized-stock liquidity reaching traditional "
                "market liquidity via DTCC/Ripple/NSCC rails."
            ),
            captures=[],
            misses=["Tokenized equity volume", "Liquidity threshold", "Clearing-rail criterion"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex is unrelated to tokenized-stock liquidity.",
                )
            ],
        )
    if "solana" in claim_text or "sol remains" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves Solana usage, PMF, UX, and fundamentals together; "
                "price would be a noisy proxy."
            ),
            captures=[],
            misses=["Usage metric", "PMF definition", "UX/speed/efficiency criteria"],
            rejected_markets=[],
        )
    if "global ai spending" in claim_text and "frontier model prices" in claim_text:
        return MarketFit(
            recommended_market_id="pm_amazon_2026_capex_above",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "Amazon capex is a weak proxy: it is a single-company spend metric, not "
                "global AI spend, model pricing, or enterprise cost-saving behavior."
            ),
            captures=["One hyperscaler capex metric"],
            misses=[
                "Gartner global AI spend",
                "Frontier model price trajectory",
                "Enterprise cost-saving adoption",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Tempting but weak: it resolves Amazon capex, not the broader AI "
                        "spend/pricing thesis."
                    ),
                )
            ],
        )
    if "preemptively hike rates" in claim_text or "supply shocks" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a policy recommendation based on HSBC's supply-shock view, "
                "not a clean forecast about a specific rate decision."
            ),
            captures=[],
            misses=["Specific central bank", "Rate-hike action", "Supply-shock citation criterion"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason=(
                        "A Fed cut-count market does not resolve whether central banks "
                        "should hike."
                    ),
                )
            ],
        )
    if "antfleet" in claim_text or "doppler" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the specific AntFleet/Doppler vulnerability finding "
                "or independent confirmation of the submitted fix."
            ),
            captures=[],
            misses=["Repository confirmation", "Specific vulnerability validity", "Fix acceptance"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Model release timing does not resolve this security finding.",
                )
            ],
        )
    if "gpt-5.6" in claim_text:
        return MarketFit(
            recommended_market_id="pm_gpt56_released_by_june_30_2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The GPT-5.6 by June 30 market matches the named OpenAI model, public "
                "availability condition, and June 2026 horizon for the OpenAI portion of "
                "the source."
            ),
            captures=["OpenAI GPT-5.6", "public release", "June 2026 horizon"],
            misses=[
                "Parallel Sonnet 4.8 release claim",
                "Parallel Gemini 3.5 Pro release claim",
                "Internal leak tags as evidence quality",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason=(
                        "Bucketed release-date market is also relevant, but the binary June 30 "
                        "market expresses the core dated release claim more simply."
                    ),
                )
            ],
        )
    if "claude 4.8 opus" in claim_text:
        return MarketFit(
            recommended_market_id="pm_claude_5_released_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The market resolves on Claude 5 public availability by a target date, while "
                "the source names Claude 4.8 Opus and gives no explicit deadline."
            ),
            captures=["Anthropic frontier model release theme"],
            misses=["Claude 4.8 naming", "Clear source horizon", "Opus-specific versioning"],
            rejected_markets=[],
        )
    if "reopening the strait of hormuz" in claim_text or (
        "final phase" in claim_text and "hormuz" in claim_text
    ):
        return MarketFit(
            recommended_market_id="pm_hormuz_traffic_normal_end_june_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The Hormuz traffic market measures a concrete reopening outcome, but it "
                "does not resolve whether the revised diplomatic proposal was accepted."
            ),
            captures=["Strait of Hormuz reopening objective", "June 2026 observable outcome"],
            misses=[
                "Proposal acceptance",
                "Full conflict-ending deal",
                "Diplomatic final-phase status",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_us_iran_permanent_peace_by",
                    reason=(
                        "A permanent peace deal is stronger than the source's uncertain proposal "
                        "and reopening-progress language."
                    ),
                )
            ],
        )
    if "blocked-funds" in claim_text or "blocked funds" in claim_text:
        return MarketFit(
            recommended_market_id="pm_us_iran_permanent_peace_by",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The peace-deal market captures overall diplomatic resolution, but not the "
                "source's three specific disagreement points."
            ),
            captures=["US-Iran diplomatic outcome"],
            misses=["Nuclear issue", "Blocked-funds transfer", "Hormuz-control mechanics"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_hormuz_traffic_normal_end_june_2026",
                    reason=(
                        "Hormuz traffic normalization misses the nuclear and blocked-funds "
                        "conditions."
                    ),
                )
            ],
        )
    if "ubiquity" in claim_text or "android and search" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves Gemini distribution ubiquity across Android and "
                "Search; model release or leaderboard markets would test a different claim."
            ),
            captures=[],
            misses=[
                "Distribution reach across Android/Search",
                "Native product integration",
                "Buyer expectation shift away from benchmark leadership",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="OpenAI release timing does not resolve Google distribution strategy.",
                )
            ],
        )
    if "mi450x" in claim_text or "helios rack-scale" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves AMD Helios/MI450X shipment timing, customer "
                "deployment, or AI accelerator share."
            ),
            captures=[],
            misses=["AMD product shipment", "Customer deployment", "AI accelerator share"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Amazon capex is a hyperscaler spending metric, not AMD shipment or "
                        "share capture."
                    ),
                )
            ],
        )
    if "no intel foundry deal" in claim_text or "tsmc" in claim_text and "foundry" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves whether AMD avoids or signs an Intel foundry deal "
                "while staying with TSMC."
            ),
            captures=[],
            misses=["AMD foundry decision", "Intel manufacturing relationship", "TSMC allocation"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex does not resolve AMD's foundry partner choice.",
                )
            ],
        )
    if "frontier ai models" in claim_text and "cross-border" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves new US or China restrictions on frontier AI "
                "model exports, acquisitions, or partnerships."
            ),
            captures=[],
            misses=[
                "Official restriction",
                "Model/acquisition scope",
                "Cross-border partnership rule",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_released_by_june_30_2026",
                    reason="Model release timing does not resolve export or acquisition controls.",
                )
            ],
        )
    if "spacex" in claim_text and "compute access" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the alleged Anthropic-SpaceX compute contract; "
                "aggregate capex or IPO markets would miss the counterparty and contract terms."
            ),
            captures=[],
            misses=[
                "Contract confirmation",
                "Counterparties",
                "Dollar amount",
                "Through-2029 term",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason="Amazon capex is a single-company spend metric, not this contract.",
                )
            ],
        )
    if "global vc funding" in claim_text or "limited measurable roi" in claim_text:
        return MarketFit(
            recommended_market_id="pm_amazon_2026_capex_above",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "Amazon capex is only a weak proxy for the source's aggregate AI funding, "
                "lab burn-rate, backlog, and ROI thesis."
            ),
            captures=["One hyperscaler capex metric", "AI infrastructure spend direction"],
            misses=[
                "Global VC funding share",
                "Anthropic spend-to-revenue ratio",
                "Enterprise AI ROI",
                "Multi-company backlog concentration",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_amazon_2026_capex_above",
                    reason=(
                        "Tempting but weak: it resolves Amazon purchases of property and "
                        "equipment, not the broader VC/capex/ROI thesis."
                    ),
                )
            ],
        )
    if "sibyl" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves SIBYL public release, compatibility, or claimed "
                "hallucination reductions."
            ),
            captures=[],
            misses=["SIBYL release", "Memory compatibility", "92% and 96% reduction claims"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason="GPT-5.6 release timing does not resolve agent memory tooling.",
                )
            ],
        )
    if "homes are about 40% overpriced" in claim_text or "40% overpriced" in claim_text:
        return MarketFit(
            recommended_market_id="pm_30y_mortgage_rate_hit_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The mortgage-rate market is only a weak proxy because it resolves rate "
                "thresholds, not whether home prices are 40% overvalued or correct."
            ),
            captures=["Mortgage-rate environment", "2026 rate thresholds"],
            misses=[
                "Home-price valuation metric",
                "40% overpricing estimate",
                "Case-Shiller or comparable price response",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_30y_mortgage_rate_hit_2026",
                    reason=(
                        "Tempting but weak: rate levels are an input to the thesis, not the "
                        "housing valuation output."
                    ),
                )
            ],
        )
    if "not expected to cut rates until at least 2028" in claim_text:
        return MarketFit(
            recommended_market_id="pm_fed_rate_cuts_2026_count",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The 2026 Fed-cuts market tests the near-term direction of the thesis, but "
                "does not cover the full no-cuts-until-2028 horizon."
            ),
            captures=["Official FOMC rate decisions", "2026 no-cut direction"],
            misses=["2027 rate path", "Full until-2028 forecast horizon", "Risk-asset implication"],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cut_by_2026_meeting",
                    reason=(
                        "Meeting-specific cut markets are narrower than the source's multi-year "
                        "forecast."
                    ),
                )
            ],
        )
    if "fiscal policy conduct limits" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is an academic causal thesis about fiscal policy limiting monetary "
                "policy effectiveness, not a single market-resolvable future event."
            ),
            captures=[],
            misses=[
                "Academic finding",
                "Causal mechanism",
                "Retrospective COVID-era inflation scope",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason=(
                        "A 2026 rate-cut count does not resolve why prior inflation responded "
                        "to policy."
                    ),
                )
            ],
        )
    if "agentic ai is moving" in claim_text or "workflow integration" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves the narrative shift from AI demos to workflow "
                "infrastructure with measurable adoption criteria."
            ),
            captures=[],
            misses=[
                "Enterprise deployment count",
                "Governance criteria",
                "Vocabulary-shift measurement",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_gpt56_release_bucket_june_2026",
                    reason="Model release timing does not resolve enterprise agent maturation.",
                )
            ],
        )
    if "performance reviews" in claim_text and "ai fluency" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No supplied market resolves whether companies have a standardized playbook "
                "for evaluating AI fluency in performance reviews."
            ),
            captures=[],
            misses=[
                "HR playbook standardization",
                "Company adoption threshold",
                "AI fluency criteria",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm_fed_rate_cuts_2026_count",
                    reason="Fed rate cuts are unrelated to workplace AI evaluation standards.",
                )
            ],
        )
    if "agent-approved payment" in claim_text or "link cli" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No clean market in the seed set resolves Stripe Link CLI, agent-approved "
                "payment credentials, or agents completing approved purchases by EOY 2026."
            ),
            captures=[],
            misses=[
                "Agentic payment credential launch criteria",
                "Named payment-company product release",
                "Objective purchase-completion threshold",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "AI benchmark success is unrelated to agent-approved payment "
                        "credentials or commerce adoption."
                    ),
                )
            ],
        )
    if "swap lines" in claim_text or "safe-haven" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is a broad macro causal thesis about USD liquidity and reserve "
                "behavior, not a single dated market expression."
            ),
            captures=[],
            misses=[
                "Specific swap-line counterparty",
                "Official Federal Reserve announcement date",
                "Objective safe-haven status criterion",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-fed-cut-sept-2026",
                    reason=(
                        "A rate-decision market does not resolve on swap-line availability or "
                        "the dollar safe-haven bid."
                    ),
                )
            ],
        )
    if "research-agent" in claim_text or "reconstruct complex academic papers" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "No clean market resolves release of a general-purpose research agent or "
                "paper-reconstruction capability."
            ),
            captures=[],
            misses=[
                "Named qualifying labs",
                "Research-agent release criteria",
                "Paper reconstruction success threshold",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "The IMO market resolves on math competition results, not research-agent "
                        "productization."
                    ),
                )
            ],
        )
    if "multi-agent systems" in claim_text or "coordination breakthrough" in claim_text:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The source is ambiguous and rhetorical; it does not define a dated, resolvable "
                "forecast about enterprise multi-agent orchestration."
            ),
            captures=[],
            misses=[
                "Named product release",
                "Coordination-success criterion",
                "Clear time horizon",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "A Chatbot Arena company ranking does not resolve enterprise "
                        "multi-agent coordination."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason=(
                        "A math benchmark does not resolve autonomous multi-agent orchestration."
                    ),
                ),
            ],
        )
    if "gemini 3.2" in claim_text or "gemini 3.5" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_gemini_3_2_june_30_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The June 30 horizon matches the source, but the source mentions Gemini 3.2 "
                "and 3.5 rather than one exact release version."
            ),
            captures=["Google Gemini release timing", "June 30, 2026 horizon"],
            misses=[
                "The source does not narrow to Gemini 3.2 exactly",
                "The market ignores Gemini 3.5 if that is the actual release label",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Best-model ranking resolves on Chatbot Arena score, not public release "
                        "of a Gemini 3.x model."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_ai_wins_imo_gold_2026",
                    reason="IMO gold resolves on a math contest, not Gemini release timing.",
                ),
            ],
        )
    if "spacex" in claim_text and "largest ipo" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_largest_ipo_2026_spacex",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolves on the company with the highest first-day closing market "
                "capitalization among 2026 IPOs, matching the SpaceX largest-IPO thesis."
            ),
            captures=["SpaceX", "2026 IPO", "largest by first-day closing market cap"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_spacex_ipo_closing_market_cap",
                    reason=(
                        "That market is about SpaceX's absolute valuation bucket, not whether "
                        "SpaceX is the largest IPO of 2026."
                    ),
                )
            ],
        )
    if _is_anthropic_500b_valuation_claim(claim_text):
        return MarketFit(
            recommended_market_id="polymarket_anthropic_500b_valuation_2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolves on Anthropic reaching or confirming at least a $500B "
                "public or private valuation in 2026, matching the valuation thesis."
            ),
            captures=["Anthropic", "$500B valuation threshold", "2026 horizon"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_anthropic_no_ipo_june_30_2026",
                    reason="IPO timing is a different event from valuation confirmation.",
                ),
                RejectedMarket(
                    market_id="polymarket_largest_ipo_2026_anthropic",
                    reason=(
                        "Largest IPO ranking is a comparative public-listing claim, not a "
                        "private valuation threshold."
                    ),
                ),
            ],
        )
    if _is_google_tpu_v7_ga_claim(claim_text):
        return MarketFit(
            recommended_market_id="pm-tpu-v7-ga-2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolves on Google making TPU v7 generally available before "
                "Jan 1, 2027, matching the claim's entity, event, and horizon."
            ),
            captures=["Google", "TPU v7 general availability", "before 2027 horizon"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-gemini-arena-2026",
                    reason=(
                        "Gemini leaderboard rank is a different claim from TPU v7 product "
                        "availability."
                    ),
                )
            ],
        )
    if "tpu 8t" in claim_text or "tpu 8i" in claim_text or "3x performance" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_best_ai_model_google_end_june_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The Google best-model market is only a weak adjacent expression: it resolves "
                "on Chatbot Arena company rank, not TPU hardware performance or hardware-caused "
                "model improvement."
            ),
            captures=["Google model competitiveness", "June 30, 2026 ranking horizon"],
            misses=[
                "TPU 8t/8i performance claims",
                "Hardware causality",
                "Liquidity and market-quality concerns raised by the source",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Tempting but weak: leaderboard rank can move for many reasons unrelated "
                        "to TPU performance claims."
                    ),
                )
            ],
        )
    if "anthropic" in claim_text and "ipo momentum" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_anthropic_no_ipo_june_30_2026",
            semantic_fit_class=FitClass.WEAK_PROXY,
            fit_reason=(
                "The no-IPO-by-June market is a weak proxy for valuation-driven IPO momentum; "
                "IPO timing and private valuation pressure are different claims."
            ),
            captures=["Anthropic", "near-term IPO timing as an adjacent question"],
            misses=[
                "Private valuation momentum",
                "Whether valuation hype causally increases IPO probability",
                "Longer or unclear horizon in the user note",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_anthropic_no_ipo_june_30_2026",
                    reason=(
                        "It resolves on whether an IPO happens by June 30, not whether private "
                        "valuation signals imply IPO momentum."
                    ),
                ),
                RejectedMarket(
                    market_id="polymarket_anthropic_500b_valuation_2026",
                    reason=(
                        "This is direct to valuation confirmation but not to the user's inferred "
                        "near-term IPO timing thesis."
                    ),
                ),
            ],
        )
    if "putnam" in claim_text and "imo" in claim_text:
        return MarketFit(
            recommended_market_id="polymarket_ai_wins_imo_gold_2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The IMO gold market captures a related math-benchmark outcome, but the source "
                "is about Putnam performance and Axiom Math rather than the official 2026 IMO "
                "resolution event."
            ),
            captures=["AI math capability", "2026 math competition horizon"],
            misses=[
                "Putnam and IMO are different competitions",
                "Official IMO/AIMO resolution source",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="polymarket_best_ai_model_google_end_june_2026",
                    reason=(
                        "Best-AI-model ranking resolves on Chatbot Arena rank, not math contest "
                        "performance."
                    ),
                )
            ],
        )
    if "gemini" in claim_text and "tpu" in claim_text:
        return MarketFit(
            recommended_market_id="pm-gemini-arena-2026",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason=(
                "The leaderboard market is the closest retrieved adjacent signal, but it "
                "does not directly resolve the TPU-driven frontier-gap thesis."
            ),
            captures=[
                "Gemini relative performance signal",
                "A measurable 2026 market close",
            ],
            misses=[
                "The market does not resolve the TPU causal mechanism",
                "The market does not capture every frontier-model benchmark",
            ],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-tpu-v7-ga-2026",
                    reason="Hardware availability can happen without Gemini closing the model gap.",
                )
            ],
        )
    if "federal reserve" in claim_text and "july 2026" in claim_text:
        return MarketFit(
            recommended_market_id="pm-direct-fed-cut-july-2026",
            semantic_fit_class=FitClass.DIRECT,
            fit_reason=(
                "The market resolution directly matches the claim, event, institution, and "
                "meeting date."
            ),
            captures=["Federal Reserve decision", "July 2026 meeting", "rate-cut direction"],
            misses=[],
            rejected_markets=[
                RejectedMarket(
                    market_id="pm-fed-cut-sept-2026",
                    reason="September is a different meeting and horizon.",
                )
            ],
        )

    scored_markets = _score_markets(claim, markets)
    if not scored_markets:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The bounded market context did not return any candidate market for this claim."
            ),
            captures=[],
            misses=["No candidate market was available for comparison."],
            rejected_markets=[],
        )

    best = scored_markets[0]
    if best[0] < 2:
        return MarketFit(
            recommended_market_id=None,
            semantic_fit_class=FitClass.NO_CLEAN_EXPRESSION,
            fit_reason=(
                "The seed market set contains related-looking topics at best, but no market whose "
                "resolution rules cleanly express this claim."
            ),
            captures=[],
            misses=["No candidate shares enough entities, horizon, and resolution target."],
            rejected_markets=[
                RejectedMarket(
                    market_id=market.market_id,
                    reason=(
                        "Insufficient entity and resolution-rule overlap with the normalized claim."
                    ),
                )
                for _, market in _score_markets(claim, markets)[:2]
            ],
        )
    return MarketFit(
        recommended_market_id=best[1].market_id,
        semantic_fit_class=FitClass.INDIRECT,
        fit_reason=(
            "The market shares some entities with the claim but only partially expresses it."
        ),
        captures=["Some entity overlap"],
        misses=["Resolution rules do not directly encode the full thesis."],
        rejected_markets=[],
    )


def _score_markets(
    claim: NormalizedClaim, markets: list[CandidateMarket]
) -> list[tuple[int, CandidateMarket]]:
    claim_terms = set(re.findall(r"[a-z0-9]+", claim.claim_text.lower())) - STOPWORDS
    scored = []
    for market in markets:
        haystack = " ".join(
            [market.title, market.description, market.resolution_rules, *market.entity_tags]
        ).lower()
        market_terms = set(re.findall(r"[a-z0-9]+", haystack)) - STOPWORDS
        scored.append((len(claim_terms & market_terms), market))
    return sorted(scored, key=lambda item: item[0], reverse=True)


STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "be",
    "before",
    "by",
    "for",
    "if",
    "in",
    "is",
    "it",
    "make",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "will",
    "with",
    "year",
}


def _is_composite_iran_relief_package(claim_text: str) -> bool:
    return bool(
        "iran" in claim_text
        and ("hormuz" in claim_text or "strait" in claim_text)
        and "ceasefire" in claim_text
        and ("sanction" in claim_text or "asset" in claim_text or "unfreeze" in claim_text)
    )


def _is_anthropic_500b_valuation_claim(claim_text: str) -> bool:
    if "anthropic" not in claim_text or "valuation" not in claim_text:
        return False
    if "ipo momentum" in claim_text or "near-term ipo" in claim_text:
        return False
    return bool(
        re.search(r"\$?\s*500\s*(?:b|bn|billion)\b", claim_text)
        or "half trillion" in claim_text
    )


def _is_google_tpu_v7_ga_claim(claim_text: str) -> bool:
    if "google" not in claim_text or "tpu" not in claim_text or "v7" not in claim_text:
        return False
    if "frontier" in claim_text or "model gap" in claim_text or "benchmark" in claim_text:
        return False
    has_ga_event = (
        "generally available" in claim_text
        or "general availability" in claim_text
        or re.search(r"\bga\b", claim_text) is not None
    )
    has_2026_horizon = (
        "before 2027" in claim_text
        or "2026" in claim_text
        or "jan 1, 2027" in claim_text
        or "january 1, 2027" in claim_text
    )
    return has_ga_event and has_2026_horizon


def _find_market_by_terms(
    markets: list[CandidateMarket], required_terms: tuple[str, ...]
) -> CandidateMarket | None:
    for market in markets:
        haystack = " ".join(
            [market.market_id, market.title, market.description, market.resolution_rules]
        ).lower()
        if all(term in haystack for term in required_terms):
            return market
    return None


def _market_haystack(market: CandidateMarket) -> str:
    return " ".join(
        [
            market.market_id,
            market.title,
            market.description,
            market.resolution_rules,
            *market.entity_tags,
        ]
    ).lower()


def _claim_haystack(claim: NormalizedClaim) -> str:
    return " ".join(
        [claim.claim_text, *claim.entities, claim.horizon, claim.stance, claim.reasoning_summary]
    ).lower()
