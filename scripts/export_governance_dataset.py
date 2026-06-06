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

DEFAULT_MANIFEST = Path("evals/market_fit_governance_50/governance_examples.jsonl")
DEFAULT_OUTPUT = Path("evals/market_fit_governance_50/phoenix_dataset_result.json")
DEFAULT_DATASET_NAME = "market_fit_governance_50"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Market Fit Governance 50 rows into a Phoenix Dataset."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = _read_jsonl(Path(args.manifest))
    examples = [_phoenix_example(row) for row in rows]
    missing_config = []
    if not settings.phoenix_base_url:
        missing_config.append("PHOENIX_BASE_URL")
    if not settings.phoenix_api_key:
        missing_config.append("PHOENIX_API_KEY")
    dry_run = bool(args.dry_run or missing_config)

    dataset = None
    phoenix_write_error = None
    if not dry_run:
        try:
            dataset = _create_dataset(args.dataset_name, examples)
        except Exception as exc:  # pragma: no cover - depends on Phoenix service state
            dry_run = True
            phoenix_write_error = f"{type(exc).__name__}: {exc}"

    summary = _summary(
        dataset=dataset,
        dataset_name=args.dataset_name,
        rows=rows,
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


def _phoenix_example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "input": {
            "governance_id": row["governance_id"],
            "case_id": row["case_id"],
            "source_text": row["source_text"],
            "source_type": row.get("source_type"),
            "embedding_text": row["embedding_text"],
        },
        "output": {
            "fit_class": row["fit_class"],
            "truth_scope": row["truth_scope"],
            "failure_modes": row["failure_modes"],
            "actual_behavior": row["actual_behavior"],
            "expected_behavior": row["expected_behavior"],
            "promotion_blockers": row["promotion_blockers"],
        },
        "metadata": {
            "hero_cluster": row.get("hero_cluster"),
            "is_hero_cluster": row.get("is_hero_cluster", False),
            "topic": row.get("topic"),
            "source_kind": row["source_kind"],
            "source_ref": row["source_ref"],
            "review_status": row.get("review_status"),
            "trace_url": row.get("trace_url"),
            "expected_fit_class": row.get("expected_fit_class"),
            "expected_best_market_id": row.get("expected_best_market_id"),
            "acceptable_market_ids": row.get("acceptable_market_ids", []),
            "adjacent_market_ids": row.get("adjacent_market_ids", []),
            "rejected_market_ids": row.get("rejected_market_ids", []),
            "candidate_market_ids": row.get("candidate_market_ids", []),
            "experiment_eligible": row["experiment_eligible"],
            "strict_metric_eligible": row["strict_metric_eligible"],
            "market_snapshot_path": row.get("market_snapshot_path"),
            "dataset_role": "governance_memory",
            "canonical_truth_source": (
                "repo_fixtures"
                if row["truth_scope"] == "strict_golden"
                else "explicit_truth_scope_metadata"
            ),
        },
    }


def _create_dataset(dataset_name: str, examples: list[dict[str, Any]]) -> Any:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    return client.datasets.create_dataset(
        name=dataset_name,
        examples=examples,
        dataset_description=(
            "Market Fit Governance 50: mixed-scope rows showing how trace failures "
            "become reviewed eval memory. Not every row is a strict golden; truth_scope "
            "defines how each row may be used."
        ),
        timeout=60,
    )


def _summary(
    *,
    dataset: Any | None,
    dataset_name: str,
    rows: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    dry_run: bool,
    missing_config: list[str],
    phoenix_write_error: str | None,
) -> dict[str, Any]:
    dataset_url = (
        f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
        if dataset is not None and settings.phoenix_base_url
        else None
    )
    truth_scope_counts = _count(row["truth_scope"] for row in rows)
    return {
        "status": "blocked" if phoenix_write_error else ("dry_run" if dry_run else "ok"),
        "mode": "dry_run" if dry_run else "phoenix",
        "dataset_name": dataset_name,
        "dataset_id": dataset.id if dataset is not None else None,
        "dataset_version_id": dataset.version_id if dataset is not None else None,
        "dataset_url": dataset_url,
        "missing_config": missing_config,
        "phoenix_write_error": phoenix_write_error,
        "row_count": len(rows),
        "example_count": len(examples),
        "truth_scope_counts": truth_scope_counts,
        "hero_cluster": "ai_startup_ipo_stage_mismatch",
        "hero_cluster_count": sum(1 for row in rows if row.get("is_hero_cluster")),
        "strict_rows_are_not_conflated_with_candidates": True,
        "rows": [
            {
                "governance_id": row["governance_id"],
                "case_id": row["case_id"],
                "truth_scope": row["truth_scope"],
                "fit_class": row["fit_class"],
                "hero_cluster": row.get("hero_cluster"),
                "trace_url": row.get("trace_url"),
            }
            for row in rows
        ],
    }


def _count(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    raise SystemExit(main())
