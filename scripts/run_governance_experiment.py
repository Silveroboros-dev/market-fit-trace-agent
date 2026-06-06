from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import MarketFitTraceAgent
from app.config import settings
from app.ledger import LedgerStore
from app.models import CandidateMarket, FitClass
from scripts.run_evals import OfflineADKRuntime

DEFAULT_MANIFEST = Path("evals/market_fit_governance_50/governance_examples.jsonl")
DEFAULT_OUTPUT = Path("evals/market_fit_governance_50/phoenix_experiment_result.json")
DEFAULT_DATASET_NAME = "market_fit_governance_50_policy_subset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the current deterministic policy against governance rows that have "
            "usable expected labels, then optionally publish a Phoenix Experiment."
        )
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--experiment-name", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    all_rows = _read_jsonl(manifest_path)
    experiment_rows = [
        row
        for row in all_rows
        if row.get("experiment_eligible")
        and row.get("expected_fit_class")
        and row.get("market_snapshot_path")
    ]
    results = _run_policy_rows(experiment_rows)
    experiment_name = (
        args.experiment_name
        or f"current-policy-market_fit_governance_50-{_short_commit_sha()}"
    )

    missing_config = []
    if not settings.phoenix_base_url:
        missing_config.append("PHOENIX_BASE_URL")
    if not settings.phoenix_api_key:
        missing_config.append("PHOENIX_API_KEY")
    dry_run = bool(args.dry_run or missing_config)

    dataset = None
    experiment_id = None
    experiment_url = None
    phoenix_error = None
    if not dry_run:
        try:
            dataset = _create_experiment_dataset(args.dataset_name, experiment_rows)
            experiment = _run_phoenix_experiment(
                dataset=dataset,
                rows=results,
                experiment_name=experiment_name,
            )
            experiment_id = experiment["experiment_id"]
            experiment_url = experiment["experiment_url"]
        except Exception as exc:  # pragma: no cover - depends on Phoenix service state
            dry_run = True
            phoenix_error = f"{type(exc).__name__}: {exc}"

    summary = _summary(
        all_rows=all_rows,
        experiment_rows=experiment_rows,
        result_rows=results,
        dataset=dataset,
        dataset_name=args.dataset_name,
        experiment_name=experiment_name,
        experiment_id=experiment_id,
        experiment_url=experiment_url,
        dry_run=dry_run,
        missing_config=missing_config,
        phoenix_error=phoenix_error,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    if phoenix_error:
        return 2
    return 0 if summary["status"] == "passed" else 1


def _run_policy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    market_cache: dict[str, list[CandidateMarket]] = {}
    for row in rows:
        market_path = row["market_snapshot_path"]
        if market_path not in market_cache:
            market_cache[market_path] = _load_markets(Path(market_path))
        prompt_version = (
            "v2_trace_inspected"
            if row["expected_fit_class"] == FitClass.WEAK_PROXY.value
            else "v1_lenient"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LedgerStore(Path(tmpdir) / "ledger.json")
            agent = MarketFitTraceAgent(
                store=store,
                adk_runtime=OfflineADKRuntime(),
                markets=market_cache[market_path],
            )
            result = asyncio.run(
                agent.run(
                    thesis=row["source_text"],
                    title=row.get("source_provenance", {}).get("source_name"),
                    prompt_version=prompt_version,
                )
            )
        result_row = {
            "governance_id": row["governance_id"],
            "case_id": row["case_id"],
            "truth_scope": row["truth_scope"],
            "strict_metric_eligible": row["strict_metric_eligible"],
            "hero_cluster": row.get("hero_cluster"),
            "failure_modes": row["failure_modes"],
            "expected_fit_class": row["expected_fit_class"],
            "actual_fit_class": result.fit.semantic_fit_class.value,
            "expected_best_market_id": row.get("expected_best_market_id"),
            "actual_market_id": result.fit.recommended_market_id,
            "acceptable_market_ids": row.get("acceptable_market_ids", []),
            "adjacent_market_ids": row.get("adjacent_market_ids", []),
            "false_strong_recommendation": result.eval.metrics.false_strong_recommendation,
            "weak_proxy_detected": result.eval.metrics.weak_proxy_detected,
            "unsupported_implication": result.eval.metrics.unsupported_implication,
            "failure_summary": result.eval.failure_summary,
            "trace_id": result.phoenix_trace_id,
            "trace_url": result.phoenix_trace_url,
        }
        _score_row(result_row)
        results.append(result_row)
    return results


def _create_experiment_dataset(dataset_name: str, rows: list[dict[str, Any]]) -> Any:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    return client.datasets.create_dataset(
        name=dataset_name,
        examples=[_experiment_example(row) for row in rows],
        dataset_description=(
            "Policy-evaluation subset derived from market_fit_governance_50. "
            "Includes only rows with usable expected labels; weak/draft governance "
            "rows are intentionally excluded from strict accuracy metrics."
        ),
        timeout=60,
    )


def _experiment_example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "input": {
            "governance_id": row["governance_id"],
            "case_id": row["case_id"],
            "source_text": row["source_text"],
        },
        "output": {
            "expected_fit_class": row["expected_fit_class"],
            "expected_best_market_id": row.get("expected_best_market_id"),
            "acceptable_market_ids": row.get("acceptable_market_ids", []),
            "adjacent_market_ids": row.get("adjacent_market_ids", []),
            "expected_behavior": row["expected_behavior"],
        },
        "metadata": {
            "truth_scope": row["truth_scope"],
            "strict_metric_eligible": row["strict_metric_eligible"],
            "failure_modes": row["failure_modes"],
            "hero_cluster": row.get("hero_cluster"),
            "source_ref": row["source_ref"],
            "market_snapshot_path": row["market_snapshot_path"],
        },
    }


def _run_phoenix_experiment(
    *,
    dataset: Any,
    rows: list[dict[str, Any]],
    experiment_name: str,
) -> dict[str, Any]:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    rows_by_id = {row["governance_id"]: row for row in rows}

    def task(input: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        _ = expected
        return rows_by_id[input["governance_id"]]

    ran = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators={
            "fit_class_match": _fit_class_match,
            "market_id_match": _market_id_match,
            "false_strong_guard": _false_strong_guard,
            "stage_mismatch_guard": _stage_mismatch_guard,
        },
        experiment_name=experiment_name,
        experiment_description=(
            "Current deterministic market-fit policy compared against the labeled "
            "subset of Market Fit Governance 50."
        ),
        experiment_metadata={
            "main_governance_dataset": "market_fit_governance_50",
            "experiment_rows_are_usable_expected_labels_only": True,
            "strict_metrics_exclude_weak_or_draft_rows": True,
            "market_data_mode": "fixture",
            "llm_as_judge": False,
            "commit_sha": _commit_sha(),
        },
        dry_run=False,
        print_summary=True,
        timeout=120,
    )
    experiment_id = ran["experiment_id"]
    return {
        "experiment_id": experiment_id,
        "experiment_url": client.experiments.get_experiment_url(
            dataset_id=dataset.id,
            experiment_id=experiment_id,
        ),
    }


def _fit_class_match(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    passed = output["actual_fit_class"] == expected["expected_fit_class"]
    return {
        "label": "pass" if passed else "fail",
        "score": 1.0 if passed else 0.0,
        "explanation": (
            f"expected={expected['expected_fit_class']} "
            f"actual={output['actual_fit_class']}"
        ),
    }


def _market_id_match(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    row = {
        "expected_fit_class": expected["expected_fit_class"],
        "actual_market_id": output["actual_market_id"],
        "expected_best_market_id": expected["expected_best_market_id"],
        "acceptable_market_ids": expected["acceptable_market_ids"],
        "adjacent_market_ids": expected["adjacent_market_ids"],
    }
    passed = _market_id_passed(row)
    return {
        "label": "pass" if passed else "fail",
        "score": 1.0 if passed else 0.0,
        "explanation": (
            f"expected_best={expected['expected_best_market_id']} "
            f"actual={output['actual_market_id']}"
        ),
    }


def _false_strong_guard(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    _ = expected
    passed = not output["false_strong_recommendation"]
    return {
        "label": "pass" if passed else "fail",
        "score": 1.0 if passed else 0.0,
        "explanation": f"false_strong={output['false_strong_recommendation']}",
    }


def _stage_mismatch_guard(
    output: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    _ = expected
    is_stage_case = "event_stage_mismatch" in output.get("failure_modes", [])
    passed = not is_stage_case or output["actual_fit_class"] != FitClass.DIRECT.value
    return {
        "label": "pass" if passed else "fail",
        "score": 1.0 if passed else 0.0,
        "explanation": (
            "event_stage_mismatch case must not be classified direct; "
            f"actual={output['actual_fit_class']}"
        ),
    }


def _summary(
    *,
    all_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    dataset: Any | None,
    dataset_name: str,
    experiment_name: str,
    experiment_id: str | None,
    experiment_url: str | None,
    dry_run: bool,
    missing_config: list[str],
    phoenix_error: str | None,
) -> dict[str, Any]:
    passed = all(row["passed"] for row in result_rows)
    strict_rows = [row for row in result_rows if row["strict_metric_eligible"]]
    governance_metrics = _metric_summary(result_rows)
    strict_metrics = _metric_summary(strict_rows)
    dataset_url = (
        f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
        if dataset is not None and settings.phoenix_base_url
        else None
    )
    return {
        "status": "blocked" if phoenix_error else ("passed" if passed else "failed"),
        "mode": "dry_run" if dry_run else "phoenix",
        "main_governance_dataset_name": "market_fit_governance_50",
        "main_governance_row_count": len(all_rows),
        "experiment_dataset_name": dataset_name,
        "experiment_dataset_id": dataset.id if dataset is not None else None,
        "experiment_dataset_version_id": dataset.version_id if dataset is not None else None,
        "experiment_dataset_url": dataset_url,
        "experiment_name": experiment_name,
        "experiment_id": experiment_id,
        "experiment_url": experiment_url,
        "missing_config": missing_config,
        "phoenix_error": phoenix_error,
        "commit_sha": _commit_sha(),
        "experiment_rows_are_usable_expected_labels_only": True,
        "strict_metrics_exclude_weak_or_draft_rows": True,
        "governance_metrics_include_all_50_rows": len(all_rows) == 50,
        "experiment_row_count": len(experiment_rows),
        "strict_metric_row_count": len(strict_rows),
        "passed_count": sum(1 for row in result_rows if row["passed"]),
        "metrics": {
            "governance_experiment_subset": governance_metrics,
            "strict_only": strict_metrics,
        },
        "rows": result_rows,
    }


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "fit_class_accuracy": 0.0,
            "market_id_accuracy": 0.0,
            "false_strong_recommendation_rate": 0.0,
            "stage_mismatch_case_count": 0,
            "stage_mismatch_direct_false_positive_count": 0,
        }
    stage_rows = [
        row for row in rows if "event_stage_mismatch" in row.get("failure_modes", [])
    ]
    stage_false_positive_rows = [
        row for row in stage_rows if row["actual_fit_class"] == FitClass.DIRECT.value
    ]
    return {
        "row_count": len(rows),
        "fit_class_accuracy": _mean(row["fit_class_passed"] for row in rows),
        "market_id_accuracy": _mean(row["market_id_passed"] for row in rows),
        "false_strong_recommendation_rate": _mean(
            row["false_strong_recommendation"] for row in rows
        ),
        "stage_mismatch_case_count": len(stage_rows),
        "stage_mismatch_direct_false_positive_count": len(stage_false_positive_rows),
        "stage_mismatch_direct_false_positive_case_ids": [
            row["case_id"] for row in stage_false_positive_rows
        ],
    }


def _score_row(row: dict[str, Any]) -> None:
    row["fit_class_passed"] = row["expected_fit_class"] == row["actual_fit_class"]
    row["market_id_passed"] = _market_id_passed(row)
    row["stage_mismatch_passed"] = bool(
        "event_stage_mismatch" not in row.get("failure_modes", [])
        or row["actual_fit_class"] != FitClass.DIRECT.value
    )
    row["eval_metrics_passed"] = bool(
        not row["false_strong_recommendation"]
        and not row["unsupported_implication"]
        and (
            row["expected_fit_class"] != FitClass.WEAK_PROXY.value
            or row["weak_proxy_detected"]
        )
    )
    row["passed"] = bool(
        row["fit_class_passed"]
        and row["market_id_passed"]
        and row["stage_mismatch_passed"]
        and row["eval_metrics_passed"]
    )


def _market_id_passed(row: dict[str, Any]) -> bool:
    expected_class = row["expected_fit_class"]
    actual = row["actual_market_id"]
    best = row["expected_best_market_id"]
    acceptable = set(row.get("acceptable_market_ids", []))
    adjacent = set(row.get("adjacent_market_ids", []))
    if expected_class == FitClass.NO_CLEAN_EXPRESSION.value:
        return actual is None
    if expected_class == FitClass.WEAK_PROXY.value:
        return actual is None or actual == best or actual in acceptable or actual in adjacent
    return actual == best or actual in acceptable


def _load_markets(path: Path) -> list[CandidateMarket]:
    markets: list[CandidateMarket] = []
    for item in _read_jsonl(path):
        close_time = item.get("close_time") or item.get("close_date") or ""
        markets.append(
            CandidateMarket(
                market_id=str(item["market_id"]),
                title=str(item["title"]),
                venue=str(item["venue"]),
                description=str(item.get("description") or ""),
                resolution_rules=str(item.get("resolution_rules") or ""),
                close_date=str(close_time).split("T")[0] if close_time else "unspecified",
                outcomes=[str(outcome) for outcome in item.get("outcomes", ["Yes", "No"])],
                current_probability=item.get("yes_price", item.get("current_probability")),
                known_fit_risks=[str(risk) for risk in item.get("known_fit_risks", [])],
                entity_tags=[str(tag) for tag in item.get("tags", item.get("entity_tags", []))],
            )
        )
    return markets


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _mean(values: Any) -> float:
    items = [bool(value) for value in values]
    if not items:
        return 0.0
    return sum(1 for item in items if item) / len(items)


def _commit_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip()


def _short_commit_sha() -> str:
    sha = _commit_sha()
    return sha[:7] if sha != "unknown" else "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
