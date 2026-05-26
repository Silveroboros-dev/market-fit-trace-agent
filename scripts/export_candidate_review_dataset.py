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

from phoenix.client import Client

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
    parser.add_argument("--dataset-name", default="market_fit_candidate_review")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--require-run-result",
        action="store_true",
        help="Skip retrieval-only packets that do not include run_result.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not settings.phoenix_base_url or not settings.phoenix_api_key:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "PHOENIX_BASE_URL and PHOENIX_API_KEY are required.",
                },
                indent=2,
            )
        )
        return 2

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
    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    dataset = client.datasets.create_dataset(
        name=args.dataset_name,
        examples=examples,
        dataset_description=(
            "Candidate market-fit goldens awaiting human review. Rows are evidence "
            "packets, not strict eval truth."
        ),
        timeout=60,
    )
    summary = _summary(
        dataset=dataset,
        dataset_name=args.dataset_name,
        examples=examples,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 0


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
    review_notes = (path / "review_notes.md").read_text(encoding="utf-8")
    rules_summary = _rules_status_summary(rules)
    eval_metrics = (run_result or {}).get("eval", {}).get("metrics", {})
    fit = (run_result or {}).get("fit", {})
    claim = (run_result or {}).get("claim", {})
    trace_id = (run_result or {}).get("phoenix_trace_id")
    trace_url = (run_result or {}).get("phoenix_trace_url")
    market_ids = retrieval.get("market_ids_considered") or [
        market.get("market_id") for market in markets
    ]

    return {
        "input": {
            "case_id": source["case_id"],
            "source_text": source["source_text"],
            "source_type": source.get("source_type", "retrieval_candidate"),
        },
        "output": {
            "human_review_status": "pending",
            "reviewer_decision_required": True,
            "expected_fit_class": None,
            "expected_best_market_id": None,
            "recommended_action": _recommended_action(rules_summary, eval_metrics),
        },
        "metadata": {
            "candidate_dir": str(path),
            "created_at_utc": source.get("created_at_utc"),
            "retrieval_id": retrieval.get("retrieval_id"),
            "snapshot_id": retrieval.get("snapshot_id"),
            "as_of_ts": retrieval.get("as_of_ts"),
            "retrieval_mode": retrieval.get("mode"),
            "market_ids_considered": market_ids,
            "returned_count": len(markets),
            "rules_status_summary": rules_summary,
            "run_id": (run_result or {}).get("run_id"),
            "claim_id": (run_result or {}).get("claim_id"),
            "phoenix_trace_id": trace_id,
            "phoenix_trace_url": trace_url,
            "normalized_claim": claim,
            "fit_class_proposed": fit.get("semantic_fit_class"),
            "recommended_market_id": fit.get("recommended_market_id"),
            "fit_reason": fit.get("fit_reason"),
            "false_strong_recommendation": eval_metrics.get(
                "false_strong_recommendation"
            ),
            "weak_proxy_detected": eval_metrics.get("weak_proxy_detected"),
            "unsupported_implication": eval_metrics.get("unsupported_implication"),
            "review_notes_preview": review_notes[:1000],
            "agent_run_status": "run_backed" if run_result else "retrieval_only",
        },
    }


def _summary(*, dataset: Any, dataset_name: str, examples: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "case_id": example["input"]["case_id"],
            "human_review_status": example["output"]["human_review_status"],
            "agent_run_status": example["metadata"]["agent_run_status"],
            "retrieval_id": example["metadata"]["retrieval_id"],
            "snapshot_id": example["metadata"]["snapshot_id"],
            "phoenix_trace_id": example["metadata"]["phoenix_trace_id"],
            "fit_class_proposed": example["metadata"]["fit_class_proposed"],
            "recommended_market_id": example["metadata"]["recommended_market_id"],
            "rules_status_summary": example["metadata"]["rules_status_summary"],
            "recommended_action": example["output"]["recommended_action"],
        }
        for example in examples
    ]
    run_backed = sum(1 for row in rows if row["agent_run_status"] == "run_backed")
    missing_rules_cases = sum(
        1
        for row in rows
        if row["rules_status_summary"].get("missing", 0) > 0
    )
    dataset_url = f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
    return {
        "status": "ok",
        "dataset_name": dataset_name,
        "dataset_id": dataset.id,
        "dataset_version_id": dataset.version_id,
        "dataset_url": dataset_url,
        "candidate_count": len(rows),
        "run_backed_count": run_backed,
        "retrieval_only_count": len(rows) - run_backed,
        "pending_review_count": len(rows),
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
