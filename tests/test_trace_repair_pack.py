import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "evals" / "trace_repair_v1"
MAKEFILE = ROOT / "Makefile"


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


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
