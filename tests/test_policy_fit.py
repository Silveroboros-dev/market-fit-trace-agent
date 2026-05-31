from app.models import CandidateMarket, FitClass, MarketPolarity, NormalizedClaim
from app.policy.fit import _deterministic_classify


def test_inverse_binary_market_can_be_direct_with_no_supporting_outcome():
    claim = NormalizedClaim(
        claim_text=(
            "An unusually divided Federal Reserve held its key interest rate steady "
            "as policymakers weighed the H2 2026 policy path."
        ),
        entities=["Federal Reserve", "FOMC"],
        horizon="H2 2026",
        stance="expects hold/no-cut path",
    )
    markets = [
        CandidateMarket(
            market_id="906973",
            title="Will the Fed decrease interest rates by 25 bps after the June 2026 meeting?",
            venue="Polymarket",
            description="One-meeting Fed decrease market.",
            resolution_rules=(
                "This market resolves on the amount of basis points the upper bound "
                "of the target federal funds rate is changed by versus the level it "
                "was prior to the Federal Reserve's June 2026 meeting."
            ),
            close_date="2026-06-17",
            outcomes=["Yes", "No"],
            current_probability=0.01,
            entity_tags=["Fed", "FOMC", "Fed Rates"],
        ),
        CandidateMarket(
            market_id="1439555",
            title="Fed rate cut by December 2026 meeting?",
            venue="Polymarket",
            description="Cut-by-December Fed policy path market.",
            resolution_rules=(
                "This market will resolve to Yes if the upper bound of the target "
                "federal funds rate is decreased at any point between December 16, "
                "2025 and the completion of the FOMC meeting for December 2026. "
                "Otherwise, this market will resolve to No."
            ),
            close_date="2026-06-17",
            outcomes=["Yes", "No"],
            current_probability=0.3,
            entity_tags=["Fed", "FOMC", "Fed Rates"],
        ),
    ]

    fit = _deterministic_classify(claim, markets, "v1_lenient")

    assert fit.semantic_fit_class == FitClass.DIRECT
    assert fit.recommended_market_id == "1439555"
    assert fit.supporting_outcome == "No"
    assert fit.polarity == MarketPolarity.INVERSE
    assert "Reductio ad absurdum" in fit.fit_reason
    assert "906973" in {market.market_id for market in fit.rejected_markets}
