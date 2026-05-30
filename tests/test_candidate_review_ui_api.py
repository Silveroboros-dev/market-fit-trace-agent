import json

from app.candidate_review import (
    find_candidate_dir,
    load_candidate_review_detail,
    load_candidate_review_summary,
)


def test_candidate_review_summary_reads_export_without_expected_labels(tmp_path):
    export_path = tmp_path / "phoenix_candidate_review_dataset_result.json"
    export_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "mode": "phoenix",
                "dataset_name": "market_fit_candidate_cases",
                "dataset_id": "dataset-1",
                "dataset_version_id": "version-1",
                "dataset_url": "https://phoenix/datasets/dataset-1",
                "strict_expected_labels_present": False,
                "candidate_count": 2,
                "review_status_counts": {"reject": 1, "promote": 1},
                "rows": [
                    {"case_id": "case-reject", "human_review_status": "reject"},
                    {"case_id": "case-promote", "human_review_status": "promote"},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = load_candidate_review_summary(export_path)

    assert summary["dataset_version_id"] == "version-1"
    assert summary["strict_expected_labels_present"] is False
    assert [row["case_id"] for row in summary["rows"]] == [
        "case-promote",
        "case-reject",
    ]
    assert "expected_fit_class" not in summary["rows"][0]
    assert "expected_best_market_id" not in summary["rows"][0]


def test_candidate_review_detail_loads_packet_and_optional_llm_suggestion(tmp_path):
    candidates_dir = tmp_path / "evals" / "retrieval_candidates"
    candidate_dir = candidates_dir / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "source.json",
        {"case_id": "case-1", "source_text": "Composite geopolitical package."},
    )
    _write_json(
        candidate_dir / "retrieval_result.json",
        {"retrieval_id": "retr-1", "market_ids_considered": ["m1"]},
    )
    _write_json(
        candidate_dir / "run_result.json",
        {
            "run_id": "run-1",
            "phoenix_trace_url": "https://phoenix/traces/trace-1",
            "claim": {"claim_text": "Normalized claim"},
            "fit": {"semantic_fit_class": "weak_proxy", "recommended_market_id": "m1"},
        },
    )
    _write_json(
        candidate_dir / "review_decision.json",
        {
            "human_review_status": "promote",
            "reviewer_note": "Promote only as reviewed weak proxy.",
        },
    )
    _write_json(
        candidate_dir / "llm_review_suggestion.json",
        {
            "canonical_truth": False,
            "writes_strict_expected_labels": False,
            "suggested_review_status": "promote",
            "likely_issues": ["weak_proxy_risk"],
        },
    )
    _write_jsonl(candidate_dir / "market_snapshots.jsonl", [{"market_id": "m1"}])
    _write_jsonl(
        candidate_dir / "agent_market_rules_snapshots.jsonl",
        [{"market_id": "m1", "rules_status": "present"}],
    )
    export_path = candidates_dir / "phoenix_candidate_review_dataset_result.json"
    _write_json(
        export_path,
        {
            "status": "ok",
            "mode": "phoenix",
            "dataset_name": "market_fit_candidate_cases",
            "strict_expected_labels_present": False,
            "rows": [{"case_id": "case-1", "human_review_status": "promote"}],
        },
    )

    detail = load_candidate_review_detail("case-1", candidates_dir, export_path)

    assert detail["case_id"] == "case-1"
    assert detail["review_decision"]["human_review_status"] == "promote"
    assert detail["llm_review_suggestion"]["suggested_review_status"] == "promote"
    assert detail["review_rules"] == [{"market_id": "m1", "rules_status": "present"}]
    assert detail["dataset_export"]["strict_expected_labels_present"] is False
    assert "expected_fit_class" not in detail["dataset_export"]["row"]
    assert find_candidate_dir("case-1", candidates_dir) == candidate_dir


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
