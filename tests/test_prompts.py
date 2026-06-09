from app.models import CandidateMarket, NormalizedClaim
from app.prompts import build_market_fit_prompt


def test_market_fit_prompt_makes_inverse_check_advisory_only():
    prompt = build_market_fit_prompt(
        claim=NormalizedClaim(
            claim_text="The Federal Reserve will hold rates steady through 2026.",
            entities=["Federal Reserve"],
            horizon="2026",
            stance="expects no cut",
        ),
        markets=[
            CandidateMarket(
                market_id="fed-cut-2026",
                title="Will the Fed cut rates by December 2026?",
                venue="Polymarket",
                description="Binary rate-cut market.",
                resolution_rules="Resolves Yes if the Fed cuts rates by December 2026.",
                close_date="2026-12-31",
                outcomes=["Yes", "No"],
            )
        ],
        prompt_version="v1_lenient",
        prior_failure_summary=None,
    )

    assert "advisory_inverse_market_check" in prompt
    assert "review guidance, not a truth label" in prompt
    assert "No outcome could be" in prompt
    assert "Do not use this advisory field to force semantic_fit_class to" in prompt


def test_market_fit_prompt_includes_failure_family_guardrails():
    prompt = build_market_fit_prompt(
        claim=NormalizedClaim(
            claim_text="OpenAI is preparing to file confidentially for an IPO.",
            entities=["OpenAI", "IPO"],
            horizon="2026",
            stance="expects confidential filing preparation",
        ),
        markets=[
            CandidateMarket(
                market_id="openai-ipo-cap",
                title="OpenAI IPO closing market cap above $300B in 2026?",
                venue="SyntheticStress",
                description="IPO valuation market.",
                resolution_rules=(
                    "Resolves Yes if OpenAI completes an IPO and the closing price "
                    "implies a market capitalization above $300 billion."
                ),
                close_date="2026-12-31",
                outcomes=["Yes", "No"],
            )
        ],
        prompt_version="v1_lenient",
        prior_failure_summary=None,
    )

    assert "market-fit checklist" in prompt
    assert "do not turn every mismatch into no_clean_expression" in prompt
    assert "Event stage" in prompt
    assert "Metric" in prompt
    assert "Horizon" in prompt
    assert "Compound coverage" in prompt
    assert "Causal bridge" in prompt
    assert "Outcome polarity" in prompt
    assert "Inverse framing alone must never be direct" in prompt
    assert "Class calibration" in prompt
    assert "IPO-completion market can be indirect evidence" in prompt
    assert "weak_proxy" in prompt
    assert "adjacent evidence that plausibly updates" in prompt
