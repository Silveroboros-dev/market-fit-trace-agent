import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DIR = ROOT / "evals" / "market_fit_governance_50"


def test_governance_50_manifest_has_required_truth_scopes_and_fields():
    rows = _read_jsonl(GOVERNANCE_DIR / "governance_examples.jsonl")

    assert len(rows) == 50
    assert len({row["governance_id"] for row in rows}) == 50
    for row in rows:
        assert row["fit_class"] in {
            "direct",
            "indirect",
            "weak_proxy",
            "no_clean_expression",
        }
        assert row["truth_scope"] in {
            "strict_golden",
            "failure_mode_golden",
            "reviewed_candidate",
            "draft_candidate",
            "trace_repair_case",
        }
        assert isinstance(row["failure_modes"], list)
        assert row["actual_behavior"]
        assert row["expected_behavior"]
        assert isinstance(row["promotion_blockers"], list)
        assert row["embedding_text"]


def test_governance_50_has_judge_facing_ipo_stage_mismatch_cluster():
    rows = _read_jsonl(GOVERNANCE_DIR / "governance_examples.jsonl")
    hero_rows = [
        row for row in rows if row.get("hero_cluster") == "ai_startup_ipo_stage_mismatch"
    ]
    hero_case_ids = {row["case_id"] for row in hero_rows}

    assert len(hero_rows) == 12
    assert "ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1" in hero_case_ids
    assert "eval_006" in hero_case_ids
    assert "eval_007" in hero_case_ids
    assert "eval_009" in hero_case_ids

    openai = next(
        row
        for row in hero_rows
        if row["case_id"]
        == "ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1"
    )
    assert openai["truth_scope"] == "failure_mode_golden"
    assert openai["fit_class"] == "indirect"
    assert "event_stage_mismatch" in openai["failure_modes"]
    assert openai["expected_best_market_id"] == "2314379"
    assert "656312" in openai["acceptable_market_ids"]


def test_governance_50_phoenix_results_preserve_metric_boundary():
    dataset = json.loads(
        (GOVERNANCE_DIR / "phoenix_dataset_result.json").read_text(encoding="utf-8")
    )
    experiment = json.loads(
        (GOVERNANCE_DIR / "phoenix_experiment_result.json").read_text(encoding="utf-8")
    )

    assert dataset["status"] == "ok"
    assert dataset["dataset_name"] == "market_fit_governance_50"
    assert dataset["row_count"] == 50
    assert dataset["hero_cluster_count"] == 12
    assert dataset["strict_rows_are_not_conflated_with_candidates"] is True
    assert dataset["dataset_url"]

    assert experiment["status"] == "passed"
    assert experiment["main_governance_row_count"] == 50
    assert experiment["experiment_rows_are_usable_expected_labels_only"] is True
    assert experiment["strict_metrics_exclude_weak_or_draft_rows"] is True
    assert experiment["experiment_row_count"] == 26
    assert experiment["strict_metric_row_count"] == 19
    assert experiment["metrics"]["governance_experiment_subset"][
        "stage_mismatch_direct_false_positive_count"
    ] == 0


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
