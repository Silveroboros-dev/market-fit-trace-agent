from __future__ import annotations

# ruff: noqa: E402
import argparse
import asyncio
import json
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import MarketFitTraceAgent
from app.config import settings
from app.ledger import LedgerStore
from app.models import CandidateMarket

PACK_DIR = ROOT / "evals" / "trace_repair_v1"
RESULT_PATH = PACK_DIR / "run_results" / "trace_repair_result.json"
REQUIRED_TRACE_SIGNALS = (
    "false_strong_recommendation",
    "causal_mechanism_mismatch",
    "resolution_target_mismatch",
    "trace_repair_candidate",
)
FIRST_TRACE_EXPECTED_ANNOTATION_LABELS = {
    "false_strong_recommendation": "fail",
    "causal_mechanism_mismatch": "true",
    "resolution_target_mismatch": "true",
    "trace_repair_candidate": "true",
    "trace_repair_gate_applied": "false",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Phoenix-MCP-gated trace-repair proof pack."
    )
    parser.add_argument("--case-id", default="trace_repair_tpu_frontier_gap_001")
    parser.add_argument("--trace-wait-seconds", type=int, default=45)
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    config_error = _config_error()
    if config_error:
        _write_result(config_error)
        print(json.dumps(config_error, indent=2))
        return 2

    cases = {item["case_id"]: item for item in _read_jsonl(PACK_DIR / "cases.jsonl")}
    expected = {
        item["case_id"]: item
        for item in _read_jsonl(PACK_DIR / "expected_transitions.jsonl")
    }
    case = cases[args.case_id]
    transition = expected[args.case_id]
    markets = [
        CandidateMarket.model_validate(item)
        for item in _read_jsonl(PACK_DIR / "market_snapshots.jsonl")
        if item["market_id"] in set(case["candidate_market_ids"])
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        store = LedgerStore(Path(tmpdir) / "ledger.json")
        agent = MarketFitTraceAgent(store=store, markets=markets)

        first = await agent.run(
            thesis=case["source_text"],
            title=case["source_provenance"]["source_name"],
            prompt_version=transition["first_run_expected"]["prompt_version"],
        )
        first_check = _check_first_run(first, transition)
        trace_check = _wait_for_trace_context(
            first.phoenix_trace_id,
            timeout_seconds=args.trace_wait_seconds,
        )
        improved = await agent.improve_from_trace(first.run_id)
        second_check = _check_second_run(improved, transition)

    passed = bool(first_check["passed"] and trace_check["passed"] and second_check["passed"])
    result = {
        "status": "passed" if passed else "failed",
        "eval_pack": "trace_repair_v1",
        "case_id": args.case_id,
        "first_run": first_check,
        "phoenix_trace": trace_check,
        "improvement": second_check,
        "before_run_id": improved.before_run_id,
        "after_run_id": improved.after_run_id,
        "before_trace_id": improved.before_trace_id,
        "after_trace_id": improved.after_trace_id,
        "inspection_source": improved.inspection_source,
        "fallback_used": improved.fallback_used,
        "result_path": str(RESULT_PATH.relative_to(ROOT)),
    }
    _write_result(result)
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


def _config_error() -> dict[str, Any] | None:
    missing: list[str] = []
    if not settings.phoenix_base_url:
        missing.append("PHOENIX_BASE_URL")
    if not settings.phoenix_api_key:
        missing.append("PHOENIX_API_KEY")
    if not settings.phoenix_mcp_enabled:
        missing.append("PHOENIX_MCP_ENABLED=true")
    if missing:
        return {
            "status": "missing_config",
            "message": (
                "trace-repair requires real Phoenix MCP inspection; local fallback is "
                "not accepted for this proof."
            ),
            "missing": missing,
        }
    return None


def _check_first_run(first: Any, transition: dict[str, Any]) -> dict[str, Any]:
    expected = transition["first_run_expected"]
    metrics = first.eval.metrics
    checks = {
        "prompt_version": first.prompt_version == expected["prompt_version"],
        "fit_class": first.fit.semantic_fit_class.value == expected["fit_class"],
        "recommended_market_id": (
            first.fit.recommended_market_id == expected["recommended_market_id"]
        ),
        "false_strong_recommendation": (
            metrics.false_strong_recommendation
            is expected["false_strong_recommendation"]
        ),
        "causal_mechanism_mismatch": (
            metrics.causal_mechanism_mismatch is expected["causal_mechanism_mismatch"]
        ),
        "resolution_target_mismatch": (
            metrics.resolution_target_mismatch
            is expected["resolution_target_mismatch"]
        ),
        "trace_repair_candidate": (
            metrics.trace_repair_candidate is expected["trace_repair_candidate"]
        ),
        "phoenix_trace_id_nonlocal": not first.phoenix_trace_id.startswith("local-"),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "run_id": first.run_id,
        "trace_id": first.phoenix_trace_id,
        "failure_summary": first.eval.failure_summary,
    }


def _check_second_run(improved: Any, transition: dict[str, Any]) -> dict[str, Any]:
    expected = transition["second_run_expected"]
    inspection_expected = transition["inspection_expected"]
    metrics = improved.after.eval.metrics
    ledger_events = [event.event_type for event in improved.after.ledger.events]
    checks = {
        "inspection_source": improved.inspection_source
        == inspection_expected["inspection_source"],
        "fallback_used_is_false": improved.fallback_used
        is inspection_expected["fallback_used"],
        "prompt_version": improved.after.prompt_version == expected["prompt_version"],
        "fit_class": improved.after.fit.semantic_fit_class.value == expected["fit_class"],
        "recommended_market_id": (
            improved.after.fit.recommended_market_id == expected["recommended_market_id"]
        ),
        "false_strong_recommendation": (
            metrics.false_strong_recommendation
            is expected["false_strong_recommendation"]
        ),
        "weak_proxy_detected": metrics.weak_proxy_detected
        is expected["weak_proxy_detected"],
        "trace_repair_gate_applied": (
            metrics.trace_repair_gate_applied is expected["trace_repair_gate_applied"]
        ),
        "previous_trace_id_recorded": metrics.previous_trace_id == improved.before_trace_id,
        "ledger_gate_event": "trace_repair_gate_applied" in ledger_events,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "inspection_summary": improved.inspection.summary,
        "after_fit_reason": improved.after.fit.fit_reason,
    }


def _wait_for_trace_context(trace_id: str, *, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _check_trace_context(trace_id)
        if last["passed"]:
            return last
        time.sleep(2)
    return last or {"passed": False, "trace_id": trace_id, "error": "trace_not_checked"}


def _check_trace_context(trace_id: str) -> dict[str, Any]:
    try:
        project = urllib.parse.quote(settings.phoenix_project_name, safe="")
        traces = _request(
            "GET",
            f"/v1/projects/{project}/traces?limit=20&include_spans=true",
        ).get("data", [])
        trace = next((item for item in traces if item.get("trace_id") == trace_id), None)
        if not trace:
            return {
                "passed": False,
                "trace_id": trace_id,
                "error": "trace_not_found",
                "recent_trace_ids": [item.get("trace_id") for item in traces],
            }
        spans = trace.get("spans", [])
        fit_span = next((span for span in spans if span.get("name") == "fit_eval_run"), None)
        if not fit_span:
            return {
                "passed": False,
                "trace_id": trace_id,
                "error": "fit_eval_run_missing",
                "span_names": [span.get("name") for span in spans],
            }
        annotations = _request(
            "GET",
            f"/v1/projects/{project}/span_annotations?span_ids={fit_span['span_id']}&limit=100",
        ).get("data", [])
        annotation_names = {item.get("name") for item in annotations}
        annotation_values = {
            item.get("name"): _annotation_label(item) for item in annotations
        }
        missing = [
            signal for signal in REQUIRED_TRACE_SIGNALS if signal not in annotation_names
        ]
        mismatched_values = {
            name: {"expected": expected, "actual": annotation_values.get(name)}
            for name, expected in FIRST_TRACE_EXPECTED_ANNOTATION_LABELS.items()
            if annotation_values.get(name) != expected
        }
        return {
            "passed": not missing and not mismatched_values,
            "trace_id": trace_id,
            "fit_eval_span_id": fit_span["span_id"],
            "required_signals_found": [
                signal for signal in REQUIRED_TRACE_SIGNALS if signal in annotation_names
            ],
            "required_signals_missing": missing,
            "expected_annotation_values": FIRST_TRACE_EXPECTED_ANNOTATION_LABELS,
            "actual_annotation_values": {
                name: annotation_values.get(name)
                for name in FIRST_TRACE_EXPECTED_ANNOTATION_LABELS
            },
            "mismatched_annotation_values": mismatched_values,
        }
    except Exception as exc:
        return {"passed": False, "trace_id": trace_id, "error": str(exc)}


def _annotation_label(annotation: dict[str, Any]) -> str | None:
    result = annotation.get("result")
    if isinstance(result, dict):
        label = result.get("label")
        return str(label) if label is not None else None
    return None


def _request(method: str, path: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{settings.phoenix_base_url.rstrip('/')}{path}",
        headers={
            "Authorization": f"Bearer {settings.phoenix_api_key}",
            "Accept": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_result(result: dict[str, Any]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
