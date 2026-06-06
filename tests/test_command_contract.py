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
