"""Run Gemini/ADK against the stress-40 synthetic dataset.

Reads evals/stress_test_v1/stress_cases.jsonl, runs each case through
MarketFitTraceAgent with a StaticMarketProvider wrapping the single synthetic
market, compares observed fit class to the constructed expected label, and
exports mismatches as failure eval candidates.

Requires GOOGLE_API_KEY or Vertex AI configured.

Usage:
    python scripts/run_stress_gemini_eval.py
    # or: make run-stress-40
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.ledger import LedgerStore  # noqa: E402
from app.market_provider import StaticMarketProvider  # noqa: E402
from app.models import CandidateMarket  # noqa: E402
from app.workflow import MarketFitTraceAgent  # noqa: E402

INPUT_FILE = Path("evals/stress_test_v1/stress_cases.jsonl")
OUTPUT_DIR = Path("evals/stress_test_v1")
RESULTS_FILE = OUTPUT_DIR / "stress_results.jsonl"
SUMMARY_FILE = OUTPUT_DIR / "stress_summary.json"
FAILURE_OUT_DIR = Path("evals/failure_candidates")
STRESS_FAILURE_SCHEMA_VERSION = "stress_gemini_failure_candidate_v0"
POLICY_PROPOSAL_VERSION = "policy_pr_candidate_v0"
FIT_CLASS_VALUES = {"direct", "indirect", "weak_proxy", "no_clean_expression"}
FIT_CLASS_KEYS = (
    "semantic_fit_class",
    "fit_class",
    "proposed_fit_class",
    "market_fit_class",
)
HUMAN_REVIEW_OPTIONS = (
    "promote_to_strict_golden_candidate",
    "needs_more_rules",
    "candidate_only",
    "disregard",
)


def _load_cases() -> list[dict[str, Any]]:
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run `make build-stress-40` first.", file=sys.stderr)
        sys.exit(1)
    return [json.loads(line) for line in INPUT_FILE.read_text("utf-8").splitlines() if line.strip()]


def _market_from_case(case: dict[str, Any]) -> CandidateMarket:
    m = case["market"]
    return CandidateMarket(
        market_id=m["market_id"],
        title=m["title"],
        venue=m.get("venue", "SyntheticStress"),
        description=m.get("description", ""),
        resolution_rules=m.get("resolution_rules", ""),
        close_date=m.get("close_date", "2026-12-31"),
        outcomes=m.get("outcomes", ["Yes", "No"]),
        current_probability=m.get("current_probability"),
        known_fit_risks=m.get("known_fit_risks", []),
        entity_tags=m.get("entity_tags", []),
    )


def _parse_model_fit_proposal(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict | list):
        return raw
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _extract_fit_class(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in FIT_CLASS_VALUES:
            return stripped
        for key in FIT_CLASS_KEYS:
            match = re.search(rf'"{key}"\s*:\s*"(?P<fit>[^"]+)"', stripped)
            if match and match.group("fit") in FIT_CLASS_VALUES:
                return match.group("fit")
        return None
    if isinstance(value, dict):
        for key in FIT_CLASS_KEYS:
            fit_class = _extract_fit_class(value.get(key))
            if fit_class:
                return fit_class
        for nested in value.values():
            if not isinstance(nested, dict | list):
                continue
            fit_class = _extract_fit_class(nested)
            if fit_class:
                return fit_class
        return None
    if isinstance(value, list):
        for item in value:
            fit_class = _extract_fit_class(item)
            if fit_class:
                return fit_class
    return None


def _model_fit_from_run(store: LedgerStore, run_id: str) -> tuple[str | None, Any, str | None]:
    run = store.get_run(run_id)
    raw = run.get("model_fit_proposal_json")
    parsed = _parse_model_fit_proposal(raw)
    return raw, parsed, _extract_fit_class(parsed)


async def _run_case(case: dict[str, Any], case_index: int, total: int) -> dict[str, Any]:
    case_id = case["case_id"]
    expected = case["expected_fit_class"]
    market = _market_from_case(case)

    store = LedgerStore(path=Path(f".local/stress_ledger_{case_id}.json"))
    agent = MarketFitTraceAgent(
        store=store,
        market_provider=StaticMarketProvider(markets=[market], name="synthetic_stress"),
    )

    print(f"  [{case_index + 1}/{total}] {case_id} ... ", end="", flush=True)
    try:
        result = await agent.run(thesis=case["thesis"], prompt_version="v1_lenient")
        run_id = result.run_id
        proposal_raw, proposal, gemini_fit_class = _model_fit_from_run(store, run_id)
        gemini_match = (
            gemini_fit_class == expected if gemini_fit_class is not None else None
        )
        deterministic_fit_class = result.fit.semantic_fit_class.value
        deterministic_match = deterministic_fit_class == expected
        if gemini_match is None:
            status = "NO_GEMINI_PROPOSAL"
        else:
            status = "MATCH" if gemini_match else "MISMATCH"
        print(
            "expected="
            f"{expected} gemini={gemini_fit_class or 'missing'} "
            f"deterministic={deterministic_fit_class} {status}"
        )

        row: dict[str, Any] = {
            "case_id": case_id,
            "expected_fit_class": expected,
            "primary_evaluation_target": "gemini_advisory_proposal",
            "observed_fit_class": gemini_fit_class,
            "match": gemini_match,
            "gemini_fit_class": gemini_fit_class,
            "gemini_match": gemini_match,
            "gemini_proposal_present": proposal is not None,
            "gemini_proposal_json": proposal_raw,
            "deterministic_fit_class": deterministic_fit_class,
            "deterministic_match": deterministic_match,
            "mismatch_family": case["mismatch_family"],
            "run_id": run_id,
            "phoenix_trace_id": result.phoenix_trace_id,
            "phoenix_trace_url": result.phoenix_trace_url,
            "recommended_market_id": result.fit.recommended_market_id,
            "fit_reason": result.fit.fit_reason,
            "failure_candidate_exported": False,
            "failure_candidate_dir": None,
            "error": None,
        }

        if gemini_match is False:
            try:
                fc_result = _export_stress_gemini_failure_candidate(case=case, row=row)
                row["failure_candidate_exported"] = True
                row["failure_candidate_dir"] = fc_result.get("candidate_dir")
            except Exception as exc:
                row["failure_candidate_exported"] = False
                row["failure_candidate_dir"] = f"export_error: {exc}"

        return row

    except Exception as exc:
        print(f"ERROR: {exc}")
        return {
            "case_id": case_id,
            "expected_fit_class": expected,
            "primary_evaluation_target": "gemini_advisory_proposal",
            "observed_fit_class": None,
            "match": None,
            "gemini_fit_class": None,
            "gemini_match": None,
            "gemini_proposal_present": False,
            "gemini_proposal_json": None,
            "deterministic_fit_class": None,
            "deterministic_match": None,
            "mismatch_family": case["mismatch_family"],
            "run_id": None,
            "phoenix_trace_id": None,
            "phoenix_trace_url": None,
            "recommended_market_id": None,
            "fit_reason": None,
            "failure_candidate_exported": False,
            "failure_candidate_dir": None,
            "error": str(exc),
        }
    finally:
        # Clean up per-case ledger
        try:
            store.path.unlink(missing_ok=True)
        except OSError:
            pass


def _export_stress_gemini_failure_candidate(
    *, case: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    packet = _build_stress_gemini_failure_packet(case=case, row=row)
    candidate_id = f"stress-gemini-{case['case_id']}"
    candidate_dir = FAILURE_OUT_DIR / datetime.now(UTC).date().isoformat() / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    _write_json(candidate_dir / "source.json", packet["source"])
    _write_json(candidate_dir / "failure_signal.json", packet["failure_signal"])
    _write_json(candidate_dir / "proposed_eval_case.json", packet["proposed_eval_case"])
    (candidate_dir / "policy_gap.md").write_text(
        _stress_policy_gap_markdown(packet),
        encoding="utf-8",
    )
    (candidate_dir / "PR_DESCRIPTION.md").write_text(
        _stress_pr_description_markdown(packet),
        encoding="utf-8",
    )
    (candidate_dir / "review_notes.md").write_text(
        _stress_review_notes_markdown(packet),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "schema_version": STRESS_FAILURE_SCHEMA_VERSION,
        "candidate_dir": str(candidate_dir),
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
    }


def _build_stress_gemini_failure_packet(
    *, case: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    market = case["market"]
    source = {
        "schema_version": STRESS_FAILURE_SCHEMA_VERSION,
        "case_id": case["case_id"],
        "source_type": "synthetic_stress_case",
        "source_text": case["thesis"],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "canonical_truth": False,
        "truth_scope": case["truth_scope"],
        "expected_label_source": case["expected_label_source"],
    }
    failure_signal = {
        "schema_version": STRESS_FAILURE_SCHEMA_VERSION,
        "case_id": case["case_id"],
        "run_id": row.get("run_id"),
        "phoenix_trace_id": row.get("phoenix_trace_id"),
        "phoenix_trace_url": row.get("phoenix_trace_url"),
        "triggered_metrics": ["gemini_advisory_mismatch"],
        "mismatch_family": case["mismatch_family"],
        "trap_description": case["trap_description"],
        "expected_fit_class": case["expected_fit_class"],
        "observed_gemini_fit_class": row.get("gemini_fit_class"),
        "deterministic_fit_class": row.get("deterministic_fit_class"),
        "deterministic_match": row.get("deterministic_match"),
        "observed_recommended_market_id": row.get("recommended_market_id"),
        "candidate_only": True,
    }
    proposed_eval_case = {
        "schema_version": STRESS_FAILURE_SCHEMA_VERSION,
        "policy_proposal_version": POLICY_PROPOSAL_VERSION,
        "case_id": f"stress-gemini-failure-{case['case_id']}",
        "source_kind": "synthetic_stress_gemini_failure",
        "truth_scope": case["truth_scope"],
        "canonical_truth": False,
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
        "human_review_required": True,
        "human_review_options": list(HUMAN_REVIEW_OPTIONS),
        "recommended_default_review": "needs_more_rules",
        "disregard_when": [
            "the synthetic trap is unrealistic or too leading",
            "the constructed expected label is not defensible",
            "the Gemini output is missing or malformed",
            "the deterministic policy already handles the class and no new rule is needed",
        ],
        "source_text": case["thesis"],
        "market": market,
        "expected_fit_class": case["expected_fit_class"],
        "observed_gemini_fit_class": row.get("gemini_fit_class"),
        "deterministic_fit_class": row.get("deterministic_fit_class"),
        "deterministic_match": row.get("deterministic_match"),
        "model_fit_proposal_json": row.get("gemini_proposal_json"),
        "policy_gap_summary": (
            "Gemini advisory classification disagreed with a synthetic expected label. "
            "Human review should decide whether this is a real policy blind spot, "
            "a prompt issue, or synthetic noise to disregard."
        ),
    }
    return {
        "source": source,
        "failure_signal": failure_signal,
        "proposed_eval_case": proposed_eval_case,
    }


def _stress_policy_gap_markdown(packet: dict[str, Any]) -> str:
    failure = packet["failure_signal"]
    proposed = packet["proposed_eval_case"]
    return f"""# Stress Gemini Failure Candidate

This packet is candidate-only. It does not mutate strict goldens or policy code.

## Failure Signal

- Case: `{failure["case_id"]}`
- Family: `{failure["mismatch_family"]}`
- Expected fit: `{failure["expected_fit_class"]}`
- Gemini advisory fit: `{failure["observed_gemini_fit_class"]}`
- Deterministic fit: `{failure["deterministic_fit_class"]}`
- Phoenix trace: {failure.get("phoenix_trace_url") or failure.get("phoenix_trace_id") or "n/a"}

## Human Review Outcomes

- `needs_more_rules`: treat this as a real policy/prompt gap and write a targeted rule proposal.
- `candidate_only`: keep as stress evidence, but do not promote to a strict golden.
- `promote_to_strict_golden_candidate`: only after a reviewer converts the
  synthetic setup into a defensible frozen eval case.
- `disregard`: drop as synthetic noise or an unrealistic trap.

## Proposed Gap

{proposed["policy_gap_summary"]}

Do not apply this automatically.
"""


def _stress_pr_description_markdown(packet: dict[str, Any]) -> str:
    failure = packet["failure_signal"]
    return f"""# Candidate Policy Proposal: {failure["case_id"]}

## Problem

Gemini advisory classification returned `{failure["observed_gemini_fit_class"]}`
for a case constructed as `{failure["expected_fit_class"]}`.

## Scope

- Truth scope: synthetic expected label.
- Human review required before promotion.
- Deterministic policy code is unchanged by this packet.

## Review Decision

Choose one: `needs_more_rules`, `candidate_only`,
`promote_to_strict_golden_candidate`, or `disregard`.
"""


def _stress_review_notes_markdown(packet: dict[str, Any]) -> str:
    proposed = packet["proposed_eval_case"]
    return f"""# Review Notes

Source text:

```text
{proposed["source_text"]}
```

Review checklist:

- Is the expected fit class defensible?
- Is this a realistic market-fit trap or synthetic noise?
- Should the prompt, deterministic policy, or neither change?
- If rejected, mark `disregard` and keep strict goldens untouched.
"""


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_summary(
    results: list[dict[str, Any]],
    *,
    adk_configured: bool,
    run_at_utc: str | None = None,
) -> dict[str, Any]:
    total = len(results)
    errors = [r for r in results if r["error"] is not None]
    missing_gemini = [
        r for r in results if r["error"] is None and r.get("gemini_match") is None
    ]
    gemini_matches = [
        r for r in results if r["error"] is None and r.get("gemini_match") is True
    ]
    gemini_mismatches = [
        r for r in results if r["error"] is None and r.get("gemini_match") is False
    ]
    deterministic_matches = [
        r
        for r in results
        if r["error"] is None and r.get("deterministic_match") is True
    ]
    deterministic_mismatches = [
        r
        for r in results
        if r["error"] is None and r.get("deterministic_match") is False
    ]
    exported = [r for r in results if r["failure_candidate_exported"]]

    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gemini_match": 0,
            "gemini_mismatch": 0,
            "missing_gemini_proposal": 0,
            "deterministic_mismatch": 0,
            "error": 0,
        }
    )
    for r in results:
        family = r["mismatch_family"]
        if r["error"]:
            by_family[family]["error"] += 1
        elif r.get("gemini_match") is True:
            by_family[family]["gemini_match"] += 1
        elif r.get("gemini_match") is False:
            by_family[family]["gemini_mismatch"] += 1
        else:
            by_family[family]["missing_gemini_proposal"] += 1
        if r.get("deterministic_match") is False:
            by_family[family]["deterministic_mismatch"] += 1

    gemini_denominator = max(1, total - len(errors) - len(missing_gemini))
    deterministic_denominator = max(1, total - len(errors))
    return {
        "run_at_utc": run_at_utc or datetime.now(UTC).isoformat(),
        "primary_evaluation_target": "gemini_advisory_proposal",
        "adk_configured": adk_configured,
        "total": total,
        "match": len(gemini_matches),
        "mismatch": len(gemini_mismatches),
        "gemini_match": len(gemini_matches),
        "gemini_mismatch": len(gemini_mismatches),
        "missing_gemini_proposal": len(missing_gemini),
        "errors": len(errors),
        "mismatch_rate": round(len(gemini_mismatches) / gemini_denominator, 4),
        "gemini_mismatch_rate": round(
            len(gemini_mismatches) / gemini_denominator,
            4,
        ),
        "deterministic_match": len(deterministic_matches),
        "deterministic_mismatch": len(deterministic_mismatches),
        "deterministic_mismatch_rate": round(
            len(deterministic_mismatches) / deterministic_denominator,
            4,
        ),
        "failure_candidates_exported": len(exported),
        "by_family": dict(by_family),
    }


async def run_all() -> int:
    cases = _load_cases()
    total = len(cases)
    print(f"Stress-40 eval: {total} cases")
    print(f"ADK configured: {settings.adk_configured}")
    if not settings.adk_configured:
        print(
            "WARNING: Gemini/ADK is not configured. The deterministic extraction/policy "
            "fallback will handle all cases and Gemini will never get to make mistakes. "
            "Set GOOGLE_API_KEY or configure Vertex AI for meaningful stress results.",
            file=sys.stderr,
        )
    print()

    results: list[dict[str, Any]] = []
    for i, case in enumerate(cases):
        row = await _run_case(case, i, total)
        results.append(row)

    # Write per-case results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    summary = _build_summary(results, adk_configured=settings.adk_configured)

    with SUMMARY_FILE.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    # Print summary
    print("\nStress-40 results:")
    print(f"  total: {total}")
    print(f"  gemini_match: {summary['gemini_match']}")
    print(f"  gemini_mismatch: {summary['gemini_mismatch']}")
    print(f"  missing_gemini_proposal: {summary['missing_gemini_proposal']}")
    print(f"  deterministic_mismatch: {summary['deterministic_mismatch']}")
    print(f"  errors: {summary['errors']}")
    print(f"  gemini_mismatch_rate: {summary['gemini_mismatch_rate']}")
    print(f"  failure_candidates_exported: {summary['failure_candidates_exported']}")
    print("\n  by_family:")
    for family, counts in sorted(summary["by_family"].items()):
        denominator = counts["gemini_match"] + counts["gemini_mismatch"]
        print(
            f"    {family}: {counts['gemini_mismatch']}/{denominator} "
            "gemini mismatch"
        )
    print(f"\nResults: {RESULTS_FILE}")
    print(f"Summary: {SUMMARY_FILE}")

    return 0


def main() -> int:
    return asyncio.run(run_all())


if __name__ == "__main__":
    raise SystemExit(main())
