from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adk_runtime import ADKJsonRuntime
from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from market_fit_adk.agent import root_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test ADK runtime and Phoenix tracing wiring."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not require Google/Phoenix credentials; verifies imports and fallback behavior.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    runtime = ADKJsonRuntime()
    phoenix_configured = bool(
        os.getenv("PHOENIX_API_KEY") and os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    )
    google_configured = bool(
        os.getenv("GOOGLE_API_KEY")
        or (
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
            and os.getenv("GOOGLE_CLOUD_PROJECT")
            and os.getenv("GOOGLE_CLOUD_LOCATION")
        )
    )

    if not args.offline and not (phoenix_configured and google_configured):
        print(
            json.dumps(
                {
                    "status": "missing_credentials",
                    "google_configured": google_configured,
                    "phoenix_configured": phoenix_configured,
                    "hint": (
                        "Set GOOGLE_API_KEY or Vertex env vars, plus PHOENIX_API_KEY and "
                        "PHOENIX_COLLECTOR_ENDPOINT, or rerun with --offline."
                    ),
                },
                indent=2,
            )
        )
        return 2

    thesis = (
        "Google TPU claims mean Gemini will close the gap with frontier models this year. "
        "Find the best prediction-market expression and tell me whether the market is a clean fit."
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LedgerStore(Path(tmpdir) / "ledger.json")
        agent = MarketFitTraceAgent(store=store, adk_runtime=runtime)
        result = await agent.run(thesis=thesis, prompt_version="v1_lenient")
        print(
            json.dumps(
                {
                    "status": "ok",
                    "mode": "offline" if args.offline else "live",
                    "adk_import_available": runtime._imports_available(),
                    "adk_runtime_available": runtime.available,
                    "adk_root_agent_name": root_agent.name,
                    "adk_root_agent_model": str(root_agent.model),
                    "google_configured": google_configured,
                    "phoenix_configured": phoenix_configured,
                    "model": result.model,
                    "trace_id": result.phoenix_trace_id,
                    "fit_class": result.fit.semantic_fit_class.value,
                    "false_strong_recommendation": (
                        result.eval.metrics.false_strong_recommendation
                    ),
                    "phoenix_trace_url": _trace_url(result.phoenix_trace_id),
                },
                indent=2,
            )
        )
    return 0


def _trace_url(trace_id: str) -> str | None:
    base_url = os.getenv("PHOENIX_BASE_URL")
    if not base_url or trace_id.startswith("local-"):
        return None
    return f"{base_url.rstrip('/')}/traces/{trace_id}"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
