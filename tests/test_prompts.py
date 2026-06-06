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
