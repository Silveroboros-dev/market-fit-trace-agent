from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES_DIR = ROOT / "evals" / "retrieval_candidates"
DEFAULT_DATASET_EXPORT = (
    DEFAULT_CANDIDATES_DIR / "phoenix_candidate_review_dataset_result.json"
)
REVIEW_STATUSES = ("promote", "reject", "needs_more_rules", "candidate_only")


def load_candidate_review_summary(
    export_path: Path = DEFAULT_DATASET_EXPORT,
    candidates_dir: Path | None = None,
) -> dict[str, Any]:
    candidates_dir = candidates_dir or export_path.parent
    summary = _read_optional_json(export_path)
    if not summary:
        summary = {
            "status": "missing_export",
            "mode": "local",
            "dataset_name": "market_fit_candidate_cases",
            "dataset_id": None,
            "dataset_version_id": None,
            "dataset_url": None,
            "strict_expected_labels_present": False,
            "candidate_count": 0,
            "run_backed_count": 0,
            "retrieval_only_count": 0,
            "pending_review_count": 0,
            "review_status_counts": {},
            "missing_rules_case_count": 0,
            "rows": [],
        }
    local_summary = _local_candidate_summary(
        candidates_dir=candidates_dir,
        dataset_name=summary.get("dataset_name", "market_fit_candidate_cases"),
    )
    if local_summary:
        summary = {
            **summary,
            "candidate_count": local_summary["candidate_count"],
            "run_backed_count": local_summary["run_backed_count"],
            "retrieval_only_count": local_summary["retrieval_only_count"],
            "pending_review_count": local_summary["pending_review_count"],
            "review_status_counts": local_summary["review_status_counts"],
            "missing_rules_case_count": local_summary["missing_rules_case_count"],
            "rows": local_summary["rows"],
        }
    rows = sorted(summary.get("rows", []), key=_candidate_sort_key)
    return {**summary, "rows": rows}


def load_candidate_review_detail(
    case_id: str,
    candidates_dir: Path = DEFAULT_CANDIDATES_DIR,
    export_path: Path = DEFAULT_DATASET_EXPORT,
) -> dict[str, Any]:
    candidate_dir = find_candidate_dir(case_id, candidates_dir)
    if candidate_dir is None:
        raise FileNotFoundError(case_id)

    summary = load_candidate_review_summary(export_path)
    dataset_row = next(
        (row for row in summary.get("rows", []) if row.get("case_id") == case_id),
        None,
    )
    market_snapshots = _read_jsonl(candidate_dir / "market_snapshots.jsonl")
    agent_rules = _read_jsonl(candidate_dir / "agent_market_rules_snapshots.jsonl")
    source_rules = _read_jsonl(candidate_dir / "market_rules_snapshots.jsonl")
    review_rules = agent_rules or source_rules

    return {
        "case_id": case_id,
        "candidate_dir": _repo_relative(candidate_dir),
        "source": _read_json(candidate_dir / "source.json"),
        "retrieval_result": _read_json(candidate_dir / "retrieval_result.json"),
        "run_result": _read_optional_json(candidate_dir / "run_result.json"),
        "review_decision": _read_optional_json(candidate_dir / "review_decision.json"),
        "llm_review_suggestion": _read_optional_json(
            candidate_dir / "llm_review_suggestion.json"
        ),
        "review_notes": _read_optional_text(candidate_dir / "review_notes.md"),
        "market_snapshots": market_snapshots,
        "market_rules_snapshots": source_rules,
        "agent_market_rules_snapshots": agent_rules,
        "review_rules": review_rules,
        "dataset_export": {
            "status": summary.get("status"),
            "mode": summary.get("mode"),
            "dataset_name": summary.get("dataset_name"),
            "dataset_id": summary.get("dataset_id"),
            "dataset_version_id": summary.get("dataset_version_id"),
            "dataset_url": summary.get("dataset_url"),
            "strict_expected_labels_present": summary.get(
                "strict_expected_labels_present"
            ),
            "row": dataset_row,
        },
    }


def find_candidate_dir(
    case_id: str, candidates_dir: Path = DEFAULT_CANDIDATES_DIR
) -> Path | None:
    if not candidates_dir.exists():
        return None
    matches = []
    for source_path in sorted(candidates_dir.glob("*/*/source.json")):
        source = _read_json(source_path)
        if source.get("case_id") == case_id:
            matches.append(source_path.parent)
    return sorted(matches)[-1] if matches else None


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


def _candidate_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    status_rank = {"promote": 0, "needs_more_rules": 1, "candidate_only": 2, "reject": 3}
    status = str(row.get("human_review_status") or "pending")
    return (status_rank.get(status, 4), str(row.get("case_id") or ""))


def _local_candidate_summary(
    *,
    candidates_dir: Path,
    dataset_name: str,
) -> dict[str, Any] | None:
    if not candidates_dir.exists():
        return None
    from scripts.export_candidate_review_dataset import (
        _candidate_dirs,
        _candidate_example,
        _summary,
    )

    candidate_dirs = _candidate_dirs(candidates_dir)
    if not candidate_dirs:
        return None
    examples = []
    for path in candidate_dirs:
        try:
            examples.append(_candidate_example(path))
        except FileNotFoundError:
            continue
    if not examples:
        return None
    return _summary(
        dataset=None,
        dataset_name=dataset_name,
        examples=examples,
        dry_run=True,
        missing_config=[],
        phoenix_write_error=None,
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
