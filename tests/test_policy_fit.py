import json
from pathlib import Path

from app.models import CandidateMarket, FitClass, NormalizedClaim
from app.policy.extraction import _deterministic_extract
from app.policy.fit import _deterministic_classify

ROOT = Path(__file__).resolve().parents[1]


def test_inverse_binary_market_is_not_deterministic_truth():
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

    assert fit.semantic_fit_class != FitClass.DIRECT
    assert fit.supporting_outcome is None
    assert fit.polarity is None
    assert "Reductio ad absurdum" not in fit.fit_reason


def test_inverse_policy_does_not_upgrade_v1_regression_goldens_to_direct():
    expected_classes = {
        "eval_001": FitClass.NO_CLEAN_EXPRESSION,
        "eval_003": FitClass.NO_CLEAN_EXPRESSION,
        "eval_004": FitClass.NO_CLEAN_EXPRESSION,
        "eval_005": FitClass.INDIRECT,
        "eval_010": FitClass.INDIRECT,
    }
    examples = {
        row["example_id"]: row
        for row in _read_jsonl(ROOT / "evals" / "market_fit_v1" / "examples.jsonl")
    }
    markets = _load_v1_market_rules()

    for example_id, expected_class in expected_classes.items():
        claim = _deterministic_extract(examples[example_id]["source_text"])
        fit = _deterministic_classify(claim, markets, "v1_lenient")

        assert fit.semantic_fit_class == expected_class, example_id
        assert fit.semantic_fit_class != FitClass.DIRECT, example_id


def _load_v1_market_rules() -> list[CandidateMarket]:
    markets: list[CandidateMarket] = []
    for item in _read_jsonl(ROOT / "evals" / "market_fit_v1" / "market_rules_snapshots.jsonl"):
        close_time = item.get("close_time") or item.get("close_date") or ""
        markets.append(
            CandidateMarket(
                market_id=item["market_id"],
                title=item["title"],
                venue=item["venue"],
                description=item["description"],
                resolution_rules=item["resolution_rules"],
                close_date=close_time.split("T")[0] if close_time else "unspecified",
                outcomes=["Yes", "No"],
                current_probability=item.get("yes_price", item.get("current_probability")),
                entity_tags=item.get("tags", item.get("entity_tags", [])),
            )
        )
    return markets


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
