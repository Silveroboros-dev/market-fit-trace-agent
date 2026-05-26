from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_CANDIDATES_DIR = Path("evals/retrieval_candidates")
REVIEW_STATUSES = ("promote", "reject", "needs_more_rules", "candidate_only")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a human review decision for a retrieval candidate packet."
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--status", required=True, choices=REVIEW_STATUSES)
    parser.add_argument("--note", default="")
    parser.add_argument("--reviewer", default="local_reviewer")
    parser.add_argument("--candidates-dir", default=str(DEFAULT_CANDIDATES_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates_dir = Path(args.candidates_dir)
    candidate_dir = find_candidate_dir(candidates_dir, args.case_id)
    if candidate_dir is None:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"No candidate packet found for case_id={args.case_id!r}.",
                    "candidates_dir": str(candidates_dir),
                },
                indent=2,
            )
        )
        return 1

    decision = build_review_decision(
        case_id=args.case_id,
        candidate_dir=candidate_dir,
        status=args.status,
        note=args.note,
        reviewer=args.reviewer,
    )
    output_path = candidate_dir / "review_decision.json"
    output_path.write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "case_id": args.case_id,
                "candidate_dir": str(candidate_dir),
                "review_decision_path": str(output_path),
                "human_review_status": args.status,
                "reviewer_note": args.note,
            },
            indent=2,
        )
    )
    return 0


def find_candidate_dir(root: Path, case_id: str) -> Path | None:
    if not root.exists():
        return None
    matches = [
        path.parent
        for path in root.glob(f"*/{case_id}/source.json")
        if (path.parent / "retrieval_result.json").exists()
    ]
    if not matches:
        return None
    return sorted(matches)[-1]


def build_review_decision(
    *,
    case_id: str,
    candidate_dir: Path,
    status: str,
    note: str,
    reviewer: str,
) -> dict[str, Any]:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Unsupported review status: {status}")
    return {
        "case_id": case_id,
        "candidate_dir": str(candidate_dir),
        "human_review_status": status,
        "reviewer_note": note,
        "reviewed_at_utc": datetime.now(UTC).isoformat(),
        "reviewer": reviewer,
    }


if __name__ == "__main__":
    raise SystemExit(main())
