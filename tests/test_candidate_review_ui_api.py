import json

from app.candidate_review import (
    find_candidate_dir,
    load_candidate_review_detail,
    load_candidate_review_summary,
)
from app.models import (
    CandidateMarket,
    EvalMetrics,
    EvalResult,
    FitClass,
    MarketFit,
    MarketRetrievalProvenance,
    NormalizedClaim,
    RunResult,
)
from app.run_candidates import export_current_run_candidate
from app.source_candidates import list_source_candidate_rows


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


def test_current_run_candidate_export_preserves_source_eval_trace_and_markets(tmp_path):
    candidates_dir = tmp_path / "evals" / "retrieval_candidates"
    run = RunResult(
        run_id="run-1",
        source_id="src-1",
        claim_id="claim-1",
        phoenix_trace_id="trace-1",
        phoenix_trace_url="https://phoenix/traces/trace-1",
        model="test",
        prompt_version="v1_lenient",
        claim=NormalizedClaim(claim_text="Normalized thesis", entities=["Google"]),
        fit=MarketFit(
            recommended_market_id="m1",
            semantic_fit_class=FitClass.INDIRECT,
            fit_reason="Adjacent market.",
        ),
        market_retrieval=MarketRetrievalProvenance(
            mode="fixture",
            retrieval_id="retr-1",
            market_ids_considered=["m1"],
        ),
        market_context=[
            CandidateMarket(
                market_id="m1",
                title="Market one",
                venue="SnapshotMarket",
                description="desc",
                resolution_rules="rules",
                close_date="2026-12-31",
                outcomes=["Yes", "No"],
            )
        ],
        eval=EvalResult(
            phoenix_trace_id="trace-1",
            metrics=EvalMetrics(
                schema_valid=True,
                false_strong_recommendation=True,
                weak_proxy_detected=False,
                unsupported_implication=True,
                human_verification_required=True,
            ),
            failure_summary="False strong.",
        ),
        ledger={"claim_id": "claim-1", "status": "proposed", "events": []},
    )

    detail = export_current_run_candidate(
        source_text="Original messy source",
        run=run,
        case_id="case-run-1",
        source_assisted={
            "source_case_key": "market_fit_v2_candidates::eval_v2_001",
            "pack": "market_fit_v2_candidates",
            "example_id": "eval_v2_001",
            "source_provenance": {
                "source_name": "X / source",
                "fetch_status": "user_provided_grok_validated",
            },
            "proposed_fit_class": "indirect",
            "canonical_truth": False,
            "source_truth_scope": "source_text_and_provenance_only",
        },
        candidates_dir=candidates_dir,
    )

    assert detail["source"]["source_text"] == "Original messy source"
    assert detail["source"]["source_type"] == "source_assisted_current_run_candidate"
    assert detail["source"]["source_assisted"]["canonical_truth"] is False
    assert (
        detail["source"]["source_assisted"]["source_truth_scope"]
        == "source_text_and_provenance_only"
    )
    assert detail["run_result"]["claim"]["claim_text"] == "Normalized thesis"
    assert detail["run_result"]["phoenix_trace_id"] == "trace-1"
    assert detail["run_result"]["eval"]["failure_summary"] == "False strong."
    assert detail["market_snapshots"][0]["market_id"] == "m1"
    summary = load_candidate_review_summary(
        candidates_dir / "phoenix_candidate_review_dataset_result.json",
        candidates_dir=candidates_dir,
    )
    assert [row["case_id"] for row in summary["rows"]] == ["case-run-1"]
    assert (
        summary["rows"][0]["source_assisted_case_key"]
        == "market_fit_v2_candidates::eval_v2_001"
    )
    assert summary["rows"][0]["source_assisted_canonical_truth"] is False
    assert summary["strict_expected_labels_present"] is False


def test_source_candidate_rows_are_source_truth_not_strict_labels():
    summary = list_source_candidate_rows()

    assert summary["source_candidate_count"] == 30
    assert summary["canonical_truth"] is False
    assert summary["truth_scope"] == "source_text_and_provenance_only"
    assert {row["pack"] for row in summary["rows"]} == {
        "market_fit_v2_candidates",
        "market_fit_v3_candidates",
    }
    first = summary["rows"][0]
    assert first["source_case_key"] == f"{first['pack']}::{first['example_id']}"
    assert first["source_text"]
    assert first["source_provenance"]
    assert first["strict_expected_labels_present"] is False
    assert first["canonical_truth"] is False


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
