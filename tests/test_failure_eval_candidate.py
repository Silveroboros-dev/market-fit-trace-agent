import json
from pathlib import Path

from scripts.export_failure_eval_candidate import (
    HUMAN_REVIEW_OPTIONS,
    export_failure_eval_candidate,
)


def test_export_failure_eval_candidate_creates_review_packet_without_mutating_goldens(
    tmp_path,
):
    ledger_path = tmp_path / "ledger_store.json"
    _write_json(ledger_path, _failed_tpu_ledger())

    result = export_failure_eval_candidate(
        run_id="run_tpu_false_strong",
        ledger_store_path=ledger_path,
        out_dir=tmp_path / "failure_candidates",
    )

    candidate_dir = Path(result["candidate_dir"])
    assert result["status"] == "ok"
    assert result["writes_strict_expected_labels"] is False
    assert result["writes_policy_code"] is False
    assert "false_strong_recommendation" in result["failure_metrics"]

    expected_files = {
        "source.json",
        "run_result.json",
        "failure_signal.json",
        "proposed_eval_case.json",
        "policy_gap.md",
        "PR_DESCRIPTION.md",
        "review_notes.md",
    }
    assert expected_files == {path.name for path in candidate_dir.iterdir()}

    proposed = _read_json(candidate_dir / "proposed_eval_case.json")
    assert proposed["truth_scope"] == "failure_candidate"
    assert proposed["canonical_truth"] is False
    assert proposed["writes_strict_expected_labels"] is False
    assert proposed["writes_policy_code"] is False
    assert proposed["human_review_required"] is True
    assert proposed["proposed_target_fit_class"] == "weak_proxy"
    assert "disregard" in proposed["human_review_options"]
    assert proposed["recommended_default_review"] == "promote_to_strict_golden_candidate"
    assert proposed["candidate_market_ids"] == [
        "pm-gemini-arena-2026",
        "pm-tpu-v7-ga-2026",
    ]

    failure_signal = _read_json(candidate_dir / "failure_signal.json")
    assert failure_signal["candidate_only"] is True
    assert failure_signal["observed_fit_class"] == "indirect"
    assert failure_signal["observed_recommended_market_id"] == "pm-gemini-arena-2026"

    policy_gap = (candidate_dir / "policy_gap.md").read_text(encoding="utf-8")
    assert "Human Review Outcomes" in policy_gap
    assert "`disregard`" in policy_gap
    assert "Do not apply this automatically" in policy_gap

    assert not list(tmp_path.rglob("expected_outputs.jsonl"))


def test_export_failure_eval_candidate_defaults_to_disregard_without_failure_metric(
    tmp_path,
):
    ledger = _failed_tpu_ledger()
    metrics = json.loads(ledger["eval_results"][0]["metrics_json"])
    for key in (
        "false_strong_recommendation",
        "unsupported_implication",
        "causal_mechanism_mismatch",
        "resolution_target_mismatch",
        "horizon_mismatch",
        "entity_mismatch",
        "no_clean_expression_expected",
    ):
        metrics[key] = False
    ledger["eval_results"][0]["metrics_json"] = json.dumps(metrics)
    ledger["eval_results"][0]["failure_summary"] = None
    ledger_path = tmp_path / "ledger_store.json"
    _write_json(ledger_path, ledger)

    result = export_failure_eval_candidate(
        run_id="run_tpu_false_strong",
        ledger_store_path=ledger_path,
        out_dir=tmp_path / "failure_candidates",
    )

    proposed = _read_json(Path(result["candidate_dir"]) / "proposed_eval_case.json")
    assert result["failure_metrics"] == ["review_requested_no_failure_metric"]
    assert proposed["recommended_default_review"] == "disregard"
    assert set(HUMAN_REVIEW_OPTIONS) == set(proposed["human_review_options"])


def _failed_tpu_ledger():
    thesis = "Google TPU progress means Gemini closes the frontier-model gap in 2026."
    metrics = {
        "schema_valid": True,
        "false_strong_recommendation": True,
        "weak_proxy_detected": False,
        "unsupported_implication": False,
        "human_verification_required": True,
        "causal_mechanism_mismatch": True,
        "resolution_target_mismatch": False,
        "horizon_mismatch": False,
        "entity_mismatch": False,
        "trace_repair_candidate": True,
    }
    return {
        "sources": [
            {
                "id": "src_tpu",
                "title": "TPU demo",
                "source_type": "pasted_text",
                "uri": None,
                "raw_text": thesis,
                "content_hash": "hash",
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
        "agent_runs": [
            {
                "id": "run_tpu_false_strong",
                "user_goal": thesis,
                "model": "google-adk:gemini-3.5-flash",
                "prompt_version": "v1_lenient",
                "phoenix_trace_id": "trace_tpu",
                "status": "completed",
                "eval_summary_json": json.dumps(metrics),
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
        "claims": [
            {
                "id": "claim_tpu",
                "run_id": "run_tpu_false_strong",
                "source_id": "src_tpu",
                "claim_text": thesis,
                "entities_json": json.dumps(["Google", "TPU", "Gemini"]),
                "horizon": "2026",
                "stance": "expects Gemini to close the frontier-model gap",
                "status": "proposed",
                "confidence": 0.72,
                "reasoning_summary": "Fixture demo claim.",
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
        "market_fit_records": [
            {
                "id": "fit_tpu",
                "claim_id": "claim_tpu",
                "recommended_market_id": "pm-gemini-arena-2026",
                "semantic_fit_class": "indirect",
                "fit_reason": "The market is related but overstates the thesis.",
                "supporting_outcome": None,
                "polarity": None,
                "captures_json": json.dumps(["Gemini progress"]),
                "misses_json": json.dumps(["TPU causal mechanism", "frontier gap closure"]),
                "rejected_markets_json": json.dumps(
                    [
                        {
                            "market_id": "pm-tpu-v7-ga-2026",
                            "reason": "Hardware shipment is not the same as model gap closure.",
                        }
                    ]
                ),
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
        "human_verdicts": [],
        "eval_results": [
            {
                "id": "eval_tpu",
                "run_id": "run_tpu_false_strong",
                "claim_id": "claim_tpu",
                "phoenix_trace_id": "trace_tpu",
                "metrics_json": json.dumps(metrics),
                "failure_summary": "False-strong recommendation: indirect overstates weak proxy.",
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
        "ledger_events": [
            {
                "id": "evt_retrieval",
                "run_id": "run_tpu_false_strong",
                "claim_id": "claim_tpu",
                "event_type": "market_retrieval_run",
                "event_payload_json": {
                    "mode": "fixture",
                    "snapshot_id": None,
                    "retrieval_id": None,
                    "market_ids_considered": [
                        "pm-gemini-arena-2026",
                        "pm-tpu-v7-ga-2026",
                    ],
                },
                "summary": "Retrieved 2 markets via fixture",
                "created_at": "2026-06-08T00:00:00+00:00",
            }
        ],
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
