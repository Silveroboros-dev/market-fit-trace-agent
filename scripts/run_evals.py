from __future__ import annotations

# ruff: noqa: E402, I001

import asyncio
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from app.market_data import load_markets
from app.models import CandidateMarket, FitClass


V1_CASES = Path("evals/market_fit_v1/examples.jsonl")
V1_EXPECTED = Path("evals/market_fit_v1/expected_outputs.jsonl")
V1_MARKETS = Path("evals/market_fit_v1/market_snapshots.jsonl")

MARKET_FIT_RISKS = {
    "polymarket_best_ai_model_google_end_june_2026": [
        "weak_proxy_for_causal_tpu_claim",
        "leaderboard_rank_can_move_for_reasons_unrelated_to_hardware",
    ],
    "polymarket_ai_wins_imo_gold_2026": [
        "wrong_market_for_general_research_agent_product",
        "indirect_for_putnam_to_imo_transfer_claim",
        "benchmark_market_not_same_as_source_claim",
    ],
    "polymarket_anthropic_no_ipo_june_30_2026": [
        "weak_proxy_for_valuation_driven_ipo_momentum",
        "ipo_timing_not_same_as_private_valuation_signal",
    ],
    "pm_amazon_2026_capex_above": [
        "weak_proxy_for_aggregate_ai_vc_capex_roi_claim",
        "single_hyperscaler_capex_not_same_as_global_vc_or_roi",
    ],
    "pm_30y_mortgage_rate_hit_2026": [
        "weak_proxy_for_home_overpricing_claim",
        "rate_threshold_not_same_as_housing_valuation_metric",
    ],
}


class OfflineADKRuntime:
    runtime_name = "offline-golden-eval"

    async def generate_json(self, **_kwargs: object) -> None:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run golden market-fit eval cases through MarketFitTraceAgent."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use configured Google ADK/Gemini and Phoenix tracing.",
    )
    parser.add_argument(
        "--cases",
        default=str(V1_CASES),
        help="Path to golden eval fixture JSON.",
    )
    parser.add_argument(
        "--expected",
        default=str(V1_EXPECTED),
        help="Path to market_fit_v1 expected outputs JSONL.",
    )
    parser.add_argument(
        "--markets",
        default=str(V1_MARKETS),
        help="Path to market_fit_v1 market snapshots JSONL.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help=(
            "Print failed eval rows but exit 0. Intended for candidate packs that are "
            "not default CI goldens yet."
        ),
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if Path(args.cases).suffix == ".jsonl":
        return await run_market_fit_v1(args)
    return await run_legacy_seed_cases(args)


async def run_legacy_seed_cases(args: argparse.Namespace) -> int:
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LedgerStore(Path(tmpdir) / "ledger.json")
        runtime = None if args.live else OfflineADKRuntime()
        agent = MarketFitTraceAgent(store=store, adk_runtime=runtime, markets=load_markets())
        rows: list[dict[str, Any]] = []
        for case in cases:
            prompt_version = (
                "v2_trace_inspected"
                if case["expected_fit_class"] == FitClass.WEAK_PROXY.value
                else "v1_lenient"
            )
            result = await agent.run(thesis=case["thesis"], prompt_version=prompt_version)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "expected_fit_class": case["expected_fit_class"],
                    "actual_fit_class": result.fit.semantic_fit_class.value,
                    "expected_market_id": case["expected_market_id"],
                    "actual_market_id": result.fit.recommended_market_id,
                    "false_strong_recommendation": result.eval.metrics.false_strong_recommendation,
                    "weak_proxy_detected": result.eval.metrics.weak_proxy_detected,
                    "failure_summary": result.eval.failure_summary,
                    "trace_id": result.phoenix_trace_id,
                    "phoenix_trace_url": _trace_url(result.phoenix_trace_id),
                }
            )
        passed = _passed(rows)
        print(
            json.dumps(
                {
                    "status": "passed" if passed else "failed",
                    "mode": "live" if args.live else "offline",
                    "case_count": len(rows),
                    "passed_count": sum(1 for row in rows if row["passed"]),
                    "rows": rows,
                },
                indent=2,
            )
        )
        return _exit_code(passed, args)


async def run_market_fit_v1(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    examples = _read_jsonl(cases_path)
    expected = {item["example_id"]: item for item in _read_jsonl(Path(args.expected))}
    markets = _load_v1_markets(Path(args.markets))
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LedgerStore(Path(tmpdir) / "ledger.json")
        runtime = None if args.live else OfflineADKRuntime()
        agent = MarketFitTraceAgent(store=store, adk_runtime=runtime, markets=markets)
        for example in examples:
            case_id = example["example_id"]
            gold = expected[case_id]["expected_fit"]
            prompt_version = (
                "v2_trace_inspected"
                if gold["semantic_fit_class"] == FitClass.WEAK_PROXY.value
                else "v1_lenient"
            )
            result = await agent.run(
                thesis=example["source_text"],
                title=example["source_provenance"].get("source_name"),
                prompt_version=prompt_version,
            )
            rows.append(
                {
                    "case_id": case_id,
                    "expected_fit_class": gold["semantic_fit_class"],
                    "actual_fit_class": result.fit.semantic_fit_class.value,
                    "expected_best_market_id": gold["best_market_id"],
                    "actual_market_id": result.fit.recommended_market_id,
                    "acceptable_market_ids": gold["acceptable_market_ids"],
                    "adjacent_market_ids": gold["adjacent_market_ids"],
                    "false_strong_recommendation": (
                        result.eval.metrics.false_strong_recommendation
                    ),
                    "weak_proxy_detected": result.eval.metrics.weak_proxy_detected,
                    "failure_summary": result.eval.failure_summary,
                    "trace_id": result.phoenix_trace_id,
                    "phoenix_trace_url": result.phoenix_trace_url,
                }
            )
    passed = _passed_v1(rows)
    print(
        json.dumps(
            {
                "status": "passed" if passed else "failed",
                "mode": "live" if args.live else "offline",
                "eval_pack": cases_path.parent.name,
                "allow_failures": args.allow_failures,
                "case_count": len(rows),
                "passed_count": sum(1 for row in rows if row["passed"]),
                "rows": rows,
            },
            indent=2,
        )
    )
    return _exit_code(passed, args)


def _exit_code(passed: bool, args: argparse.Namespace) -> int:
    return 0 if passed or args.allow_failures else 1


def _passed(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        row["fit_class_passed"] = row["expected_fit_class"] == row["actual_fit_class"]
        row["market_id_passed"] = row["expected_market_id"] == row["actual_market_id"]
        row["passed"] = bool(row["fit_class_passed"] and row["market_id_passed"])
    return all(bool(row["passed"]) for row in rows)


def _passed_v1(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
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
    return all(bool(row["passed"]) for row in rows)


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


def _trace_url(trace_id: str) -> str | None:
    base_url = os.getenv("PHOENIX_BASE_URL")
    if not base_url or trace_id.startswith("local-"):
        return None
    return f"{base_url.rstrip('/')}/traces/{trace_id}"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
