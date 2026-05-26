from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.client import Client

from app.agent import MarketFitTraceAgent
from app.config import settings
from app.ledger import LedgerStore
from app.models import CandidateMarket, FitClass
from scripts.run_evals import MARKET_FIT_RISKS, OfflineADKRuntime

V1_CASES = Path("evals/market_fit_v1/examples.jsonl")
V1_EXPECTED = Path("evals/market_fit_v1/expected_outputs.jsonl")
V1_MARKETS = Path("evals/market_fit_v1/market_snapshots.jsonl")
DEFAULT_OUTPUT = Path("evals/market_fit_v1/phoenix_experiment_result.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export market_fit_v1 to a Phoenix Dataset and run a small Phoenix "
            "Experiment comparing current policy output against expected labels."
        )
    )
    parser.add_argument("--cases", default=str(V1_CASES))
    parser.add_argument("--expected", default=str(V1_EXPECTED))
    parser.add_argument("--markets", default=str(V1_MARKETS))
    parser.add_argument("--dataset-name", default="market_fit_v1_policy_eval")
    parser.add_argument("--experiment-name", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
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

    cases = _read_jsonl(Path(args.cases))
    if args.limit > 0:
        cases = cases[: args.limit]
    expected = {item["example_id"]: item for item in _read_jsonl(Path(args.expected))}
    markets = _load_v1_markets(Path(args.markets))
    examples = [_dataset_example(case, expected[case["example_id"]]) for case in cases]

    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    dataset = client.datasets.create_dataset(
        name=args.dataset_name,
        examples=examples,
        dataset_description=(
            "market_fit_v1 promoted golden cases mirrored from local frozen fixtures. "
            "Strict eval truth remains local; this dataset is for Phoenix experiment comparison."
        ),
        timeout=60,
    )

    rows: list[dict[str, Any]] = []
    rows_lock = Lock()

    def run_current_policy(input: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        prompt_version = (
            "v2_trace_inspected"
            if expected["expected_fit_class"] == FitClass.WEAK_PROXY.value
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
                    thesis=input["source_text"],
                    title=input.get("source_name"),
                    prompt_version=prompt_version,
                )
            )
        row = {
            "case_id": input["case_id"],
            "expected_fit_class": expected["expected_fit_class"],
            "actual_fit_class": result.fit.semantic_fit_class.value,
            "expected_best_market_id": expected["expected_best_market_id"],
            "actual_market_id": result.fit.recommended_market_id,
            "acceptable_market_ids": expected["acceptable_market_ids"],
            "adjacent_market_ids": expected["adjacent_market_ids"],
            "false_strong_recommendation": result.eval.metrics.false_strong_recommendation,
            "weak_proxy_detected": result.eval.metrics.weak_proxy_detected,
            "unsupported_implication": result.eval.metrics.unsupported_implication,
            "failure_summary": result.eval.failure_summary,
            "trace_id": result.phoenix_trace_id,
            "trace_url": result.phoenix_trace_url,
        }
        row["fit_class_passed"] = row["expected_fit_class"] == row["actual_fit_class"]
        row["market_id_passed"] = _market_id_passed(row)
        row["eval_metrics_passed"] = bool(
            not row["false_strong_recommendation"]
            and (
                row["expected_fit_class"] != FitClass.WEAK_PROXY.value
                or row["weak_proxy_detected"]
            )
        )
        row["passed"] = bool(
            row["fit_class_passed"]
            and row["market_id_passed"]
            and row["eval_metrics_passed"]
        )
        with rows_lock:
            rows.append(row)
        return row

    def fit_class_match(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        passed = output["actual_fit_class"] == expected["expected_fit_class"]
        return {
            "label": "pass" if passed else "fail",
            "score": 1.0 if passed else 0.0,
            "explanation": (
                f"expected={expected['expected_fit_class']} actual={output['actual_fit_class']}"
            ),
        }

    def market_id_match(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
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

    def fit_eval_metrics_pass(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        passed = bool(
            not output["false_strong_recommendation"]
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
                f"{output['weak_proxy_detected']}"
            ),
        }

    experiment_name = args.experiment_name or f"current-policy-{_short_commit_sha()}"
    ran = client.experiments.run_experiment(
        dataset=dataset,
        task=run_current_policy,
        evaluators={
            "fit_class_match": fit_class_match,
            "market_id_match": market_id_match,
            "fit_eval_metrics_pass": fit_eval_metrics_pass,
        },
        experiment_name=experiment_name,
        experiment_description=(
            "Current deterministic Market Fit Trace Agent policy compared against "
            "market_fit_v1 expected labels."
        ),
        experiment_metadata={
            "eval_pack": "market_fit_v1",
            "commit_sha": _commit_sha(),
            "strict_fixture_source": True,
            "adk_runtime": "offline-golden-eval",
        },
        dry_run=args.dry_run,
        print_summary=True,
        timeout=120,
    )

    rows_by_case = {row["case_id"]: row for row in rows}
    ordered_rows = [
        rows_by_case[case["example_id"]]
        for case in cases
        if case["example_id"] in rows_by_case
    ]
    dataset_url = f"{settings.phoenix_base_url.rstrip('/')}/datasets/{dataset.id}"
    experiment_id = ran["experiment_id"]
    experiment_url = None
    if experiment_id != "DRY_RUN":
        experiment_url = client.experiments.get_experiment_url(
            dataset_id=dataset.id,
            experiment_id=experiment_id,
        )
    summary = {
        "status": "passed" if all(row["passed"] for row in ordered_rows) else "failed",
        "mode": "dry_run" if args.dry_run else "phoenix",
        "dataset_name": dataset.name,
        "dataset_id": dataset.id,
        "dataset_version_id": dataset.version_id,
        "dataset_url": dataset_url,
        "experiment_name": experiment_name,
        "experiment_id": experiment_id,
        "experiment_url": experiment_url,
        "commit_sha": _commit_sha(),
        "case_count": len(ordered_rows),
        "passed_count": sum(1 for row in ordered_rows if row["passed"]),
        "metrics": {
            "fit_class_accuracy": _mean(row["fit_class_passed"] for row in ordered_rows),
            "market_id_accuracy": _mean(row["market_id_passed"] for row in ordered_rows),
            "eval_metrics_pass_rate": _mean(row["eval_metrics_passed"] for row in ordered_rows),
        },
        "rows": ordered_rows,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["status"] == "passed" else 1


def _dataset_example(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    gold = expected["expected_fit"]
    return {
        "input": {
            "case_id": case["example_id"],
            "source_text": case["source_text"],
            "source_name": case["source_provenance"].get("source_name"),
            "source_url": case["source_provenance"].get("source_url"),
        },
        "output": {
            "expected_fit_class": gold["semantic_fit_class"],
            "expected_best_market_id": gold["best_market_id"],
            "acceptable_market_ids": gold["acceptable_market_ids"],
            "adjacent_market_ids": gold["adjacent_market_ids"],
        },
        "metadata": {
            "schema_version": case["schema_version"],
            "topic": case.get("labels", {}).get("topic"),
            "difficulty": case.get("labels", {}).get("difficulty"),
            "market_snapshot_build_id": case["market_snapshot_ref"]["build_id"],
            "market_rules_snapshot_build_id": case["market_rules_snapshot_ref"]["build_id"],
            "source_actor": case.get("source_signal", {}).get("source_actor"),
            "source_actor_type": case.get("source_signal", {}).get("source_actor_type"),
            "expected_case_tags": gold.get("case_tags", []),
            "minimum_expected_behavior": gold.get("minimum_expected_behavior", ""),
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_v1_markets(path: Path) -> list[CandidateMarket]:
    markets: list[CandidateMarket] = []
    for item in _read_jsonl(path):
        close_time = item.get("close_time") or ""
        markets.append(
            CandidateMarket(
                market_id=item["market_id"],
                title=item["title"],
                venue=item["venue"],
                description=item["description"],
                resolution_rules=item["resolution_rules"],
                close_date=close_time.split("T")[0] if close_time else "unspecified",
                outcomes=["Yes", "No"],
                current_probability=item.get("yes_price"),
                known_fit_risks=MARKET_FIT_RISKS.get(item["market_id"], []),
                entity_tags=item.get("tags", []),
            )
        )
    return markets


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
