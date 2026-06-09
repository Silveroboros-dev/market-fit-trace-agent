import json
from pathlib import Path

from scripts.build_policy_review_batch import build_policy_review_batch


def test_build_policy_review_batch_groups_candidates_without_mutating_goldens(tmp_path):
    input_dir = tmp_path / "failure_candidates"
    out_dir = tmp_path / "policy_review_batches"
    _write_candidate(
        input_dir / "2026-06-08" / "stress-a",
        case_id="stress_es_openai",
        family="event_stage_mismatch",
        expected="no_clean_expression",
        gemini="indirect",
        deterministic="indirect",
        deterministic_match=False,
    )
    _write_candidate(
        input_dir / "2026-06-08" / "stress-b",
        case_id="stress_hm_fed",
        family="horizon_mismatch",
        expected="indirect",
        gemini="weak_proxy",
        deterministic="indirect",
        deterministic_match=True,
    )

    result = build_policy_review_batch(
        input_dir=input_dir,
        out_dir=out_dir,
        date="2026-06-08",
    )

    summary_path = Path(result["summary_path"])
    review_path = Path(result["policy_review_path"])
    assert result["status"] == "ok"
    assert result["candidate_count"] == 2
    assert result["family_count"] == 2
    assert result["writes_strict_expected_labels"] is False
    assert result["writes_policy_code"] is False
    assert summary_path.exists()
    assert review_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 2
    assert summary["families"]["event_stage_mismatch"]["candidate_count"] == 1
    assert summary["families"]["horizon_mismatch"]["candidate_count"] == 1
    assert summary["families"]["event_stage_mismatch"][
        "deterministic_mismatch_count"
    ] == 1
    assert summary["mutation_risk_case_ids"] == []
    assert summary["missing_disregard_case_ids"] == []

    markdown = review_path.read_text(encoding="utf-8")
    assert "Policy Review Batch" in markdown
    assert "`event_stage_mismatch`" in markdown
    assert "`horizon_mismatch`" in markdown
    assert "No policy code, strict expected labels, or golden fixtures were mutated" in (
        markdown
    )
    assert "expected_outputs.jsonl" not in {
        path.name for path in tmp_path.rglob("*")
    }


def test_build_policy_review_batch_uses_latest_candidate_date(tmp_path):
    input_dir = tmp_path / "failure_candidates"
    out_dir = tmp_path / "policy_review_batches"
    _write_candidate(
        input_dir / "2026-06-07" / "old",
        case_id="old_case",
        family="metric_mismatch",
    )
    _write_candidate(
        input_dir / "2026-06-08" / "new",
        case_id="new_case",
        family="inverse_framing",
    )

    result = build_policy_review_batch(input_dir=input_dir, out_dir=out_dir)

    assert result["candidate_date"] == "2026-06-08"
    summary = json.loads(Path(result["summary_path"]).read_text(encoding="utf-8"))
    assert set(summary["families"]) == {"inverse_framing"}


def test_build_policy_review_batch_ignores_incomplete_candidate_dirs(tmp_path):
    input_dir = tmp_path / "failure_candidates"
    out_dir = tmp_path / "policy_review_batches"
    complete_dir = input_dir / "2026-06-08" / "complete"
    incomplete_dir = input_dir / "2026-06-08" / "incomplete"
    _write_candidate(complete_dir, case_id="complete_case", family="entity_mismatch")
    incomplete_dir.mkdir(parents=True)
    (incomplete_dir / "failure_signal.json").write_text(
        json.dumps({"case_id": "incomplete_case"}),
        encoding="utf-8",
    )

    result = build_policy_review_batch(
        input_dir=input_dir,
        out_dir=out_dir,
        date="2026-06-08",
    )

    summary = json.loads(Path(result["summary_path"]).read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 1
    assert summary["families"]["entity_mismatch"]["candidate_count"] == 1


def _write_candidate(
    candidate_dir: Path,
    *,
    case_id: str,
    family: str,
    expected: str = "weak_proxy",
    gemini: str = "indirect",
    deterministic: str = "no_clean_expression",
    deterministic_match: bool = False,
) -> None:
    candidate_dir.mkdir(parents=True)
    failure = {
        "schema_version": "stress_gemini_failure_candidate_v0",
        "case_id": case_id,
        "triggered_metrics": ["gemini_advisory_mismatch"],
        "mismatch_family": family,
        "expected_fit_class": expected,
        "observed_gemini_fit_class": gemini,
        "deterministic_fit_class": deterministic,
        "deterministic_match": deterministic_match,
        "candidate_only": True,
        "trap_description": "Related market is not a clean test.",
        "phoenix_trace_url": f"https://phoenix.example/traces/{case_id}",
    }
    proposed = {
        "schema_version": "stress_gemini_failure_candidate_v0",
        "case_id": f"failure-{case_id}",
        "truth_scope": "synthetic_expected_label",
        "canonical_truth": False,
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
        "human_review_options": [
            "promote_to_strict_golden_candidate",
            "needs_more_rules",
            "candidate_only",
            "disregard",
        ],
        "source_text": "Synthetic thesis",
        "market": {"title": "Synthetic market"},
    }
    source = {
        "schema_version": "stress_gemini_failure_candidate_v0",
        "case_id": case_id,
        "source_type": "synthetic_stress_case",
    }
    (candidate_dir / "failure_signal.json").write_text(
        json.dumps(failure, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (candidate_dir / "proposed_eval_case.json").write_text(
        json.dumps(proposed, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (candidate_dir / "source.json").write_text(
        json.dumps(source, indent=2, sort_keys=True),
        encoding="utf-8",
    )
