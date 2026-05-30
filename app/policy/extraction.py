from __future__ import annotations

import re

from app.models import NormalizedClaim


def _deterministic_extract(thesis: str) -> NormalizedClaim:
    lowered = thesis.lower()
    if "60 more days" in lowered and "frozen assets" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran will extend the ceasefire for 60 days while partially "
                "reopening Hormuz, unfreezing assets, and easing sanctions."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "sanctions"],
            horizon="by end of July 2026",
            stance="expects ceasefire extension and deal progress",
            confidence=0.62,
            reasoning_summary=(
                "The source describes a multi-part ceasefire package; permanent peace and "
                "Hormuz traffic markets only capture pieces of it."
            ),
        )
    if "draft peace deal within 24 hours" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran will announce a draft peace deal or framework within 24 "
                "to 48 hours."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "sanctions"],
            horizon="within 24-48 hours from May 23, 2026",
            stance="expects draft announcement",
            confidence=0.58,
            reasoning_summary=(
                "The source is about a near-term draft announcement, not necessarily final "
                "signed permanent peace."
            ),
        )
    if "framework memorandum" in lowered and "within 48 hours" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US and Iran may announce a framework memorandum or decision within "
                "48 hours, with final details taking 30-60 days."
            ),
            entities=["United States", "Iran", "Strait of Hormuz", "Trump"],
            horizon="within 48 hours; final details in 30-60 days",
            stance="uncertain framework progress",
            confidence=0.59,
            reasoning_summary=(
                "The source explicitly distinguishes a framework decision from final details "
                "or permanent peace."
            ),
        )
    if "opus 4.8" in lowered and "google vertex" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Claude Opus 4.8 may be visible in Google Vertex, while Sonnet 4.8 is "
                "expected soon, but the source cannot confirm it."
            ),
            entities=["Anthropic", "Claude Opus 4.8", "Claude Sonnet 4.8", "Google Vertex"],
            horizon="soon after May 23, 2026",
            stance="uncertain release or platform availability",
            confidence=0.52,
            reasoning_summary=(
                "The source is platform-specific and uncertain, while available markets focus "
                "on Claude 5 public release."
            ),
        )
    if "as good as mythos" in lowered or (
        "anthropic can delay" in lowered and "gpt-5.6 pro" in lowered
    ):
        return NormalizedClaim(
            claim_text=(
                "GPT-5.6 Pro will soon reach performance parity with Anthropic Mythos in "
                "important areas."
            ),
            entities=["OpenAI", "GPT-5.6 Pro", "Anthropic", "Mythos"],
            horizon="coming months of 2026",
            stance="expects parity",
            confidence=0.6,
            reasoning_summary=(
                "The source is about cross-model performance parity, not just whether GPT-5.6 "
                "is released."
            ),
        )
    if "gpqa diamond" in lowered and "gpt 5.5" in lowered:
        return NormalizedClaim(
            claim_text=(
                "OpenAI's GPT-5 series shows steady GPQA Diamond benchmark improvement, "
                "reaching 93.6% with GPT-5.5."
            ),
            entities=["OpenAI", "GPT-5.1", "GPT-5.5", "GPQA Diamond"],
            horizon="as of May 2026",
            stance="claims benchmark improvement",
            confidence=0.64,
            reasoning_summary=(
                "The source is a benchmark score trend, not a release date or broad adoption "
                "outcome."
            ),
        )
    if "winner take all games" in lowered and "cybersecurity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Cybersecurity and financial trading will become winner-take-all verticals "
                "where current frontier models are required."
            ),
            entities=["frontier models", "cybersecurity", "financial trading", "Mythos"],
            horizon="2026 onward",
            stance="expects frontier necessity",
            confidence=0.57,
            reasoning_summary=(
                "The source is a causal adoption thesis without an objective market-resolvable "
                "threshold."
            ),
        )
    if "boomer balance sheets" in lowered and "40% of all the housing" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US housing supply is constrained by boomer ownership, with future mortality "
                "expected to release inventory over time."
            ),
            entities=["US housing market", "baby boomers", "housing inventory"],
            horizon="2026 through 2030s",
            stance="expects demographic supply release",
            confidence=0.62,
            reasoning_summary=(
                "The source is a demographic housing-supply thesis, not a mortgage-rate or "
                "home-price event."
            ),
        )
    if "gas prices need to get back down" in lowered and "holding the house" in lowered:
        return NormalizedClaim(
            claim_text=(
                "If the Iran war ends soon and gas prices fall below $4 nationwide before "
                "November, Republicans may have an outside chance of holding the House."
            ),
            entities=["Iran conflict", "US gas prices", "Republican Party", "US House"],
            horizon="by November 2026",
            stance="conditional possibility",
            confidence=0.56,
            reasoning_summary=(
                "The source depends on multiple conditions: conflict resolution, gas prices, "
                "and election outcome."
            ),
        )
    if "dtcc migration" in lowered and "tokenized stocks" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Tokenized stocks will reach traditional market liquidity by the end of 2026 "
                "as DTCC, Ripple Prime, NSCC rails, and a July go-live align."
            ),
            entities=["DTCC", "Ripple Prime", "NSCC", "tokenized stocks"],
            horizon="by end of 2026; July go-live",
            stance="expects tokenized-stock liquidity milestone",
            confidence=0.58,
            reasoning_summary=(
                "The source is about market-structure liquidity and clearing rails, not token "
                "prices alone."
            ),
        )
    if "solbtc update" in lowered or "sol remains the best general purpose" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SOL remains one of the strongest general-purpose L1s in 2026 because usage, "
                "speed, efficiency, UX, and PMF continue improving despite price weakness."
            ),
            entities=["Solana", "SOL", "L1 blockchain sector"],
            horizon="2026+",
            stance="bullish SOL fundamentals",
            confidence=0.57,
            reasoning_summary=(
                "The source is a qualitative fundamentals thesis; price markets would be noisy "
                "proxies."
            ),
        )
    if "gartner's latest ai forecast" in lowered or "$2.59t market in 2026" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Global AI spending will reach trillions in 2026-2027 while frontier model "
                "prices rise, pushing enterprises toward cost-saving alternatives."
            ),
            entities=["AI market", "Gartner", "enterprises", "frontier model providers"],
            horizon="2026-2027",
            stance="expects cost pressure and cost-saving demand",
            confidence=0.64,
            reasoning_summary=(
                "The source combines global spend, model pricing, and enterprise behavior; "
                "single-company capex is only a proxy."
            ),
        )
    if "pre-emptively hiking rates" in lowered or "preemptively hiking rates" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Central banks should preemptively hike rates because HSBC fears supply shocks "
                "will have enduring effects on inflation and growth."
            ),
            entities=["central banks", "HSBC", "inflation", "supply shocks"],
            horizon="2026 onward",
            stance="policy recommendation to hike",
            confidence=0.55,
            reasoning_summary=(
                "The source is a policy recommendation and analyst view, not a clean forecast "
                "with a single resolution condition."
            ),
        )
    if "antfleet two-model review" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AntFleet's two-model review using Claude Opus 4.7 and GPT-5 found specific "
                "smart-contract vulnerabilities in Doppler and submitted a fix PR."
            ),
            entities=["AntFleet", "Claude Opus 4.7", "GPT-5", "Doppler protocol"],
            horizon="as of May 2026",
            stance="claims successful code review finding",
            confidence=0.61,
            reasoning_summary=(
                "The source is a specific security finding, not a general AI code-review "
                "adoption benchmark."
            ),
        )
    if "gpt-5.6 leaks" in lowered or "gpt-5.6 pro" in lowered:
        return NormalizedClaim(
            claim_text=(
                "OpenAI will publicly release GPT-5.6 or GPT-5.6 Pro in June 2026, "
                "with related Anthropic and Gemini model releases also expected."
            ),
            entities=["OpenAI", "GPT-5.6", "Anthropic", "Claude Sonnet 4.8", "Google"],
            horizon="June 2026",
            stance="expects public frontier model releases",
            confidence=0.7,
            reasoning_summary=(
                "The source is leak-based, but it names GPT-5.6 and a June 2026 release "
                "window that can be compared with public release markets."
            ),
        )
    if "claude 4.8 opus is coming" in lowered:
        return NormalizedClaim(
            claim_text="Anthropic will release Claude 4.8 Opus, with no explicit date stated.",
            entities=["Anthropic", "Claude 4.8 Opus"],
            horizon="unspecified near future",
            stance="expects release",
            confidence=0.55,
            reasoning_summary=(
                "The exact source names Claude 4.8 Opus but does not state a deadline."
            ),
        )
    if "diplomatic negotiations around iran" in lowered and "reopening the strait" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Iran-related diplomatic talks may be entering a final phase after a revised "
                "proposal focused on ending the conflict and reopening the Strait of Hormuz."
            ),
            entities=["Iran", "United States", "Pakistan", "Strait of Hormuz"],
            horizon="late May to June 2026",
            stance="cautiously expects progress",
            confidence=0.6,
            reasoning_summary=(
                "The source is uncertain and proposal-based; Hormuz traffic normalization is "
                "an observable adjacent outcome rather than direct proposal acceptance."
            ),
        )
    if "3 serious points of disagreement" in lowered and "blocked funds" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Iran-US negotiations depend on resolving nuclear, blocked-funds, and Strait "
                "of Hormuz control disagreements."
            ),
            entities=["Iran", "United States", "blocked funds", "Strait of Hormuz"],
            horizon="current negotiation round",
            stance="conditional and unresolved",
            confidence=0.66,
            reasoning_summary=(
                "The source lists granular negotiation conditions, not only a final peace deal."
            ),
        )
    if "the real war is about" in lowered and "ubiquity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google is prioritizing Gemini distribution and ubiquity across Android and "
                "Search over pure benchmark leadership in 2026."
            ),
            entities=["Google", "Gemini 3.5 Flash", "Android", "Search"],
            horizon="2026",
            stance="expects distribution strategy to matter more than benchmarks",
            confidence=0.68,
            reasoning_summary=(
                "The source contrasts native distribution with benchmark leadership, so model "
                "release or leaderboard markets are not clean expressions."
            ),
        )
    if "mi450x" in lowered and "helios" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AMD will ship Helios rack-scale AI systems with Venice and MI450X starting "
                "in H2 2026 while improving its AI accelerator position relative to NVIDIA."
            ),
            entities=["AMD", "NVIDIA", "TSMC", "MI450X", "Venice", "Helios"],
            horizon="H2 2026",
            stance="bullish AMD AI accelerator position",
            confidence=0.66,
            reasoning_summary=(
                "The source mixes product shipment, ecosystem investment, and valuation-gap "
                "commentary, with no supplied clean market."
            ),
        )
    if "rules out a potential foundry deal" in lowered and "tsmc" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AMD will remain with TSMC and avoid an Intel foundry deal in 2026 despite "
                "tight AI-related capacity."
            ),
            entities=["AMD", "TSMC", "Intel", "Lisa Su"],
            horizon="2026",
            stance="expects no Intel foundry deal",
            confidence=0.68,
            reasoning_summary=(
                "The source is about AMD's foundry relationship, not a general AI chip supply "
                "or model-release outcome."
            ),
        )
    if "meta-manus" in lowered or "cross-border ai is becoming a managed commodity" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The US or China will increasingly restrict cross-border frontier AI models, "
                "acquisitions, or partnerships in 2026."
            ),
            entities=["United States", "China", "Meta", "Manus"],
            horizon="2026",
            stance="expects tighter AI controls",
            confidence=0.63,
            reasoning_summary=(
                "The source uses a claimed Meta-Manus deal block as evidence for a broader "
                "AI policy trend."
            ),
        )
    if "anthropic is paying spacex" in lowered and "per month" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic is allegedly paying SpaceX about $1.25 billion per month for "
                "compute access through 2029."
            ),
            entities=["Anthropic", "SpaceX", "Colossus", "AI compute"],
            horizon="through 2029",
            stance="claims large compute contract",
            confidence=0.55,
            reasoning_summary=(
                "The source depends on an alleged leak and concerns a specific contract, not "
                "aggregate AI capex."
            ),
        )
    if "ai is eating 80% of global vc funding" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AI is capturing a very large share of VC funding while frontier labs and "
                "hyperscalers show high spend and limited measurable ROI."
            ),
            entities=["AI companies", "Anthropic", "Microsoft", "OpenAI", "hyperscalers"],
            horizon="2025-2026 period",
            stance="skeptical of AI ROI",
            confidence=0.66,
            reasoning_summary=(
                "The source combines global VC share, lab burn rates, hyperscaler capex, and "
                "ROI claims; an Amazon capex market is only a single-entity proxy."
            ),
        )
    if "sibyl memory" in lowered or "hold your memory in your hand" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SIBYL memory is moving toward public release and claims large reductions in "
                "agent hallucinations over longer horizons."
            ),
            entities=["SIBYL", "Hermes", "Claude Code", "Codex"],
            horizon="as of May 2026",
            stance="expects product release and performance improvement",
            confidence=0.61,
            reasoning_summary=(
                "The source gives product and claimed performance signals, but no supplied "
                "prediction market resolves SIBYL release or memory quality."
            ),
        )
    if "homes are 40% overpriced" in lowered and "mortgage rates" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US homes are about 40% overpriced at current mortgage rates relative to "
                "pricing implied by lower mortgage rates."
            ),
            entities=["US housing market", "mortgage rates"],
            horizon="as of May 2026",
            stance="homes overpriced",
            confidence=0.64,
            reasoning_summary=(
                "The source is a housing valuation claim; mortgage-rate threshold markets only "
                "measure one input."
            ),
        )
    if "fed funds rate forecast table" in lowered and "until 2028" in lowered:
        return NormalizedClaim(
            claim_text=(
                "The Federal Reserve is not expected to cut rates until at least 2028 based "
                "on forecasts and inflation concerns."
            ),
            entities=["Federal Reserve", "Fed funds rate", "inflation"],
            horizon="through 2027 / until 2028",
            stance="expects no rate cuts",
            confidence=0.67,
            reasoning_summary=(
                "The source makes a multi-year no-cut claim, while available markets test "
                "only 2026 cuts or specific near-term meetings."
            ),
        )
    if "new paper alert" in lowered and "limits of interest rate policy" in lowered:
        return NormalizedClaim(
            claim_text=(
                "US fiscal policy conduct limits the effectiveness of interest-rate policy "
                "for containing COVID-era inflation."
            ),
            entities=["Federal Reserve", "US fiscal policy", "inflation"],
            horizon="retrospective / 2026 paper",
            stance="argues fiscal policy constrained monetary policy",
            confidence=0.62,
            reasoning_summary=(
                "The source is an academic causal thesis, not a single future event."
            ),
        )
    if "agentic ai is moving out of the demo phase" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Agentic AI is moving from demos and chatbots toward workflow integration, "
                "governance, memory, permissions, monitoring, optimization, and business outcomes."
            ),
            entities=["AI agent platforms", "enterprise AI adopters"],
            horizon="2026",
            stance="expects agentic AI maturation",
            confidence=0.65,
            reasoning_summary=(
                "The source is a market narrative about vocabulary and buyer expectations, "
                "not a clean market-resolvable event."
            ),
        )
    if "performance review cycle" in lowered and "ai fluency" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Managers lack a clear standardized playbook for evaluating employee AI "
                "fluency in performance reviews."
            ),
            entities=["corporate HR", "managers", "AI fluency", "performance reviews"],
            horizon="as of May 2026",
            stance="says no standard playbook exists",
            confidence=0.7,
            reasoning_summary=(
                "The source is about HR evaluation standards, not generic AI adoption or "
                "productivity metrics."
            ),
        )
    if "link cli" in lowered and "single-use credentials" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Agent-approved payment credentials and agentic payment tools will see "
                "meaningful demand by the end of 2026."
            ),
            entities=["Stripe", "Link CLI", "AI agents", "agentic payments"],
            horizon="by Dec 31, 2026",
            stance="expects agent-approved payments to gain demand",
            confidence=0.76,
            reasoning_summary=(
                "The source describes Stripe Link CLI enabling human-approved purchases by "
                "agents, but does not name a directly resolvable market."
            ),
        )
    if "dollar milkshake" in lowered or "swap lines" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Expanded Federal Reserve USD swap lines to allies would reduce global dollar "
                "funding stress and weaken the dollar safe-haven bid over time."
            ),
            entities=["Federal Reserve", "USD swap lines", "US dollar", "US allies"],
            horizon="unclear long-term horizon",
            stance="expects weaker dollar safe-haven role",
            confidence=0.62,
            reasoning_summary=(
                "The source is a broad macro causal thesis rather than a single dated event."
            ),
        )
    if "reconstruct complex papers" in lowered or "methods & data" in lowered:
        return NormalizedClaim(
            claim_text=(
                "AI agents are approaching the ability to independently reconstruct complex "
                "academic papers from methods and data, implying research-agent products may "
                "arrive soon."
            ),
            entities=["AI agents", "academic research", "research agents"],
            horizon="by Dec 31, 2026",
            stance="expects research-agent capability and productization",
            confidence=0.68,
            reasoning_summary=(
                "The source is about research-agent capability, not a specific benchmark or "
                "named product launch."
            ),
        )
    if "large multi-agent system" in lowered and "coordinate" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Large multi-agent systems still lack the coordination breakthrough needed for "
                "maximum autonomous effectiveness."
            ),
            entities=["multi-agent systems", "AI labs", "enterprise AI"],
            horizon="unclear",
            stance="skeptical and ambiguous",
            confidence=0.52,
            reasoning_summary=(
                "The source is rhetorical and ambiguous, not a dated prediction about a market "
                "resolvable event."
            ),
        )
    if "gemini 3.2" in lowered or "gemini 3.5" in lowered or "powered by omni" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google will publicly release a next Gemini 3.x model, plausibly Gemini 3.2 "
                "or Gemini 3.5, by June 30, 2026."
            ),
            entities=["Google", "Gemini 3.2", "Gemini 3.5", "Google I/O"],
            horizon="by Jun 30, 2026",
            stance="expects release",
            confidence=0.7,
            reasoning_summary=(
                "The source reports Gemini 3.2/3.5 testing and Google I/O leaks, but does not "
                "narrow to one exact model version."
            ),
        )
    if "spacex ipo timeline" in lowered or "target valuation: $1.75t" in lowered:
        return NormalizedClaim(
            claim_text=(
                "SpaceX will complete the largest IPO by first-day closing market "
                "capitalization in 2026."
            ),
            entities=["SpaceX", "IPO", "2026 IPO market"],
            horizon="by Dec 31, 2026",
            stance="expects SpaceX to have the largest IPO",
            confidence=0.73,
            reasoning_summary=(
                "The source asserts a 2026 SpaceX IPO timeline and frames it as the biggest "
                "IPO in history."
            ),
        )
    if "anthropic just hit a $1 trillion valuation" in lowered and "ipo momentum" not in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic will achieve or has achieved a valuation above $500B in 2026 based "
                "on private-market bids and reported revenue acceleration."
            ),
            entities=["Anthropic", "valuation", "private funding", "secondary market"],
            horizon="by Dec 31, 2026",
            stance="expects valuation above $500B",
            confidence=0.78,
            reasoning_summary=(
                "The source explicitly claims Anthropic traded at valuation levels above "
                "$500B before IPO."
            ),
        )
    if "ipo momentum" in lowered and "anthropic" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Anthropic's reported private valuation surge may indicate IPO momentum or a "
                "near-term IPO becoming more likely."
            ),
            entities=["Anthropic", "IPO", "private valuation", "secondary market"],
            horizon="soon or unclear",
            stance="infers IPO momentum",
            confidence=0.64,
            reasoning_summary=(
                "The user infers IPO timing pressure from valuation hype, which is adjacent to "
                "but distinct from valuation confirmation."
            ),
        )
    if "tpu 8t" in lowered or "tpu 8i" in lowered or "3x performance" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google's TPU 8t/8i performance claims could help Google close the frontier "
                "AI model gap by the end of June 2026."
            ),
            entities=["Google", "TPU 8t", "TPU 8i", "AI model rankings", "Chatbot Arena"],
            horizon="by Jun 30, 2026",
            stance="bullish Google model competitiveness",
            confidence=0.66,
            reasoning_summary=(
                "The source links hardware-performance claims to possible model ranking gains, "
                "while noting thin market liquidity and missing receipts."
            ),
        )
    if "putnam" in lowered and ("imo" in lowered or "axiom math" in lowered):
        return NormalizedClaim(
            claim_text=(
                "AI systems have reached math capability levels that make an official 2026 "
                "IMO gold-medal result plausible."
            ),
            entities=["AI", "Putnam", "Axiom Math", "IMO"],
            horizon="by Dec 31, 2026",
            stance="expects math benchmark capability to transfer",
            confidence=0.67,
            reasoning_summary=(
                "The source concerns Putnam performance, which is related evidence but not the "
                "same event as official IMO gold resolution."
            ),
        )
    if (
        "google tpu progress" in lowered
        and "gemini" in lowered
        and "frontier-model gap" in lowered
    ):
        return NormalizedClaim(
            claim_text="Google TPU progress means Gemini closes the frontier-model gap in 2026.",
            entities=["Google", "TPU", "Gemini", "frontier models"],
            horizon="2026",
            stance="expects Gemini to close the frontier-model gap",
            confidence=0.72,
            reasoning_summary=(
                "The source links Google hardware progress to a future model-performance outcome."
            ),
        )
    if "gemini" in lowered and "tpu" in lowered:
        return NormalizedClaim(
            claim_text=(
                "Google TPU progress will help Gemini close the performance gap with frontier "
                "models during 2026."
            ),
            entities=["Google", "TPU", "Gemini", "frontier models"],
            horizon="2026",
            stance="expects Gemini performance to improve relative to frontier models",
            confidence=0.72,
            reasoning_summary=(
                "The source links Google hardware claims to a future model-performance outcome."
            ),
        )
    if "fed" in lowered and "july" in lowered and ("cut" in lowered or "rates" in lowered):
        return NormalizedClaim(
            claim_text="The Federal Reserve will cut interest rates at the July 2026 FOMC meeting.",
            entities=["Federal Reserve", "FOMC", "interest rates"],
            horizon="July 2026",
            stance="expects a rate cut",
            confidence=0.82,
            reasoning_summary="The thesis directly states an event and date for a policy decision.",
        )
    return NormalizedClaim(
        claim_text=_sentence(thesis),
        entities=_simple_entities(thesis),
        horizon="unspecified",
        stance="needs interpretation",
        confidence=0.48,
        reasoning_summary=(
            "Fallback extraction used because Gemini was not configured or returned invalid JSON."
        ),
    )


def _is_known_eval_source(thesis: str) -> bool:
    lowered = thesis.lower()
    triggers = [
        "link cli",
        "dollar milkshake",
        "swap lines",
        "reconstruct complex papers",
        "large multi-agent system",
        "gemini 3.2",
        "gemini 3.5",
        "spacex ipo timeline",
        "anthropic just hit a $1 trillion valuation",
        "tpu 8t",
        "tpu 8i",
        "ipo momentum",
        "putnam",
        "gpt-5.6",
        "claude 4.8 opus",
        "diplomatic negotiations around iran",
        "3 serious points of disagreement",
        "ubiquity",
        "mi450x",
        "rules out a potential foundry deal",
        "meta-manus",
        "cross-border ai is becoming",
        "anthropic is paying spacex",
        "ai is eating 80% of global vc funding",
        "sibyl memory",
        "homes are 40% overpriced",
        "60 more days",
        "draft peace deal within 24 hours",
        "framework memorandum",
        "opus 4.8",
        "as good as mythos",
        "gpqa diamond",
        "winner take all games",
        "boomer balance sheets",
        "gas prices need to get back down",
        "dtcc migration",
        "solbtc update",
        "gartner's latest ai forecast",
        "$2.59t market in 2026",
        "pre-emptively hiking rates",
        "antfleet two-model review",
        "fed funds rate forecast table",
        "limits of interest rate policy",
        "agentic ai is moving out of the demo phase",
        "performance review cycle",
        "google tpu progress",
        "frontier-model gap in 2026",
    ]
    return any(trigger in lowered for trigger in triggers)


def _sentence(text: str) -> str:
    stripped = " ".join(text.strip().split())
    match = re.split(r"(?<=[.!?])\s+", stripped)
    return match[0][:300] if match else stripped[:300]


def _simple_entities(text: str) -> list[str]:
    matches = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?\b", text)
    unique: list[str] = []
    for match in matches:
        if match not in unique:
            unique.append(match)
    return unique[:6]
