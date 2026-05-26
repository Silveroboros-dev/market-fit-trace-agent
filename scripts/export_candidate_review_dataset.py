from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings

DEFAULT_CANDIDATES_DIR = Path("evals/retrieval_candidates")
DEFAULT_OUTPUT = DEFAULT_CANDIDATES_DIR / "phoenix_candidate_review_dataset_result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export retrieval candidate packets into a Phoenix Dataset review queue."
        )
    )
    parser.add_argument("--candidates-dir", default=str(DEFAULT_CANDIDATES_DIR))
    parser.add_argument("--dataset-name", default="market_fit_candidate_cases")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--require-run-result",
        action="store_true",
        help="Skip retrieval-only packets that do not include run_result.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the local JSON report without creating/updating a Phoenix Dataset.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_dirs = _candidate_dirs(Path(args.candidates_dir))
    if args.require_run_result:
        candidate_dirs = [path for path in candidate_dirs if (path / "run_result.json").exists()]
    if args.limit > 0:
        candidate_dirs = candidate_dirs[: args.limit]
    if not candidate_dirs:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": (
                        "No candidate packets found. Run "
                        "`python scripts/export_retrieval_candidate.py --run-agent` first."
                    ),
                },
                indent=2,
            )
        )
        return 1

    examples = [_candidate_example(path) for path in candidate_dirs]
    missing_config = []
    if not settings.phoenix_base_url:
        missing_config.append("PHOENIX_BASE_URL")
    if not settings.phoenix_api_key:
        missing_config.append("PHOENIX_API_KEY")
    dry_run = bool(args.dry_run or missing_config)
    phoenix_write_error = None
    dataset = None
    if not dry_run:
        try:
            dataset = _create_phoenix_dataset(args.dataset_name, examples)
        except Exception as exc:  # pragma: no cover - depends on Phoenix service state
            dry_run = True
            phoenix_write_error = f"{type(exc).__name__}: {exc}"
    summary = _summary(
        dataset=dataset,
        dataset_name=args.dataset_name,
        examples=examples,
        dry_run=dry_run,
        missing_config=missing_config,
        phoenix_write_error=phoenix_write_error,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 2 if phoenix_write_error else 0


def _candidate_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path.parent
        for path in root.glob("*/*/source.json")
        if (path.parent / "retrieval_result.json").exists()
    )


def _candidate_example(path: Path) -> dict[str, Any]:
    source = _read_json(path / "source.json")
    retrieval = _read_json(path / "retrieval_result.json")
    markets = _read_jsonl(path / "market_snapshots.jsonl")
    rules = _read_jsonl(path / "market_rules_snapshots.jsonl")
    run_result = _read_optional_json(path / "run_result.json")
    review_decision = _read_optional_json(path / "review_decision.json") or {}
    review_notes = (path / "review_notes.md").read_text(encoding="utf-8")
    rules_summary = _rules_status_summary(rules)
    eval_metrics = (run_result or {}).get("eval", {}).get("metrics", {})
    fit = (run_result or {}).get("fit", {})
    claim = (run_result or {}).get("claim", {})
    trace_id = (run_result or {}).get("phoenix_trace_id")
    trace_url = (run_result or {}).get("phoenix_trace_url")
    run_retrieval = (run_result or {}).get("market_retrieval") or {}
    review_retrieval = run_retrieval or retrieval
    retrieved_market_ids = review_retrieval.get("market_ids_considered") or [
        market.get("market_id") for market in markets
    ]
    source_market_ids = retrieval.get("market_ids_considered") or [
        market.get("market_id") for market in markets
    ]
    rules_status = _overall_rules_status(rules_summary)

    return {
        "input": {
            "case_id": source["case_id"],
            "source_text": source["source_text"],
            "source_type": source.get("source_type", "retrieval_candidate"),
        },
        "output": {
            "human_review_status": review_decision.get(
                "human_review_status", "pending"
            ),
            "reviewer_note": review_decision.get("reviewer_note", ""),
            "reviewer_decision_required": True,
            "recommended_action": _recommended_action(rules_summary, eval_metrics),
        },
        "metadata": {
            "candidate_dir": str(path),
            "created_at_utc": source.get("created_at_utc"),
            "retrieval_id": review_retrieval.get("retrieval_id"),
            "snapshot_id": review_retrieval.get("snapshot_id"),
            "as_of_ts": review_retrieval.get("as_of_ts"),
            "retrieval_mode": review_retrieval.get("mode"),
            "retrieved_market_ids": retrieved_market_ids,
            "market_ids_considered": retrieved_market_ids,
            "agent_retrieval_id": run_retrieval.get("retrieval_id"),
            "agent_market_ids_considered": run_retrieval.get("market_ids_considered"),
            "source_retrieval_id": retrieval.get("retrieval_id"),
            "source_market_ids_considered": source_market_ids,
            "returned_count": len(markets),
            "rules_status": rules_status,
            "rules_status_summary": rules_summary,
            "run_id": (run_result or {}).get("run_id"),
            "claim_id": (run_result or {}).get("claim_id"),
            "trace_id": trace_id,
            "phoenix_trace_id": trace_id,
            "phoenix_trace_url": trace_url,
            "normalized_claim": claim,
            "proposed_fit_class": fit.get("semantic_fit_class"),
            "fit_class_proposed": fit.get("semantic_fit_class"),
            "recommended_market_id": fit.get("recommended_market_id"),
            "fit_reason": fit.get("fit_reason"),
            "false_strong_recommendation": eval_metrics.get(
                "false_strong_recommendation"
            ),
            "weak_proxy_detected": eval_metrics.get("weak_proxy_detected"),
            "unsupported_implication": eval_metrics.get("unsupported_implication"),
            "review_notes_preview": review_notes[:1000],
            "reviewed_at_utc": review_decision.get("reviewed_at_utc"),
            "reviewer": review_decision.get("reviewer"),
            "review_decision_path": (
                str(path / "review_decision.json")
                if (path / "review_decision.json").exists()
                else None
            ),
            "agent_run_status": "run_backed" if run_result else "retrieval_only",
        },
    }


def _create_phoenix_dataset(dataset_name: str, examples: list[dict[str, Any]]) -> Any:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    return client.datasets.create_dataset(
        name=dataset_name,
        examples=examples,
        dataset_description=(
            "Candidate market-fit goldens awaiting human review. Rows are evidence "
            "packets, not strict eval truth."
        ),
        timeout=60,
    )


def _summary(
    *,
    dataset: Any | None,
    dataset_name: str,
    examples: list[dict[str, Any]],
    dry_run: bool = False,
    missing_config: list[str] | None = None,
    phoenix_write_error: str | None = None,
) -> dict[str, Any]:
    rows = [
        {
            "case_id": example["input"]["case_id"],
            "source_text": example["input"]["source_text"],
            "normalized_claim": example["metadata"]["normalized_claim"],
            "retrieved_market_ids": example["metadata"]["retrieved_market_ids"],
            "human_review_status": example["output"]["human_review_status"],
            "reviewer_note": example["output"]["reviewer_note"],
            "reviewed_at_utc": example["metadata"].get("reviewed_at_utc"),
            "reviewer": example["metadata"].get("reviewer"),
            "agent_run_status": example["metadata"]["agent_run_status"],
            "run_id": example["metadata"]["run_id"],
            "trace_id": example["metadata"]["trace_id"],
            "retrieval_id": example["metadata"]["retrieval_id"],
            "snapshot_id": example["metadata"]["snapshot_id"],
            "as_of_ts": example["metadata"]["as_of_ts"],
            "phoenix_trace_id": example["metadata"]["phoenix_trace_id"],
            "proposed_fit_class": example["metadata"]["proposed_fit_class"],
            "recommended_market_id": example["metadata"]["recommended_market_id"],
            "weak_proxy_detected": example["metadata"]["weak_proxy_detected"],
            "false_strong_recommendation": example["metadata"][
                "false_strong_recommendation"
            ],
            "unsupported_implication": example["metadata"]["unsupported_implication"],
            "rules_status": example["metadata"]["rules_status"],
            "rules_status_summary": example["metadata"]["rules_status_summary"],
            "recommended_action": example["output"]["recommended_action"],
        }
        for example in examples
    ]
    run_backed = sum(1 for row in rows if row["agent_run_status"] == "run_backed")
    review_status_counts = _review_status_counts(rows)
    missing_rules_cases = sum(
        1
        for row in rows
        if row["rules_status_summary"].get("missing", 0) > 0
    )
    dataset_url = (
        f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
        if dataset is not None and settings.phoenix_base_url
        else None
    )
    return {
        "status": "blocked" if phoenix_write_error else ("dry_run" if dry_run else "ok"),
        "mode": "dry_run" if dry_run else "phoenix",
        "dataset_name": dataset_name,
        "dataset_id": dataset.id if dataset is not None else None,
        "dataset_version_id": dataset.version_id if dataset is not None else None,
        "dataset_url": dataset_url,
        "missing_config": missing_config or [],
        "phoenix_write_error": phoenix_write_error,
        "strict_expected_labels_present": False,
        "candidate_count": len(rows),
        "run_backed_count": run_backed,
        "retrieval_only_count": len(rows) - run_backed,
        "pending_review_count": review_status_counts.get("pending", 0),
        "review_status_counts": review_status_counts,
        "missing_rules_case_count": missing_rules_cases,
        "rows": rows,
    }


def _recommended_action(
    rules_summary: dict[str, int],
    eval_metrics: dict[str, Any],
) -> str:
    if rules_summary.get("missing", 0):
        return "needs_more_rules"
    if eval_metrics.get("false_strong_recommendation"):
        return "review_for_weak_proxy_golden"
    if eval_metrics.get("weak_proxy_detected"):
        return "review_for_weak_proxy_coverage"
    return "review"


def _rules_status_summary(rules: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for rule in rules:
        status = str(rule.get("rules_status") or "unknown")
        summary[status] = summary.get(status, 0) + 1
    return summary


def _review_status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for row in rows:
        status = str(row.get("human_review_status") or "pending")
        summary[status] = summary.get(status, 0) + 1
    return summary


def _overall_rules_status(rules_summary: dict[str, int]) -> str:
    if not rules_summary:
        return "unknown"
    if len(rules_summary) == 1:
        return next(iter(rules_summary))
    return "mixed"


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


if __name__ == "__main__":
    raise SystemExit(main())
