from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import re
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
from scripts.run_evals import MARKET_FIT_RISKS, OfflineADKRuntime

V1_CASES = Path("evals/market_fit_v1/examples.jsonl")
V1_EXPECTED = Path("evals/market_fit_v1/expected_outputs.jsonl")
V1_MARKETS = Path("evals/market_fit_v1/market_snapshots.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror promoted frozen goldens into a Phoenix Dataset and optionally "
            "run a deterministic Phoenix Experiment against expected labels."
        )
    )
    parser.add_argument("--cases", default=str(V1_CASES))
    parser.add_argument("--expected", default=str(V1_EXPECTED))
    parser.add_argument("--markets", default=str(V1_MARKETS))
    parser.add_argument("--eval-pack-name", default="")
    parser.add_argument("--dataset-name", default="")
    parser.add_argument("--experiment-name", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sync-only", action="store_true")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases_path = Path(args.cases)
    expected_path = Path(args.expected)
    markets_path = Path(args.markets)
    eval_pack = args.eval_pack_name or cases_path.parent.name
    dataset_name = args.dataset_name or f"market_fit_promoted_goldens_{_pack_suffix(eval_pack)}"
    output_path = _output_path(args, cases_path)

    cases = _read_jsonl(cases_path)
    if args.limit > 0:
        cases = cases[: args.limit]
    expected_by_case = {item["example_id"]: item for item in _read_jsonl(expected_path)}
    missing_expected = [
        case["example_id"] for case in cases if case["example_id"] not in expected_by_case
    ]
    if missing_expected:
        _write_summary(
            output_path,
            {
                "status": "error",
                "message": "Expected output is missing for one or more cases.",
                "missing_case_ids": missing_expected,
            },
        )
        return 1

    dataset_examples = [
        _dataset_example(case, expected_by_case[case["example_id"]], eval_pack)
        for case in cases
    ]

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
            dataset = _create_phoenix_dataset(dataset_name, dataset_examples, eval_pack)
        except Exception as exc:  # pragma: no cover - depends on Phoenix service state
            dry_run = True
            phoenix_write_error = f"{type(exc).__name__}: {exc}"

    dataset_summary = _dataset_sync_summary(
        dataset=dataset,
        dataset_name=dataset_name,
        examples=dataset_examples,
        eval_pack=eval_pack,
        dry_run=dry_run,
        missing_config=missing_config,
        phoenix_write_error=phoenix_write_error,
    )
    if args.sync_only:
        _write_summary(output_path, dataset_summary)
        print(json.dumps(dataset_summary, indent=2, default=str))
        return 2 if phoenix_write_error else 0

    markets = _load_markets(markets_path)
    rows = _run_current_policy_rows(
        cases=cases,
        expected_by_case=expected_by_case,
        markets=markets,
    )
    experiment_name = args.experiment_name or f"current-policy-{eval_pack}-{_short_commit_sha()}"
    experiment_id = None
    experiment_url = None
    experiment_error = None

    if not dry_run and dataset is not None:
        try:
            experiment = _run_phoenix_experiment(
                dataset=dataset,
                rows=rows,
                experiment_name=experiment_name,
                eval_pack=eval_pack,
            )
            experiment_id = experiment["experiment_id"]
            experiment_url = experiment.get("experiment_url")
        except Exception as exc:  # pragma: no cover - depends on Phoenix service state
            experiment_error = f"{type(exc).__name__}: {exc}"

    summary = _experiment_summary(
        dataset_summary=dataset_summary,
        rows=rows,
        eval_pack=eval_pack,
        experiment_name=experiment_name,
        experiment_id=experiment_id,
        experiment_url=experiment_url,
        experiment_error=experiment_error,
    )
    _write_summary(output_path, summary)
    print(json.dumps(summary, indent=2, default=str))
    if experiment_error:
        return 2
    return 0 if summary["status"] == "passed" else 1


def _dataset_example(
    case: dict[str, Any],
    expected: dict[str, Any],
    eval_pack: str,
) -> dict[str, Any]:
    gold = expected["expected_fit"]
    return {
        "input": {
            "case_id": case["example_id"],
            "source_text": case["source_text"],
            "source_type": case.get("source_type"),
            "source_name": case.get("source_provenance", {}).get("source_name"),
            "source_url": case.get("source_provenance", {}).get("source_url"),
        },
        "output": {
            "expected_fit_class": gold["semantic_fit_class"],
            "expected_best_market_id": gold["best_market_id"],
            "acceptable_market_ids": gold["acceptable_market_ids"],
            "adjacent_market_ids": gold["adjacent_market_ids"],
            "minimum_expected_behavior": gold.get("minimum_expected_behavior", ""),
        },
        "metadata": {
            "eval_pack": eval_pack,
            "schema_version": case["schema_version"],
            "as_of_ts": case.get("as_of_ts"),
            "topic": case.get("labels", {}).get("topic"),
            "difficulty": case.get("labels", {}).get("difficulty"),
            "market_snapshot_build_id": case["market_snapshot_ref"]["build_id"],
            "market_rules_snapshot_build_id": case["market_rules_snapshot_ref"][
                "build_id"
            ],
            "source_actor": case.get("source_signal", {}).get("source_actor"),
            "source_actor_type": case.get("source_signal", {}).get(
                "source_actor_type"
            ),
            "expected_case_tags": gold.get("case_tags", []),
            "strict_eval_truth_source": "repo_fixtures",
        },
    }


def _create_phoenix_dataset(
    dataset_name: str,
    examples: list[dict[str, Any]],
    eval_pack: str,
) -> Any:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    return client.datasets.create_dataset(
        name=dataset_name,
        examples=examples,
        dataset_description=(
            f"{eval_pack} promoted frozen goldens mirrored from local fixtures. "
            "Repo fixtures remain canonical eval truth; Phoenix is used for "
            "comparison and inspection."
        ),
        timeout=60,
    )


def _run_current_policy_rows(
    *,
    cases: list[dict[str, Any]],
    expected_by_case: dict[str, dict[str, Any]],
    markets: list[CandidateMarket],
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        expected = expected_by_case[case["example_id"]]["expected_fit"]
        prompt_version = (
            "v2_trace_inspected"
            if expected["semantic_fit_class"] == FitClass.WEAK_PROXY.value
            else "v1_lenient"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LedgerStore(Path(tmpdir) / "ledger.json")
            agent = MarketFitTraceAgent(
                store=store,
                adk_runtime=OfflineADKRuntime(),
                markets=markets,
            )
            result = asyncio.run(
                agent.run(
                    thesis=case["source_text"],
                    title=case.get("source_provenance", {}).get("source_name"),
                    prompt_version=prompt_version,
                )
            )
        row = {
            "case_id": case["example_id"],
            "expected_fit_class": expected["semantic_fit_class"],
            "actual_fit_class": result.fit.semantic_fit_class.value,
            "expected_best_market_id": expected["best_market_id"],
            "actual_market_id": result.fit.recommended_market_id,
            "acceptable_market_ids": expected["acceptable_market_ids"],
            "adjacent_market_ids": expected["adjacent_market_ids"],
            "false_strong_recommendation": (
                result.eval.metrics.false_strong_recommendation
            ),
            "weak_proxy_detected": result.eval.metrics.weak_proxy_detected,
            "unsupported_implication": result.eval.metrics.unsupported_implication,
            "failure_summary": result.eval.failure_summary,
            "trace_id": result.phoenix_trace_id,
            "trace_url": result.phoenix_trace_url,
            "phoenix_trace_url": result.phoenix_trace_url,
            "eval_link": result.phoenix_trace_url,
        }
        _score_row(row)
        rows.append(row)
    return rows


def _run_phoenix_experiment(
    *,
    dataset: Any,
    rows: list[dict[str, Any]],
    experiment_name: str,
    eval_pack: str,
) -> dict[str, Any]:
    from phoenix.client import Client

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    rows_by_case = {row["case_id"]: row for row in rows}

    def task(input: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        _ = expected
        return rows_by_case[input["case_id"]]

    ran = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators={
            "fit_class_match": _fit_class_match,
            "market_id_match": _market_id_match,
            "fit_eval_metrics_pass": _fit_eval_metrics_pass,
        },
        experiment_name=experiment_name,
        experiment_description=(
            "Current deterministic Market Fit Trace Agent policy compared against "
            f"{eval_pack} expected labels."
        ),
        experiment_metadata={
            "eval_pack": eval_pack,
            "commit_sha": _commit_sha(),
            "strict_fixture_source": True,
            "market_data_mode": "fixture",
            "adk_runtime": "offline-golden-eval",
            "llm_as_judge": False,
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


def _fit_eval_metrics_pass(
    output: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    passed = bool(
        not output["false_strong_recommendation"]
        and not output["unsupported_implication"]
        and (
            expected["expected_fit_class"] != FitClass.WEAK_PROXY.value
            or output["weak_proxy_detected"]
        )
    )
    return {
        "label": "pass" if passed else "fail",
        "score": 1.0 if passed else 0.0,
        "explanation": (
            "false_strong="
            f"{output['false_strong_recommendation']} weak_proxy_detected="
            f"{output['weak_proxy_detected']} unsupported_implication="
            f"{output['unsupported_implication']}"
        ),
    }


def _dataset_sync_summary(
    *,
    dataset: Any | None,
    dataset_name: str,
    examples: list[dict[str, Any]],
    eval_pack: str,
    dry_run: bool,
    missing_config: list[str],
    phoenix_write_error: str | None,
) -> dict[str, Any]:
    dataset_url = (
        f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
        if dataset is not None and settings.phoenix_base_url
        else None
    )
    rows = [
        {
            "case_id": example["input"]["case_id"],
            "expected_fit_class": example["output"]["expected_fit_class"],
            "expected_best_market_id": example["output"]["expected_best_market_id"],
            "acceptable_market_ids": example["output"]["acceptable_market_ids"],
            "adjacent_market_ids": example["output"]["adjacent_market_ids"],
            "market_snapshot_build_id": example["metadata"][
                "market_snapshot_build_id"
            ],
            "market_rules_snapshot_build_id": example["metadata"][
                "market_rules_snapshot_build_id"
            ],
        }
        for example in examples
    ]
    return {
        "status": "blocked" if phoenix_write_error else ("dry_run" if dry_run else "ok"),
        "mode": "dry_run" if dry_run else "phoenix",
        "eval_pack": eval_pack,
        "dataset_name": dataset_name,
        "dataset_id": dataset.id if dataset is not None else None,
        "dataset_version_id": dataset.version_id if dataset is not None else None,
        "dataset_url": dataset_url,
        "missing_config": missing_config,
        "phoenix_write_error": phoenix_write_error,
        "canonical_truth_source": "repo_fixtures",
        "strict_experiment_uses_live_polydata": False,
        "llm_as_judge": False,
        "promoted_expected_labels_present": True,
        "case_count": len(examples),
        "rows": rows,
    }


def _experiment_summary(
    *,
    dataset_summary: dict[str, Any],
    rows: list[dict[str, Any]],
    eval_pack: str,
    experiment_name: str,
    experiment_id: str | None,
    experiment_url: str | None,
    experiment_error: str | None,
) -> dict[str, Any]:
    passed = all(row["passed"] for row in rows)
    status = "blocked" if experiment_error else ("passed" if passed else "failed")
    metrics = _metric_summary(rows)
    return {
        "status": status,
        "mode": dataset_summary["mode"],
        "eval_pack": eval_pack,
        "dataset_name": dataset_summary["dataset_name"],
        "dataset_id": dataset_summary["dataset_id"],
        "dataset_version_id": dataset_summary["dataset_version_id"],
        "dataset_url": dataset_summary["dataset_url"],
        "experiment_name": experiment_name,
        "experiment_id": experiment_id,
        "experiment_url": experiment_url,
        "experiment_error": experiment_error,
        "missing_config": dataset_summary["missing_config"],
        "commit_sha": _commit_sha(),
        "canonical_truth_source": "repo_fixtures",
        "market_data_mode": "fixture",
        "strict_experiment_uses_live_polydata": False,
        "llm_as_judge": False,
        "case_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"]),
        "metrics": metrics,
        "rows": rows,
    }


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    no_clean_rows = [
        row for row in rows if row["expected_fit_class"] == FitClass.NO_CLEAN_EXPRESSION.value
    ]
    no_clean_false_positives = [
        row for row in no_clean_rows if row["no_clean_expression_false_positive"]
    ]
    return {
        "fit_class_accuracy": _mean(row["fit_class_passed"] for row in rows),
        "market_id_exact_match_rate": _mean(
            row["exact_market_id_match"] for row in rows
        ),
        "acceptable_market_match_rate": _mean(row["market_id_passed"] for row in rows),
        "market_id_accuracy": _mean(row["market_id_passed"] for row in rows),
        "false_strong_recommendation_rate": _mean(
            row["false_strong_recommendation"] for row in rows
        ),
        "weak_proxy_detected_rate": _mean(row["weak_proxy_detected"] for row in rows),
        "unsupported_implication_rate": _mean(
            row["unsupported_implication"] for row in rows
        ),
        "eval_metrics_pass_rate": _mean(row["eval_metrics_passed"] for row in rows),
        "no_clean_expression": {
            "expected_count": len(no_clean_rows),
            "false_positive_count": len(no_clean_false_positives),
            "false_positive_rate": (
                len(no_clean_false_positives) / len(no_clean_rows)
                if no_clean_rows
                else 0.0
            ),
            "false_positive_case_ids": [
                row["case_id"] for row in no_clean_false_positives
            ],
        },
    }


def _score_row(row: dict[str, Any]) -> None:
    row["fit_class_passed"] = row["expected_fit_class"] == row["actual_fit_class"]
    row["exact_market_id_match"] = (
        row["actual_market_id"] == row["expected_best_market_id"]
    )
    row["market_id_passed"] = _market_id_passed(row)
    row["no_clean_expression_false_positive"] = bool(
        row["expected_fit_class"] == FitClass.NO_CLEAN_EXPRESSION.value
        and (
            row["actual_fit_class"] != FitClass.NO_CLEAN_EXPRESSION.value
            or row["actual_market_id"] is not None
        )
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
        and row["eval_metrics_passed"]
        and not row["no_clean_expression_false_positive"]
    )


def _market_id_passed(row: dict[str, Any]) -> bool:
    expected_class = row["expected_fit_class"]
    actual = row["actual_market_id"]
    best = row["expected_best_market_id"]
    acceptable = set(row["acceptable_market_ids"])
    adjacent = set(row["adjacent_market_ids"])
    if expected_class == FitClass.NO_CLEAN_EXPRESSION.value:
        return actual is None
    if expected_class == FitClass.WEAK_PROXY.value:
        return actual is None or actual == best or actual in acceptable or actual in adjacent
    return actual == best or actual in acceptable


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_markets(path: Path) -> list[CandidateMarket]:
    markets: list[CandidateMarket] = []
    for item in _read_jsonl(path):
        close_time = item.get("close_time") or ""
        markets.append(
            CandidateMarket(
                market_id=item["market_id"],
                title=item["title"],
                venue=item["venue"],
                description=item.get("description", ""),
                resolution_rules=item.get("resolution_rules", ""),
                close_date=close_time.split("T")[0] if close_time else "unspecified",
                outcomes=["Yes", "No"],
                current_probability=item.get("yes_price"),
                known_fit_risks=MARKET_FIT_RISKS.get(item["market_id"], []),
                entity_tags=item.get("tags", []),
            )
        )
    return markets


def _output_path(args: argparse.Namespace, cases_path: Path) -> Path:
    if args.output:
        return Path(args.output)
    filename = (
        "phoenix_promoted_goldens_dataset_result.json"
        if args.sync_only
        else "phoenix_experiment_result.json"
    )
    return cases_path.parent / filename


def _pack_suffix(eval_pack: str) -> str:
    match = re.search(r"(v\d+)", eval_pack)
    return match.group(1) if match else re.sub(r"[^a-zA-Z0-9_]+", "_", eval_pack)


def _mean(values: Any) -> float:
    items = [bool(value) for value in values]
    if not items:
        return 0.0
    return sum(1 for item in items if item) / len(items)


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")


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
