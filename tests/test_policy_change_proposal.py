import json
from pathlib import Path

from scripts.build_policy_change_proposal import build_policy_change_proposal


def test_build_policy_change_proposal_writes_human_review_artifact(tmp_path):
    batch_dir = tmp_path / "policy_review_batches" / "2026-06-08"
    batch_dir.mkdir(parents=True)
    _write_summary(batch_dir / "summary.json")

    result = build_policy_change_proposal(
        input_dir=tmp_path / "policy_review_batches",
        date="2026-06-08",
    )

    proposal_path = Path(result["proposal_path"])
    assert result["status"] == "ok"
    assert result["candidate_count"] == 5
    assert result["family_count"] == 3
    assert result["writes_prompt_code"] is False
    assert result["writes_policy_code"] is False
    assert result["writes_strict_expected_labels"] is False
    assert proposal_path.exists()

    markdown = proposal_path.read_text(encoding="utf-8")
    assert "Policy Change Proposal" in markdown
    assert "Target file for human-approved patch: `app/prompts.py`" in markdown
    assert "`event_stage_alignment_guard`" in markdown
    assert "`compound_claim_coverage_guard`" in markdown
    assert "Positive Signals" in markdown
    assert "`metric_mismatch`" in markdown
    assert "prompt-noise candidates" in markdown
    assert "This proposal does not apply changes" in markdown
    assert "approve_prompt_only_patch" in markdown
    assert "approve_deterministic_guard" in markdown
    assert "expected_outputs.jsonl" not in {path.name for path in tmp_path.rglob("*")}


def test_build_policy_change_proposal_uses_latest_batch_date(tmp_path):
    root = tmp_path / "policy_review_batches"
    old_dir = root / "2026-06-07"
    new_dir = root / "2026-06-08"
    old_dir.mkdir(parents=True)
    new_dir.mkdir(parents=True)
    _write_summary(old_dir / "summary.json", candidate_count=1)
    _write_summary(new_dir / "summary.json", candidate_count=5)

    result = build_policy_change_proposal(input_dir=root)

    assert result["candidate_date"] == "2026-06-08"
    assert result["candidate_count"] == 5


def test_build_policy_change_proposal_prioritizes_policy_misses(tmp_path):
    batch_dir = tmp_path / "policy_review_batches" / "2026-06-08"
    batch_dir.mkdir(parents=True)
    _write_summary(batch_dir / "summary.json")

    build_policy_change_proposal(
        input_dir=tmp_path / "policy_review_batches",
        date="2026-06-08",
    )
    markdown = (batch_dir / "POLICY_CHANGE_PROPOSAL.md").read_text(encoding="utf-8")

    priority_table = markdown.split("## Priority Families", maxsplit=1)[1]
    assert priority_table.index("`composite_thesis`") < priority_table.index(
        "`event_stage_mismatch`"
    )


def _write_summary(path: Path, *, candidate_count: int = 5) -> None:
    summary = {
        "schema_version": "policy_review_batch_v0",
        "candidate_date": path.parent.name,
        "source_dir": f"evals/failure_candidates/{path.parent.name}",
        "candidate_count": candidate_count,
        "families": {
            "event_stage_mismatch": {
                "candidate_count": 2,
                "deterministic_mismatch_count": 1,
                "patterns": [
                    {
                        "family": "event_stage_mismatch",
                        "expected_fit_class": "no_clean_expression",
                        "gemini_fit_class": "indirect",
                        "deterministic_fit_class": "indirect",
                        "count": 1,
                    }
                ],
                "candidates": [
                    {
                        "case_id": "stress_es_openai",
                        "expected_fit_class": "no_clean_expression",
                        "gemini_fit_class": "indirect",
                        "deterministic_fit_class": "indirect",
                        "phoenix_trace_url": "https://phoenix.example/traces/es",
                    }
                ],
            },
            "composite_thesis": {
                "candidate_count": 3,
                "deterministic_mismatch_count": 2,
                "patterns": [
                    {
                        "family": "composite_thesis",
                        "expected_fit_class": "indirect",
                        "gemini_fit_class": "weak_proxy",
                        "deterministic_fit_class": "no_clean_expression",
                        "count": 1,
                    }
                ],
                "candidates": [
                    {
                        "case_id": "stress_ct_trade",
                        "expected_fit_class": "indirect",
                        "gemini_fit_class": "weak_proxy",
                        "deterministic_fit_class": "no_clean_expression",
                        "phoenix_trace_url": "https://phoenix.example/traces/ct",
                    }
                ],
            },
            "metric_mismatch": {
                "candidate_count": 1,
                "deterministic_mismatch_count": 0,
                "patterns": [
                    {
                        "family": "metric_mismatch",
                        "expected_fit_class": "indirect",
                        "gemini_fit_class": "weak_proxy",
                        "deterministic_fit_class": "indirect",
                        "count": 1,
                    }
                ],
                "candidates": [
                    {
                        "case_id": "stress_mm_revenue",
                        "expected_fit_class": "indirect",
                        "gemini_fit_class": "weak_proxy",
                        "deterministic_fit_class": "indirect",
                        "phoenix_trace_url": "https://phoenix.example/traces/mm",
                    }
                ],
            },
        },
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
