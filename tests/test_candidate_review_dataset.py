import json

from scripts.export_candidate_review_dataset import (
    _candidate_dirs,
    _candidate_example,
    _rules_status_summary,
)


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
        },
    )
    (candidate_dir / "review_notes.md").write_text("Review me", encoding="utf-8")

    example = _candidate_example(candidate_dir)

    assert example["input"]["case_id"] == "case-1"
    assert example["output"]["human_review_status"] == "pending"
    assert example["output"]["recommended_action"] == "needs_more_rules"
    assert example["metadata"]["agent_run_status"] == "run_backed"
    assert example["metadata"]["phoenix_trace_id"] == "trace-1"
    assert example["metadata"]["fit_class_proposed"] == "indirect"
    assert example["metadata"]["rules_status_summary"] == {"missing": 1}


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


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
