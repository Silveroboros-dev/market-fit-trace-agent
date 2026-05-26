import json

from scripts.export_candidate_review_dataset import (
    _candidate_dirs,
    _candidate_example,
    _review_status_counts,
    _rules_status_summary,
    _summary,
)
from scripts.review_candidate import build_review_decision, find_candidate_dir


def test_candidate_example_preserves_run_trace_and_review_metadata(tmp_path):
    candidate_dir = tmp_path / "evals" / "retrieval_candidates" / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "source.json",
        {
            "case_id": "case-1",
            "source_text": "A thesis about Hormuz reopening.",
            "source_type": "manual_live_retrieval_candidate",
            "created_at_utc": "2026-05-26T12:00:00+00:00",
        },
    )
    _write_json(
        candidate_dir / "retrieval_result.json",
        {
            "mode": "polydata",
            "snapshot_id": "snapshot-1",
            "as_of_ts": "2026-05-26T00:00:00+00:00",
            "retrieval_id": "retr-1",
            "market_ids_considered": ["m1"],
        },
    )
    _write_jsonl(
        candidate_dir / "market_snapshots.jsonl",
        [{"market_id": "m1", "title": "Market 1"}],
    )
    _write_jsonl(
        candidate_dir / "market_rules_snapshots.jsonl",
        [{"market_id": "m1", "rules_status": "missing"}],
    )
    _write_json(
        candidate_dir / "review_decision.json",
        {
            "case_id": "case-1",
            "candidate_dir": str(candidate_dir),
            "human_review_status": "needs_more_rules",
            "reviewer_note": "Rules missing; composite thesis.",
            "reviewed_at_utc": "2026-05-26T22:55:12+00:00",
            "reviewer": "local_reviewer",
        },
    )
    _write_json(
        candidate_dir / "run_result.json",
        {
            "run_id": "run-1",
            "claim_id": "claim-1",
            "phoenix_trace_id": "trace-1",
            "phoenix_trace_url": "https://phoenix/traces/trace-1",
            "claim": {"claim_text": "Normalized claim"},
            "fit": {
                "semantic_fit_class": "indirect",
                "recommended_market_id": "m1",
                "fit_reason": "Shares entities.",
            },
            "eval": {
                "metrics": {
                    "false_strong_recommendation": False,
                    "weak_proxy_detected": False,
                    "unsupported_implication": False,
                }
            },
            "market_retrieval": {
                "mode": "polydata",
                "snapshot_id": "snapshot-run-1",
                "as_of_ts": "2026-05-26T01:00:00+00:00",
                "retrieval_id": "retr-run-1",
                "market_ids_considered": ["m2"],
            },
        },
    )
    (candidate_dir / "review_notes.md").write_text("Review me", encoding="utf-8")

    example = _candidate_example(candidate_dir)

    assert example["input"]["case_id"] == "case-1"
    assert example["output"]["human_review_status"] == "needs_more_rules"
    assert example["output"]["reviewer_note"] == "Rules missing; composite thesis."
    assert example["output"]["recommended_action"] == "needs_more_rules"
    assert "expected_fit_class" not in example["output"]
    assert "expected_best_market_id" not in example["output"]
    assert example["metadata"]["agent_run_status"] == "run_backed"
    assert example["metadata"]["trace_id"] == "trace-1"
    assert example["metadata"]["phoenix_trace_id"] == "trace-1"
    assert example["metadata"]["retrieval_id"] == "retr-run-1"
    assert example["metadata"]["snapshot_id"] == "snapshot-run-1"
    assert example["metadata"]["retrieved_market_ids"] == ["m2"]
    assert example["metadata"]["agent_market_ids_considered"] == ["m2"]
    assert example["metadata"]["source_retrieval_id"] == "retr-1"
    assert example["metadata"]["source_market_ids_considered"] == ["m1"]
    assert example["metadata"]["reviewed_at_utc"] == "2026-05-26T22:55:12+00:00"
    assert example["metadata"]["reviewer"] == "local_reviewer"
    assert example["metadata"]["review_decision_path"].endswith(
        "review_decision.json"
    )
    assert example["metadata"]["proposed_fit_class"] == "indirect"
    assert example["metadata"]["fit_class_proposed"] == "indirect"
    assert example["metadata"]["rules_status"] == "missing"
    assert example["metadata"]["rules_status_summary"] == {"missing": 1}
    _assert_no_strict_expected_labels(example)


def test_dry_run_summary_keeps_candidates_pending_without_expected_labels():
    example = {
        "input": {
            "case_id": "case-1",
            "source_text": "A thesis about Hormuz reopening.",
        },
        "output": {
            "human_review_status": "pending",
            "reviewer_note": "",
            "recommended_action": "needs_more_rules",
        },
        "metadata": {
            "normalized_claim": {"claim_text": "Normalized claim"},
            "retrieved_market_ids": ["m1", "m2"],
            "agent_run_status": "run_backed",
            "run_id": "run-1",
            "trace_id": "trace-1",
            "retrieval_id": "retr-1",
            "snapshot_id": "snapshot-1",
            "as_of_ts": "2026-05-26T00:00:00+00:00",
            "phoenix_trace_id": "trace-1",
            "proposed_fit_class": "indirect",
            "recommended_market_id": "m1",
            "weak_proxy_detected": False,
            "false_strong_recommendation": False,
            "unsupported_implication": False,
            "rules_status": "missing",
            "rules_status_summary": {"missing": 2},
        },
    }

    summary = _summary(
        dataset=None,
        dataset_name="market_fit_candidate_cases",
        examples=[example],
        dry_run=True,
        missing_config=["PHOENIX_API_KEY"],
    )

    assert summary["status"] == "dry_run"
    assert summary["mode"] == "dry_run"
    assert summary["dataset_name"] == "market_fit_candidate_cases"
    assert summary["dataset_id"] is None
    assert summary["strict_expected_labels_present"] is False
    assert summary["missing_config"] == ["PHOENIX_API_KEY"]
    assert summary["pending_review_count"] == 1
    assert summary["review_status_counts"] == {"pending": 1}
    assert summary["rows"][0]["human_review_status"] == "pending"
    assert summary["rows"][0]["reviewer_note"] == ""
    assert "expected_fit_class" not in summary["rows"][0]
    assert "expected_best_market_id" not in summary["rows"][0]
    _assert_no_strict_expected_labels(example)


def test_candidate_dirs_finds_review_packets(tmp_path):
    candidate_dir = tmp_path / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "source.json").write_text("{}", encoding="utf-8")
    (candidate_dir / "retrieval_result.json").write_text("{}", encoding="utf-8")

    assert _candidate_dirs(tmp_path) == [candidate_dir]


def test_rules_status_summary_counts_statuses():
    assert _rules_status_summary(
        [
            {"rules_status": "missing"},
            {"rules_status": "present"},
            {"rules_status": "missing"},
            {},
        ]
    ) == {"missing": 2, "present": 1, "unknown": 1}


def test_review_status_counts_counts_non_pending_decisions():
    assert _review_status_counts(
        [
            {"human_review_status": "pending"},
            {"human_review_status": "needs_more_rules"},
            {"human_review_status": "candidate_only"},
            {},
        ]
    ) == {"pending": 2, "needs_more_rules": 1, "candidate_only": 1}


def test_review_candidate_finds_latest_packet_and_builds_decision(tmp_path):
    older = tmp_path / "2026-05-25" / "case-1"
    newer = tmp_path / "2026-05-26" / "case-1"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    for path in (older, newer):
        (path / "source.json").write_text("{}", encoding="utf-8")
        (path / "retrieval_result.json").write_text("{}", encoding="utf-8")

    assert find_candidate_dir(tmp_path, "case-1") == newer

    decision = build_review_decision(
        case_id="case-1",
        candidate_dir=newer,
        status="needs_more_rules",
        note="Rules missing; composite thesis.",
        reviewer="local_reviewer",
    )

    assert decision["human_review_status"] == "needs_more_rules"
    assert decision["reviewer_note"] == "Rules missing; composite thesis."
    assert decision["reviewer"] == "local_reviewer"
    assert "reviewed_at_utc" in decision
    assert "expected_fit_class" not in json.dumps(decision)


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
