import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_api_command_defaults_to_fixture_path_and_live_mode_is_explicit():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    api_target = re.search(r"^api:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)
    live_target = re.search(r"^api-live:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)

    assert api_target is not None
    assert live_target is not None
    assert "MARKET_PROVIDER=polydata" not in api_target.group("body")
    assert "PHOENIX_MCP_ENABLED=true" in api_target.group("body")
    assert "uvicorn app.main:app" in api_target.group("body")
    assert "PHOENIX_MCP_ENABLED=true" in live_target.group("body")
    assert "MARKET_PROVIDER=polydata" in live_target.group("body")


def test_failure_eval_candidate_command_is_candidate_only():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = re.search(
        r"^export-failure-eval-candidate:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        re.MULTILINE,
    )

    assert target is not None
    body = target.group("body")
    assert "scripts/export_failure_eval_candidate.py" in body
    assert "--run-id \"$(RUN_ID)\"" in body
    assert "expected_outputs.jsonl" not in body


def test_policy_review_batch_command_is_read_only_over_failure_candidates():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = re.search(
        r"^policy-review-batch:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        re.MULTILINE,
    )

    assert target is not None
    body = target.group("body")
    assert "scripts/build_policy_review_batch.py" in body
    assert "expected_outputs.jsonl" not in body
    assert "app/workflow.py" not in body
