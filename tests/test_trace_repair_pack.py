import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "evals" / "trace_repair_v1"
MAKEFILE = ROOT / "Makefile"
RESULT = PACK / "run_results" / "trace_repair_result.json"
REQUIRED_TRACE_SIGNALS = {
    "false_strong_recommendation",
    "causal_mechanism_mismatch",
    "resolution_target_mismatch",
    "trace_repair_candidate",
}


def test_trace_repair_pack_is_separate_transition_eval():
    readme = (PACK / "README.md").read_text(encoding="utf-8")
    cases = _read_jsonl(PACK / "cases.jsonl")
    expected = _read_jsonl(PACK / "expected_transitions.jsonl")
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "not a strict" in readme
    assert "correctness-golden pack" in readme
    assert len(cases) >= 1
    assert cases[0]["case_type"] == "trace_repair"
    assert cases[0]["source_status"] == "manual_demo_seed"
    assert "expected_fit" not in cases[0]

    transition = expected[0]
    assert transition["first_run_expected"]["false_strong_recommendation"] is True
    assert transition["inspection_expected"]["inspection_source"] == "phoenix_mcp"
    assert transition["inspection_expected"]["fallback_used"] is False
    assert transition["second_run_expected"]["trace_repair_gate_applied"] is True
    assert "scripts/run_trace_repair_eval.py" in makefile


def test_trace_repair_result_proves_real_phoenix_inspection_context():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    phoenix_trace = result["phoenix_trace"]
    improvement = result["improvement"]

    assert result["status"] == "passed"
    assert result["inspection_source"] == "phoenix_mcp"
    assert result["fallback_used"] is False
    assert phoenix_trace["passed"] is True
    assert not phoenix_trace["trace_id"].startswith("local-")
    assert phoenix_trace["fit_eval_span_id"]
    assert set(phoenix_trace["required_signals_found"]) == REQUIRED_TRACE_SIGNALS
    assert phoenix_trace["required_signals_missing"] == []
    assert phoenix_trace["mismatched_annotation_values"] == {}
    assert all(improvement["checks"].values())
    assert improvement["checks"]["trace_repair_gate_applied"] is True

    actual_values = phoenix_trace["actual_annotation_values"]
    assert actual_values["false_strong_recommendation"] == "fail"
    assert actual_values["causal_mechanism_mismatch"] == "true"
    assert actual_values["resolution_target_mismatch"] == "true"
    assert actual_values["trace_repair_candidate"] == "true"

    summary = improvement["inspection_summary"]
    assert phoenix_trace["trace_id"] in summary
    assert "Annotation names returned" in summary
    for signal in REQUIRED_TRACE_SIGNALS:
        assert signal in summary


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
