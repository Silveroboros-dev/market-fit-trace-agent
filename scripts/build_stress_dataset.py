"""Generate the stress-40 synthetic market-fit stress dataset.

Produces evals/stress_test_v1/stress_cases.jsonl — 40 cases across 7 mismatch
families.  No API calls.  Each case is a (thesis, synthetic market, expected
label, trap) tuple where the label is controlled by construction.

Usage:
    python scripts/build_stress_dataset.py
    # or: make build-stress-40
"""
# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_DIR = Path("evals/stress_test_v1")
OUTPUT_FILE = OUTPUT_DIR / "stress_cases.jsonl"
SCHEMA_VERSION = "stress_case_v1"


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _case(
    *,
    case_id: str,
    thesis: str,
    market_id: str,
    market_title: str,
    resolution_rules: str,
    close_date: str = "2026-12-31",
    outcomes: list[str] | None = None,
    entity_tags: list[str],
    expected_fit_class: str,
    mismatch_family: str,
    trap_description: str,
) -> dict:
    return {
        "case_id": case_id,
        "schema_version": SCHEMA_VERSION,
        "thesis": thesis,
        "market": {
            "market_id": market_id,
            "title": market_title,
            "venue": "SyntheticStress",
            "description": resolution_rules,
            "resolution_rules": resolution_rules,
            "close_date": close_date,
            "outcomes": outcomes or ["Yes", "No"],
            "current_probability": None,
            "known_fit_risks": ["synthetic_stress_case"],
            "entity_tags": entity_tags,
        },
        "expected_fit_class": expected_fit_class,
        "mismatch_family": mismatch_family,
        "trap_description": trap_description,
        "truth_scope": "synthetic_expected_label",
        "expected_label_source": "constructed_template",
        "canonical_truth": False,
    }


# ---------------------------------------------------------------------------
# Family 1: Event stage mismatch (8 cases)
# ---------------------------------------------------------------------------

EVENT_STAGE = [
    _case(
        case_id="stress_es_openai_filing_vs_completion_001",
        thesis="OpenAI is preparing to file confidentially for an IPO in the coming weeks.",
        market_id="synth_openai_ipo_cap_300b",
        market_title="OpenAI IPO closing market cap above $300B in 2026?",
        resolution_rules=(
            "Resolves Yes if OpenAI completes an IPO and the closing price on its "
            "first trading day implies a market capitalization above $300 billion. "
            "Resolution uses the official exchange listing page."
        ),
        entity_tags=["OpenAI", "IPO", "market cap"],
        expected_fit_class="weak_proxy",
        mismatch_family="event_stage_mismatch",
        trap_description="Entity + topic overlap, but confidential filing preparation is not IPO completion or valuation.",
    ),
    _case(
        case_id="stress_es_openai_roadshow_vs_timing_002",
        thesis="OpenAI has begun its IPO roadshow and is meeting with institutional investors this week.",
        market_id="synth_openai_ipo_by_sept_2026",
        market_title="Will OpenAI complete its IPO by September 2026?",
        resolution_rules=(
            "Resolves Yes if OpenAI common shares begin trading on a public exchange "
            "on or before September 30, 2026. Resolution uses the official exchange listing."
        ),
        entity_tags=["OpenAI", "IPO"],
        expected_fit_class="indirect",
        mismatch_family="event_stage_mismatch",
        trap_description="Roadshow is strong directional evidence for IPO completion, but not the same event. Indirect, not direct.",
    ),
    _case(
        case_id="stress_es_anthropic_acquisition_vs_valuation_003",
        thesis="Anthropic is in early-stage acquisition discussions with a major cloud provider.",
        market_id="synth_anthropic_500b_val",
        market_title="Anthropic $500B+ valuation in 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic achieves a public or private valuation of at "
            "least $500 billion, confirmed by the company or credible reporting, "
            "by December 31, 2026."
        ),
        entity_tags=["Anthropic", "valuation"],
        expected_fit_class="weak_proxy",
        mismatch_family="event_stage_mismatch",
        trap_description="Acquisition talks could affect valuation, but the thesis is about M&A, not a valuation threshold.",
    ),
    _case(
        case_id="stress_es_spacex_underwriters_vs_largest_004",
        thesis="SpaceX has reportedly hired Goldman Sachs and Morgan Stanley as lead IPO underwriters.",
        market_id="synth_spacex_largest_ipo_2026",
        market_title="Will SpaceX have the largest IPO by market cap in 2026?",
        resolution_rules=(
            "Resolves to SpaceX if it achieves the highest first-day closing market "
            "capitalization among 2026 IPOs. Resolution uses the official exchange listing."
        ),
        entity_tags=["SpaceX", "IPO", "market cap"],
        expected_fit_class="indirect",
        mismatch_family="event_stage_mismatch",
        trap_description="Hiring underwriters is strong preparation evidence, but does not guarantee completion or largest-IPO ranking.",
    ),
    _case(
        case_id="stress_es_stripe_s1_vs_ipo_005",
        thesis="Stripe has submitted a draft S-1 registration to the SEC for confidential review.",
        market_id="synth_stripe_ipo_2026",
        market_title="Will Stripe complete an IPO in 2026?",
        resolution_rules=(
            "Resolves Yes if Stripe common shares begin trading on a public exchange "
            "before December 31, 2026. Resolution uses the official exchange listing."
        ),
        entity_tags=["Stripe", "IPO", "SEC"],
        expected_fit_class="weak_proxy",
        mismatch_family="event_stage_mismatch",
        trap_description="Draft S-1 filing is an early step. Many companies file and withdraw. Filing is not completion.",
    ),
    _case(
        case_id="stress_es_databricks_pricing_vs_cap_006",
        thesis="Databricks is expected to price its IPO at $40-$45 per share next week.",
        market_id="synth_databricks_ipo_cap_100b",
        market_title="Databricks IPO closing market cap above $100B?",
        resolution_rules=(
            "Resolves Yes if Databricks completes an IPO and the closing price on its "
            "first trading day implies a market cap above $100 billion."
        ),
        entity_tags=["Databricks", "IPO", "market cap"],
        expected_fit_class="indirect",
        mismatch_family="event_stage_mismatch",
        trap_description="Pricing range is strong evidence but the market resolves on a specific cap threshold, not the pricing event.",
    ),
    _case(
        case_id="stress_es_openai_board_vs_ipo_007",
        thesis="OpenAI's board has approved proceeding with an IPO but no timeline has been set.",
        market_id="synth_openai_ipo_by_dec_2026",
        market_title="Will OpenAI complete its IPO by December 31, 2026?",
        resolution_rules=(
            "Resolves Yes if OpenAI common shares begin trading on a public exchange "
            "on or before December 31, 2026."
        ),
        entity_tags=["OpenAI", "IPO"],
        expected_fit_class="weak_proxy",
        mismatch_family="event_stage_mismatch",
        trap_description="Board approval without timeline is too early-stage to treat as evidence for a dated IPO completion market.",
    ),
    _case(
        case_id="stress_es_anthropic_ipo_rumor_vs_no_ipo_008",
        thesis="Anthropic executives have privately told investors they plan to IPO within 18 months.",
        market_id="synth_anthropic_no_ipo_june_2026",
        market_title="No Anthropic IPO by June 30, 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic does not complete an IPO on or before June 30, "
            "2026. Resolves No if an IPO occurs before the deadline."
        ),
        entity_tags=["Anthropic", "IPO"],
        expected_fit_class="no_clean_expression",
        mismatch_family="event_stage_mismatch",
        trap_description="18-month plan extends well beyond June 2026. The market's horizon does not match the thesis timeline.",
    ),
]


# ---------------------------------------------------------------------------
# Family 2: Metric mismatch (6 cases)
# ---------------------------------------------------------------------------

METRIC_MISMATCH = [
    _case(
        case_id="stress_mm_anthropic_revenue_vs_valuation_001",
        thesis="Anthropic's annualized revenue run rate just passed $30 billion, tripling in 6 months.",
        market_id="synth_anthropic_500b_val_mm",
        market_title="Anthropic $500B+ valuation in 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic achieves a public or private valuation of at "
            "least $500 billion by December 31, 2026."
        ),
        entity_tags=["Anthropic", "valuation"],
        expected_fit_class="indirect",
        mismatch_family="metric_mismatch",
        trap_description="Revenue growth is strong evidence for valuation, but revenue ≠ valuation. Different metric.",
    ),
    _case(
        case_id="stress_mm_google_tpu_throughput_vs_ranking_002",
        thesis="Google's new TPU v8 delivers 4x inference throughput per watt compared to TPU v6.",
        market_id="synth_google_best_model_june",
        market_title="Will Google have the best AI model by end of June 2026?",
        resolution_rules=(
            "Resolves Yes if a Google-branded model holds the #1 position on the "
            "Chatbot Arena leaderboard on June 30, 2026."
        ),
        entity_tags=["Google", "AI model", "leaderboard"],
        expected_fit_class="weak_proxy",
        mismatch_family="metric_mismatch",
        trap_description="Hardware throughput does not determine model ranking. Leaderboard can change for unrelated reasons.",
    ),
    _case(
        case_id="stress_mm_openai_gpqa_vs_release_003",
        thesis="OpenAI's internal GPQA Diamond score for GPT-5.6 has plateaued at 78%, below Claude 4.5's 83%.",
        market_id="synth_gpt56_release_june",
        market_title="Will GPT-5.6 be publicly released by June 30, 2026?",
        resolution_rules=(
            "Resolves Yes if OpenAI publicly releases a model branded GPT-5.6 "
            "on or before June 30, 2026."
        ),
        entity_tags=["OpenAI", "GPT-5.6"],
        expected_fit_class="no_clean_expression",
        mismatch_family="metric_mismatch",
        trap_description="Benchmark score plateau has no bearing on release timing. Completely different metric.",
    ),
    _case(
        case_id="stress_mm_meta_users_vs_revenue_004",
        thesis="Meta AI assistant now has 800 million monthly active users across Instagram and WhatsApp.",
        market_id="synth_meta_ai_revenue_10b",
        market_title="Will Meta AI generate $10B+ revenue in 2026?",
        resolution_rules=(
            "Resolves Yes if Meta reports or credible sources confirm that Meta AI "
            "products generated at least $10 billion in revenue during 2026."
        ),
        entity_tags=["Meta", "AI", "revenue"],
        expected_fit_class="indirect",
        mismatch_family="metric_mismatch",
        trap_description="User count is evidence for revenue potential, but users ≠ revenue. Monetization is uncertain.",
    ),
    _case(
        case_id="stress_mm_nvidia_margin_vs_share_price_005",
        thesis="Nvidia's gross margin expanded to 78% in Q2 2026, the highest in semiconductor history.",
        market_id="synth_nvidia_share_2000",
        market_title="Will Nvidia share price exceed $2000 by end of 2026?",
        resolution_rules=(
            "Resolves Yes if Nvidia (NVDA) closing share price on any trading day "
            "in 2026 exceeds $2000."
        ),
        entity_tags=["Nvidia", "share price"],
        expected_fit_class="weak_proxy",
        mismatch_family="metric_mismatch",
        trap_description="Margin expansion is one factor in share price, but share price depends on many other factors.",
    ),
    _case(
        case_id="stress_mm_anthropic_headcount_vs_valuation_006",
        thesis="Anthropic doubled its research headcount to 2,400 employees in Q1 2026.",
        market_id="synth_anthropic_500b_val_mm2",
        market_title="Anthropic $500B+ valuation in 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic achieves a public or private valuation of at "
            "least $500 billion by December 31, 2026."
        ),
        entity_tags=["Anthropic", "valuation"],
        expected_fit_class="no_clean_expression",
        mismatch_family="metric_mismatch",
        trap_description="Headcount growth does not resolve valuation. Many companies grow headcount without reaching valuation thresholds.",
    ),
]


# ---------------------------------------------------------------------------
# Family 3: Horizon mismatch (5 cases)
# ---------------------------------------------------------------------------

HORIZON_MISMATCH = [
    _case(
        case_id="stress_hm_fed_2028_vs_2026_cuts_001",
        thesis="The Fed is not expected to cut interest rates until at least 2028 according to the latest dot plot.",
        market_id="synth_fed_cuts_2026_count",
        market_title="How many Fed rate cuts in 2026?",
        resolution_rules=(
            "Resolves to the number of 25bp-equivalent rate cuts the Federal Reserve "
            "makes during calendar year 2026."
        ),
        entity_tags=["Federal Reserve", "rates", "2026"],
        expected_fit_class="indirect",
        mismatch_family="horizon_mismatch",
        trap_description="Same institution, same action, but the thesis is about 2028. The 2026 market tests only part of the claim.",
    ),
    _case(
        case_id="stress_hm_av_2030_vs_waymo_2026_002",
        thesis="Autonomous vehicles will handle 30% of last-mile deliveries in major US cities by 2030.",
        market_id="synth_waymo_10_cities_2026",
        market_title="Will Waymo expand to 10+ US cities by end of 2026?",
        resolution_rules=(
            "Resolves Yes if Waymo operates a commercial autonomous ride-hail service "
            "in at least 10 distinct US cities on or before December 31, 2026."
        ),
        entity_tags=["Waymo", "autonomous vehicles"],
        expected_fit_class="weak_proxy",
        mismatch_family="horizon_mismatch",
        trap_description="Same domain, but 2030 vs 2026 and delivery percentage vs city count. Double mismatch.",
    ),
    _case(
        case_id="stress_hm_climate_2050_vs_carbon_2026_003",
        thesis="Global carbon emissions will need to drop 50% by 2050 to meet Paris Agreement targets.",
        market_id="synth_us_carbon_tax_2026",
        market_title="Will the US implement a federal carbon tax by end of 2026?",
        resolution_rules=(
            "Resolves Yes if the US Congress passes and the President signs a law "
            "establishing a federal carbon tax on or before December 31, 2026."
        ),
        entity_tags=["carbon", "climate", "US policy"],
        expected_fit_class="no_clean_expression",
        mismatch_family="horizon_mismatch",
        trap_description="2050 emissions target vs 2026 policy action. Extreme horizon mismatch plus different metric.",
    ),
    _case(
        case_id="stress_hm_openai_q4_release_vs_june_market_004",
        thesis="OpenAI plans to release GPT-6 in Q4 2026 according to leaked internal roadmaps.",
        market_id="synth_gpt56_release_june_hm",
        market_title="Will GPT-5.6 be publicly released by June 30, 2026?",
        resolution_rules=("Resolves Yes if OpenAI publicly releases GPT-5.6 by June 30, 2026."),
        entity_tags=["OpenAI", "GPT-5.6", "GPT-6"],
        expected_fit_class="weak_proxy",
        mismatch_family="horizon_mismatch",
        trap_description="Different model version (GPT-6 vs GPT-5.6) and different horizon (Q4 vs June). Double mismatch.",
    ),
    _case(
        case_id="stress_hm_fusion_2035_vs_2026_005",
        thesis="Commercial fusion power will be grid-connected within 10 years, possibly by 2035.",
        market_id="synth_fusion_demo_2026",
        market_title="Will a fusion reactor demonstrate net energy gain in 2026?",
        resolution_rules=(
            "Resolves Yes if any fusion experiment demonstrates Q>1 net energy gain "
            "during calendar year 2026, confirmed by peer-reviewed publication or "
            "official agency announcement."
        ),
        entity_tags=["fusion", "energy"],
        expected_fit_class="indirect",
        mismatch_family="horizon_mismatch",
        trap_description="Net energy demo is an early milestone on the path to commercial grid connection, but 2035 vs 2026.",
    ),
]


# ---------------------------------------------------------------------------
# Family 4: Entity mismatch (5 cases)
# ---------------------------------------------------------------------------

ENTITY_MISMATCH = [
    _case(
        case_id="stress_em_claude_48_vs_claude_5_001",
        thesis="Claude 4.8 Opus is now available in Google Vertex AI and showing strong benchmark results.",
        market_id="synth_claude_5_release",
        market_title="Will Claude 5 be publicly released by September 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic publicly releases a model branded Claude 5 "
            "on or before September 30, 2026."
        ),
        entity_tags=["Anthropic", "Claude 5"],
        expected_fit_class="indirect",
        mismatch_family="entity_mismatch",
        trap_description="Same product family but different version. Claude 4.8 availability does not resolve Claude 5 release.",
    ),
    _case(
        case_id="stress_em_amd_mi450_vs_nvidia_002",
        thesis="AMD's MI450X AI accelerator is shipping to hyperscale customers ahead of schedule.",
        market_id="synth_nvidia_share_2000_em",
        market_title="Will Nvidia share price exceed $2000 by end of 2026?",
        resolution_rules=(
            "Resolves Yes if Nvidia (NVDA) closing share price on any trading day "
            "in 2026 exceeds $2000."
        ),
        entity_tags=["Nvidia", "share price"],
        expected_fit_class="no_clean_expression",
        mismatch_family="entity_mismatch",
        trap_description="Both are AI chip companies, but AMD shipping does not resolve Nvidia's share price.",
    ),
    _case(
        case_id="stress_em_gemini_35_vs_32_003",
        thesis="Google quietly released Gemini 3.5 Pro to enterprise API customers last week.",
        market_id="synth_gemini_32_june",
        market_title="Will Gemini 3.2 be released by June 30, 2026?",
        resolution_rules=(
            "Resolves Yes if Google publicly releases a model branded Gemini 3.2 "
            "on or before June 30, 2026."
        ),
        entity_tags=["Google", "Gemini 3.2"],
        expected_fit_class="indirect",
        mismatch_family="entity_mismatch",
        trap_description="Same product family but different version. Gemini 3.5 release does not resolve Gemini 3.2 market.",
    ),
    _case(
        case_id="stress_em_meta_llama_vs_google_model_004",
        thesis="Meta's Llama 4 is now the top-ranked open-source model on every major benchmark.",
        market_id="synth_google_best_model_em",
        market_title="Will Google have the best AI model by end of June 2026?",
        resolution_rules=(
            "Resolves Yes if a Google-branded model holds the #1 position on the "
            "Chatbot Arena leaderboard on June 30, 2026."
        ),
        entity_tags=["Google", "AI model", "leaderboard"],
        expected_fit_class="no_clean_expression",
        mismatch_family="entity_mismatch",
        trap_description="Both about AI model rankings, but Meta open-source vs Google overall Chatbot Arena. Different entity entirely.",
    ),
    _case(
        case_id="stress_em_microsoft_copilot_vs_openai_005",
        thesis="Microsoft Copilot enterprise adoption has reached 60% of Fortune 500 companies.",
        market_id="synth_openai_revenue_20b",
        market_title="Will OpenAI reach $20B annual revenue in 2026?",
        resolution_rules=(
            "Resolves Yes if OpenAI reports or credible sources confirm at least "
            "$20 billion in annualized revenue during 2026."
        ),
        entity_tags=["OpenAI", "revenue"],
        expected_fit_class="weak_proxy",
        mismatch_family="entity_mismatch",
        trap_description="Microsoft Copilot uses OpenAI models, so adoption may help OpenAI revenue, but it's a different entity and indirect causation.",
    ),
]


# ---------------------------------------------------------------------------
# Family 5: Causal mechanism mismatch (6 cases)
# ---------------------------------------------------------------------------

CAUSAL_MECHANISM = [
    _case(
        case_id="stress_cm_tpu_progress_vs_leaderboard_001",
        thesis="Google's TPU v8 infrastructure means Gemini can train 3x faster, closing the frontier model gap.",
        market_id="synth_gemini_arena_2026",
        market_title="Will Gemini hold the #1 Chatbot Arena spot on Dec 31, 2026?",
        resolution_rules=(
            "Resolves Yes if a Gemini-branded model is ranked first on the public "
            "Chatbot Arena leaderboard at market close on December 31, 2026."
        ),
        entity_tags=["Google", "Gemini", "leaderboard"],
        expected_fit_class="weak_proxy",
        mismatch_family="causal_mechanism",
        trap_description="The thesis is about TPU-caused model improvement. The market resolves on leaderboard rank, which can move for many unrelated reasons.",
    ),
    _case(
        case_id="stress_cm_vc_funding_vs_capex_002",
        thesis="AI startups received 80% of all global VC funding in Q1 2026, but measurable ROI remains limited.",
        market_id="synth_amazon_capex_100b",
        market_title="Will Amazon 2026 capital expenditure exceed $100B?",
        resolution_rules=(
            "Resolves Yes if Amazon reports total capital expenditure (purchases of "
            "property and equipment) exceeding $100 billion for fiscal year 2026."
        ),
        entity_tags=["Amazon", "capex"],
        expected_fit_class="weak_proxy",
        mismatch_family="causal_mechanism",
        trap_description="VC funding share and ROI concerns are about the entire AI ecosystem, not one company's capex.",
    ),
    _case(
        case_id="stress_cm_ai_safety_regulation_vs_release_003",
        thesis="The EU AI Act's enforcement will slow frontier model releases by requiring pre-deployment safety audits.",
        market_id="synth_gpt56_release_june_cm",
        market_title="Will GPT-5.6 be publicly released by June 30, 2026?",
        resolution_rules=("Resolves Yes if OpenAI publicly releases GPT-5.6 by June 30, 2026."),
        entity_tags=["OpenAI", "GPT-5.6"],
        expected_fit_class="weak_proxy",
        mismatch_family="causal_mechanism",
        trap_description="Regulatory delay thesis vs specific model release timing. The causal chain (EU regulation → OpenAI delay) is too speculative.",
    ),
    _case(
        case_id="stress_cm_chip_export_ban_vs_model_quality_004",
        thesis="US chip export restrictions to China will prevent Chinese AI labs from training frontier-scale models.",
        market_id="synth_google_best_model_cm",
        market_title="Will Google have the best AI model by end of June 2026?",
        resolution_rules=(
            "Resolves Yes if a Google-branded model holds the #1 Chatbot Arena "
            "position on June 30, 2026."
        ),
        entity_tags=["Google", "AI model", "leaderboard"],
        expected_fit_class="no_clean_expression",
        mismatch_family="causal_mechanism",
        trap_description="The thesis is about China's model capability, not Google's ranking. Completely different causal mechanism.",
    ),
    _case(
        case_id="stress_cm_interest_rates_vs_housing_005",
        thesis="Lower interest rates will revive the US housing market and push prices up 15% by 2028.",
        market_id="synth_mortgage_rate_55",
        market_title="Will the 30-year mortgage rate hit 5.5% in 2026?",
        resolution_rules=(
            "Resolves Yes if the Freddie Mac Primary Mortgage Market Survey 30-year "
            "fixed rate reaches or drops below 5.5% at any point during 2026."
        ),
        entity_tags=["mortgage", "rates", "housing"],
        expected_fit_class="weak_proxy",
        mismatch_family="causal_mechanism",
        trap_description="Mortgage rate is an input to the housing thesis, not the output. Rate level does not resolve price appreciation.",
    ),
    _case(
        case_id="stress_cm_energy_cost_vs_ai_scaling_006",
        thesis="Declining energy costs will make training 100T-parameter models economically viable by 2027.",
        market_id="synth_google_best_model_cm2",
        market_title="Will Google have the best AI model by end of June 2026?",
        resolution_rules=(
            "Resolves Yes if a Google-branded model holds the #1 Chatbot Arena "
            "position on June 30, 2026."
        ),
        entity_tags=["Google", "AI model"],
        expected_fit_class="no_clean_expression",
        mismatch_family="causal_mechanism",
        trap_description="Energy cost thesis is about economics of future model scale, not current leaderboard rankings.",
    ),
]


# ---------------------------------------------------------------------------
# Family 6: Composite thesis (5 cases)
# ---------------------------------------------------------------------------

COMPOSITE_THESIS = [
    _case(
        case_id="stress_ct_iran_ceasefire_package_001",
        thesis=(
            "The US and Iran will extend the ceasefire for 60 more days, partially reopen "
            "the Strait of Hormuz, begin unfreezing assets, and ease some sanctions."
        ),
        market_id="synth_hormuz_blockade_lifted",
        market_title="Will the Strait of Hormuz blockade be officially lifted by June 2026?",
        resolution_rules=(
            "Resolves Yes if the Iranian government or an international body officially "
            "announces the lifting of the Strait of Hormuz blockade on or before "
            "June 30, 2026."
        ),
        entity_tags=["Iran", "Hormuz", "blockade"],
        expected_fit_class="weak_proxy",
        mismatch_family="composite_thesis",
        trap_description="The market resolves only one component (Hormuz) of a four-part package (ceasefire + Hormuz + assets + sanctions).",
    ),
    _case(
        case_id="stress_ct_ai_coding_bar_002",
        thesis="AI systems will replace 40% of entry-level coding jobs AND pass the bar exam with a top-10% score by 2027.",
        market_id="synth_ai_bar_exam_2026",
        market_title="Will an AI system score in the top 10% on the bar exam in 2026?",
        resolution_rules=(
            "Resolves Yes if an AI system achieves a score at or above the 90th "
            "percentile on a US state bar exam during 2026."
        ),
        entity_tags=["AI", "bar exam"],
        expected_fit_class="indirect",
        mismatch_family="composite_thesis",
        trap_description="The market resolves only the bar exam half. The coding jobs half is unaddressed. Partial coverage of a compound thesis.",
    ),
    _case(
        case_id="stress_ct_green_energy_storage_003",
        thesis="Solar will become the cheapest energy source globally AND grid-scale battery storage costs will drop below $50/kWh by 2028.",
        market_id="synth_solar_cheapest_2026",
        market_title="Will solar be the cheapest new electricity source globally in 2026?",
        resolution_rules=(
            "Resolves Yes if the IEA or IRENA reports that utility-scale solar PV has "
            "the lowest LCOE among new electricity sources globally during 2026."
        ),
        entity_tags=["solar", "energy", "LCOE"],
        expected_fit_class="weak_proxy",
        mismatch_family="composite_thesis",
        trap_description="Only resolves the solar cost half. The battery storage cost threshold is a separate material condition.",
    ),
    _case(
        case_id="stress_ct_crypto_etf_regulation_004",
        thesis="The SEC will approve a Solana spot ETF AND implement comprehensive crypto custody rules by end of 2026.",
        market_id="synth_solana_etf_2026",
        market_title="Will a Solana spot ETF be approved by end of 2026?",
        resolution_rules=(
            "Resolves Yes if the SEC approves at least one spot Solana ETF for trading "
            "on a US exchange on or before December 31, 2026."
        ),
        entity_tags=["Solana", "ETF", "SEC"],
        expected_fit_class="indirect",
        mismatch_family="composite_thesis",
        trap_description="ETF approval is the central claim, but custody rules are a material second condition that the market does not resolve.",
    ),
    _case(
        case_id="stress_ct_us_china_ai_trade_005",
        thesis="The US will restrict AI model exports to China AND China will retaliate by banning rare earth exports to the US.",
        market_id="synth_us_china_ai_export_ban",
        market_title="Will the US ban AI model exports to China in 2026?",
        resolution_rules=(
            "Resolves Yes if the US government issues an executive order or legislation "
            "prohibiting the export of frontier AI models to China during 2026."
        ),
        entity_tags=["US", "China", "AI", "export ban"],
        expected_fit_class="no_clean_expression",
        mismatch_family="composite_thesis",
        trap_description="Market resolves only the US action. The thesis requires both US restriction AND Chinese retaliation. Neither alone is the full claim.",
    ),
]


# ---------------------------------------------------------------------------
# Family 7: Inverse framing (5 cases)
# ---------------------------------------------------------------------------

INVERSE_FRAMING = [
    _case(
        case_id="stress_if_anthropic_ipo_momentum_vs_no_ipo_001",
        thesis="Anthropic's valuation is exploding past $1T — this feels like IPO momentum and an IPO is coming soon.",
        market_id="synth_anthropic_no_ipo_june",
        market_title="No Anthropic IPO by June 30, 2026?",
        resolution_rules=(
            "Resolves Yes if Anthropic does not complete an IPO on or before June 30, "
            "2026. Resolves No if an IPO occurs."
        ),
        entity_tags=["Anthropic", "IPO"],
        expected_fit_class="weak_proxy",
        mismatch_family="inverse_framing",
        trap_description="The market is framed as the ABSENCE of the event. Valuation momentum does not directly resolve IPO timing.",
    ),
    _case(
        case_id="stress_if_housing_crash_vs_price_up_002",
        thesis="US housing prices are 40% overpriced and a major correction is inevitable within 2 years.",
        market_id="synth_home_prices_up_5",
        market_title="Will US home prices increase 5%+ YoY in 2026?",
        resolution_rules=(
            "Resolves Yes if the S&P Case-Shiller US National Home Price Index "
            "shows a year-over-year increase of at least 5% for any month in 2026."
        ),
        entity_tags=["housing", "home prices"],
        expected_fit_class="indirect",
        mismatch_family="inverse_framing",
        trap_description="Bearish thesis vs bullish market framing. The No outcome would support the thesis, but the market doesn't directly resolve overpricing.",
    ),
    _case(
        case_id="stress_if_fed_hold_vs_cut_003",
        thesis="The Fed will hold rates steady through all of 2026 due to persistent inflation.",
        market_id="synth_fed_cut_july_2026",
        market_title="Will the Fed cut rates at the July 2026 FOMC meeting?",
        resolution_rules=(
            "Resolves Yes if the Federal Reserve lowers the target federal funds rate "
            "range at the July 2026 FOMC meeting."
        ),
        entity_tags=["Federal Reserve", "rates", "FOMC"],
        expected_fit_class="indirect",
        mismatch_family="inverse_framing",
        trap_description="The thesis says NO cuts. The market asks about a specific cut. The No outcome supports the thesis but the framing is inverted.",
    ),
    _case(
        case_id="stress_if_ai_winter_vs_model_release_004",
        thesis="We are entering an AI winter — investment will dry up and no major new model will launch in H2 2026.",
        market_id="synth_gpt56_release_june_if",
        market_title="Will GPT-5.6 be publicly released by June 30, 2026?",
        resolution_rules=("Resolves Yes if OpenAI publicly releases GPT-5.6 by June 30, 2026."),
        entity_tags=["OpenAI", "GPT-5.6"],
        expected_fit_class="weak_proxy",
        mismatch_family="inverse_framing",
        trap_description="The thesis is about H2 2026 AI winter. The market resolves in June (H1). Even a Yes resolution doesn't address the H2 claim.",
    ),
    _case(
        case_id="stress_if_dollar_weakening_vs_rate_cut_005",
        thesis="The US dollar will lose its safe-haven status as expanded swap lines reduce global funding stress.",
        market_id="synth_fed_cut_sept_2026",
        market_title="Will the Fed cut rates by September 2026?",
        resolution_rules=(
            "Resolves Yes if the Federal Reserve lowers the target federal funds rate "
            "range on or before the September 2026 FOMC meeting."
        ),
        entity_tags=["Federal Reserve", "rates", "USD"],
        expected_fit_class="weak_proxy",
        mismatch_family="inverse_framing",
        trap_description="Dollar safe-haven thesis is about structural reserve currency role. A Fed rate cut is tangentially related but does not resolve swap line or safe-haven dynamics.",
    ),
]


# ---------------------------------------------------------------------------
# Build and write
# ---------------------------------------------------------------------------

ALL_CASES = (
    EVENT_STAGE
    + METRIC_MISMATCH
    + HORIZON_MISMATCH
    + ENTITY_MISMATCH
    + CAUSAL_MECHANISM
    + COMPOSITE_THESIS
    + INVERSE_FRAMING
)


def build_stress_dataset() -> list[dict]:
    """Return all 40 stress cases as a list of dicts."""
    assert len(ALL_CASES) == 40, f"Expected 40 cases, got {len(ALL_CASES)}"
    ids = [c["case_id"] for c in ALL_CASES]
    assert len(ids) == len(set(ids)), "Duplicate case_id found"
    return ALL_CASES


def main() -> int:
    cases = build_stress_dataset()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, sort_keys=True) + "\n")
    print(f"Wrote {len(cases)} stress cases to {OUTPUT_FILE}")

    by_family: dict[str, int] = {}
    by_class: dict[str, int] = {}
    for case in cases:
        family = case["mismatch_family"]
        fit = case["expected_fit_class"]
        by_family[family] = by_family.get(family, 0) + 1
        by_class[fit] = by_class.get(fit, 0) + 1

    print("\nDistribution by family:")
    for family, count in sorted(by_family.items()):
        print(f"  {family}: {count}")
    print("\nDistribution by expected class:")
    for cls, count in sorted(by_class.items()):
        print(f"  {cls}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
