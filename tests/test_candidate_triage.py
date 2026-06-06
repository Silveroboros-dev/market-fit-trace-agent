import asyncio
import json

from scripts.triage_candidates import triage_candidate_dir


class StaticRuntime:
    runtime_name = "static-test-runtime"

    def __init__(self, payload):
        self.payload = payload

    async def generate_json(self, **_kwargs):
        return self.payload


def test_triage_candidate_accepts_llm_suggestion_without_strict_labels(tmp_path):
    candidate_dir = _candidate_dir(tmp_path)

    suggestion = asyncio.run(
        triage_candidate_dir(
            candidate_dir,
            runtime=StaticRuntime(
                {
                    "review_priority": "high",
                    "suggested_review_status": "candidate_only",
                    "suggested_fit_risk": "likely_weak_proxy",
                    "likely_issues": [
                        "weak_proxy_risk",
                        "compound_thesis",
                        "inverse_market_check",
                    ],
                    "markets_to_inspect": ["m1"],
                    "judge_rationale": (
                        "The market is relevant but incomplete; inspect whether an "
                        "inverse outcome matters."
                    ),
                    "needs_human_check": True,
                    "must_not_promote_without": ["human adjudication"],
                }
            ),
        )
    )

    assert suggestion["candidate_id"] == "case-1"
    assert suggestion["triage_source"] == "google-adk"
    assert suggestion["model"] == "static-test-runtime"
    assert suggestion["suggested_review_status"] == "candidate_only"
    assert suggestion["suggested_fit_risk"] == "likely_weak_proxy"
    assert suggestion["likely_issues"] == [
        "weak_proxy_risk",
        "compound_thesis",
        "inverse_market_check",
    ]
    assert suggestion["markets_to_inspect"] == ["m1"]
    assert suggestion["market_scores"][0]["market_id"] == "m1"
    assert 0 <= suggestion["market_scores"][0]["review_score"] <= 100
    _assert_no_strict_expected_labels(suggestion)


def test_triage_candidate_falls_back_when_llm_outputs_strict_label(tmp_path):
    candidate_dir = _candidate_dir(tmp_path)

    suggestion = asyncio.run(
        triage_candidate_dir(
            candidate_dir,
            runtime=StaticRuntime(
                {
                    "review_priority": "high",
                    "suggested_review_status": "promote",
                    "expected_fit_class": "weak_proxy",
                    "judge_rationale": "Invalid because it writes strict labels.",
                }
            ),
        )
    )

    assert suggestion["triage_source"] == "local_rule_fallback"
    assert suggestion["writes_strict_expected_labels"] is False
    assert "missing_resolution_rules" in suggestion["likely_issues"]
    assert suggestion["market_scores"][0]["market_id"] == "m1"
    assert isinstance(suggestion["market_scores"][0]["review_score"], int)
    _assert_no_strict_expected_labels(suggestion)


def _candidate_dir(tmp_path):
    candidate_dir = tmp_path / "evals" / "retrieval_candidates" / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "source.json",
        {
            "case_id": "case-1",
            "source_text": (
                "The US and Iran will extend a ceasefire and reopen Hormuz while "
                "easing sanctions."
            ),
        },
    )
    _write_json(
        candidate_dir / "retrieval_result.json",
        {
            "retrieval_id": "retr-1",
            "snapshot_id": "snapshot-1",
            "as_of_ts": "2026-05-26T00:00:00+00:00",
            "market_ids_considered": ["m1"],
        },
    )
    _write_jsonl(
        candidate_dir / "market_snapshots.jsonl",
        [
            {
                "market_id": "m1",
                "title": "Will Trump announce the Hormuz blockade is lifted?",
                "description": "A market about one Hormuz announcement.",
                "resolution_rules": "",
                "entity_tags": ["Iran", "Hormuz"],
            }
        ],
    )
    _write_jsonl(
        candidate_dir / "market_rules_snapshots.jsonl",
        [{"market_id": "m1", "rules_status": "missing", "resolution_rules": ""}],
    )
    _write_json(
        candidate_dir / "run_result.json",
        {
            "claim": {"claim_text": "US-Iran ceasefire and Hormuz package."},
            "fit": {
                "semantic_fit_class": "weak_proxy",
                "recommended_market_id": "m1",
                "fit_reason": "One component only.",
                "misses": ["sanctions relief"],
            },
            "eval": {
                "metrics": {
                    "false_strong_recommendation": False,
                    "weak_proxy_detected": True,
                    "unsupported_implication": False,
                }
            },
        },
    )
    return candidate_dir


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _assert_no_strict_expected_labels(payload):
    text = json.dumps(payload)
    assert "expected_fit_class" not in text
    assert "expected_best_market_id" not in text
