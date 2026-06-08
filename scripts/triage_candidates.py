from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.candidate_triage import (  # noqa: E402
    DEFAULT_CANDIDATES_DIR,
    JUDGE_VERSION,
    OUTPUT_NAME,
    LocalRuleRuntime,
    _candidate_dirs,
    triage_candidate_dir,
)
from app.adk_runtime import ADKJsonRuntime  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate non-canonical LLM review suggestions for retrieval candidate packets."
        )
    )
    parser.add_argument("--candidates-dir", default=str(DEFAULT_CANDIDATES_DIR))
    parser.add_argument("--case-id", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Skip Gemini/ADK and write deterministic local triage suggestions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print triage suggestions without writing llm_review_suggestion.json files.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    candidate_dirs = _candidate_dirs(Path(args.candidates_dir), case_id=args.case_id)
    if args.limit > 0:
        candidate_dirs = candidate_dirs[: args.limit]
    if not candidate_dirs:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "No retrieval candidate packets found.",
                    "candidates_dir": args.candidates_dir,
                    "case_id": args.case_id or None,
                },
                indent=2,
            )
        )
        return 1

    runtime = LocalRuleRuntime() if args.force_local else ADKJsonRuntime()
    rows = []
    for candidate_dir in candidate_dirs:
        suggestion = await triage_candidate_dir(candidate_dir, runtime=runtime)
        output_path = candidate_dir / OUTPUT_NAME
        if not args.dry_run:
            output_path.write_text(
                json.dumps(suggestion, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        rows.append(
            {
                "case_id": suggestion["candidate_id"],
                "candidate_dir": str(candidate_dir),
                "suggestion_path": str(output_path),
                "review_priority": suggestion["review_priority"],
                "suggested_review_status": suggestion["suggested_review_status"],
                "likely_issues": suggestion["likely_issues"],
                "triage_source": suggestion["triage_source"],
            }
        )

    summary = {
        "status": "dry_run" if args.dry_run else "ok",
        "candidate_count": len(rows),
        "judge_version": JUDGE_VERSION,
        "rows": rows,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
