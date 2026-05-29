import json

from scripts.export_candidate_review_dataset import _candidate_example
from scripts.run_phoenix_dataset_experiment import (
    _dataset_example,
    _metric_summary,
    _score_row,
)


def test_promoted_golden_dataset_row_contains_expected_labels():
    case = {
        "example_id": "eval_001",
        "schema_version": "market_fit_v1",
        "as_of_ts": "2026-05-03T16:30:00Z",
        "source_type": "x_post_text",
        "source_text": "A public thesis.",
        "source_provenance": {
            "source_name": "Source",
            "source_url": "https://example.com/post",
        },
        "source_signal": {
            "source_actor": "Analyst",
            "source_actor_type": "commentator",
        },
        "market_snapshot_ref": {
            "build_id": "market_snapshot_1",
            "venue": "polymarket",
        },
        "market_rules_snapshot_ref": {
            "build_id": "market_rules_1",
            "venue": "polymarket",
        },
        "labels": {"topic": "AI", "difficulty": "hard"},
    }
    expected = {
        "example_id": "eval_001",
        "expected_fit": {
            "semantic_fit_class": "indirect",
            "best_market_id": "m1",
            "acceptable_market_ids": ["m2"],
            "adjacent_market_ids": [],
            "case_tags": ["horizon_mismatch"],
            "minimum_expected_behavior": "Classify as indirect.",
        },
    }

    row = _dataset_example(case, expected, "market_fit_v1")

    assert row["output"]["expected_fit_class"] == "indirect"
    assert row["output"]["expected_best_market_id"] == "m1"
    assert row["output"]["acceptable_market_ids"] == ["m2"]
    assert row["metadata"]["strict_eval_truth_source"] == "repo_fixtures"
    assert row["metadata"]["eval_pack"] == "market_fit_v1"


def test_candidate_review_row_does_not_contain_expected_labels(tmp_path):
    candidate_dir = tmp_path / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "source.json",
        {
            "case_id": "case-1",
            "source_text": "A thesis about a live market.",
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
    _write_jsonl(candidate_dir / "market_snapshots.jsonl", [{"market_id": "m1"}])
    _write_jsonl(
        candidate_dir / "market_rules_snapshots.jsonl",
        [{"market_id": "m1", "rules_status": "missing"}],
    )
    (candidate_dir / "review_notes.md").write_text("Pending review", encoding="utf-8")

    row = _candidate_example(candidate_dir)
    serialized = json.dumps(row)

    assert row["output"]["human_review_status"] == "pending"
    assert "expected_fit_class" not in serialized
    assert "expected_best_market_id" not in serialized


def test_experiment_metrics_include_no_clean_false_positive_behavior():
    rows = [
        {
            "case_id": "case-direct",
            "expected_fit_class": "direct",
            "actual_fit_class": "direct",
            "expected_best_market_id": "m1",
            "actual_market_id": "m1",
            "acceptable_market_ids": [],
            "adjacent_market_ids": [],
            "false_strong_recommendation": False,
            "weak_proxy_detected": False,
            "unsupported_implication": False,
        },
        {
            "case_id": "case-no-clean",
            "expected_fit_class": "no_clean_expression",
            "actual_fit_class": "indirect",
            "expected_best_market_id": None,
            "actual_market_id": "m2",
            "acceptable_market_ids": [],
            "adjacent_market_ids": [],
            "false_strong_recommendation": False,
            "weak_proxy_detected": False,
            "unsupported_implication": False,
        },
    ]
    for row in rows:
        _score_row(row)

    metrics = _metric_summary(rows)

    assert metrics["fit_class_accuracy"] == 0.5
    assert metrics["market_id_exact_match_rate"] == 0.5
    assert metrics["acceptable_market_match_rate"] == 0.5
    assert metrics["false_strong_recommendation_rate"] == 0.0
    assert metrics["unsupported_implication_rate"] == 0.0
    assert metrics["no_clean_expression"]["expected_count"] == 1
    assert metrics["no_clean_expression"]["false_positive_count"] == 1
    assert metrics["no_clean_expression"]["false_positive_case_ids"] == [
        "case-no-clean"
    ]


def test_experiment_metrics_name_weak_proxy_case_share_separately():
    rows = [
        {
            "case_id": "case-weak-proxy",
            "expected_fit_class": "weak_proxy",
            "actual_fit_class": "weak_proxy",
            "expected_best_market_id": None,
            "actual_market_id": "m1",
            "acceptable_market_ids": [],
            "adjacent_market_ids": ["m1"],
            "false_strong_recommendation": False,
            "weak_proxy_detected": True,
            "unsupported_implication": False,
        },
        {
            "case_id": "case-direct",
            "expected_fit_class": "direct",
            "actual_fit_class": "direct",
            "expected_best_market_id": "m2",
            "actual_market_id": "m2",
            "acceptable_market_ids": [],
            "adjacent_market_ids": [],
            "false_strong_recommendation": False,
            "weak_proxy_detected": False,
            "unsupported_implication": False,
        },
    ]
    for row in rows:
        _score_row(row)

    metrics = _metric_summary(rows)

    assert "weak_proxy_detected_rate" not in metrics
    assert metrics["weak_proxy_case_count"] == 1
    assert metrics["weak_proxy_case_share"] == 0.5
    assert metrics["weak_proxy_detected_count"] == 1
    assert metrics["weak_proxy_detection_on_weak_proxy_cases"] == {
        "expected_count": 1,
        "detected_count": 1,
        "rate": 1.0,
        "missed_case_ids": [],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
