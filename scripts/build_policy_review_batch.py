"""Build a family-level policy review batch from failure candidate packets.

Reads candidate-only packets under evals/failure_candidates/<date>/ and writes
evals/policy_review_batches/<date>/POLICY_REVIEW.md plus summary.json.

Usage:
    python scripts/build_policy_review_batch.py
    python scripts/build_policy_review_batch.py --date 2026-06-08
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_INPUT_DIR = Path("evals/failure_candidates")
DEFAULT_OUTPUT_DIR = Path("evals/policy_review_batches")
SCHEMA_VERSION = "policy_review_batch_v0"
STRICT_GOLDEN_MUTATION_FILES = {
    "expected_outputs.jsonl",
    "examples.jsonl",
    "market_snapshots.jsonl",
}
REVIEW_OPTIONS = (
    "needs_more_rules",
    "candidate_only",
    "promote_to_strict_golden_candidate",
    "disregard",
)

POLICY_DIRECTIONS = {
    "event_stage_mismatch": (
        "Strengthen stage-awareness checks. Distinguish preparation, filing, "
        "roadshow, pricing, completion, and post-event valuation before assigning "
        "indirect or stronger fit."
    ),
    "horizon_mismatch": (
        "Require explicit horizon alignment. A related market in the wrong year "
        "should stay weak_proxy or no_clean_expression unless the thesis clearly "
        "states an overlapping milestone."
    ),
    "inverse_framing": (
        "Add an outcome-polarity review cue. Inverted markets may be useful, but "
        "the system must state which outcome supports the thesis and avoid treating "
        "inverse framing as direct evidence."
    ),
    "composite_thesis": (
        "Detect compound claims. Markets that resolve only one material component "
        "should be marked partial coverage and sent to review before promotion."
    ),
    "metric_mismatch": (
        "Separate evidence metric from resolution metric. Growth, users, margins, "
        "or benchmarks may be evidence, but they do not resolve valuation, revenue, "
        "release, or price targets by themselves."
    ),
    "entity_mismatch": (
        "Tighten entity, product, and version matching. Same ecosystem is not enough "
        "when the market resolves a different company, model family, or version."
    ),
    "causal_mechanism": (
        "Require a stated causal bridge. Inputs such as hardware, funding, regulation, "
        "rates, or energy costs should not become strong market-fit labels without "
        "a resolution rule that tests the downstream claim."
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate failure candidate packets into a candidate-only policy "
            "review artifact."
        )
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--date",
        default=None,
        help="Candidate date folder to summarize. Defaults to the latest date folder.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_policy_review_batch(
            input_dir=Path(args.input_dir),
            out_dir=Path(args.out_dir),
            date=args.date,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_policy_review_batch(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    out_dir: Path = DEFAULT_OUTPUT_DIR,
    date: str | None = None,
) -> dict[str, Any]:
    candidate_date = date or _latest_candidate_date(input_dir)
    source_dir = input_dir / candidate_date
    candidates = _load_candidates(source_dir)
    if not candidates:
        raise FileNotFoundError(f"No failure candidate packets found in {source_dir}")

    summary = _summarize_candidates(
        candidates=candidates,
        candidate_date=candidate_date,
        source_dir=source_dir,
    )
    batch_dir = out_dir / candidate_date
    batch_dir.mkdir(parents=True, exist_ok=True)
    summary_path = batch_dir / "summary.json"
    markdown_path = batch_dir / "POLICY_REVIEW.md"
    _write_json(summary_path, summary)
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")

    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "candidate_date": candidate_date,
        "candidate_count": summary["candidate_count"],
        "family_count": len(summary["families"]),
        "summary_path": str(summary_path),
        "policy_review_path": str(markdown_path),
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
    }


def _latest_candidate_date(input_dir: Path) -> str:
    if not input_dir.exists():
        raise FileNotFoundError(f"Failure candidate directory not found: {input_dir}")
    date_dirs = [
        path.name
        for path in input_dir.iterdir()
        if path.is_dir() and list(path.glob("*/failure_signal.json"))
    ]
    if not date_dirs:
        raise FileNotFoundError(f"No dated failure candidate folders found in {input_dir}")
    return sorted(date_dirs)[-1]


def _load_candidates(source_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for candidate_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
        failure_path = candidate_dir / "failure_signal.json"
        proposed_path = candidate_dir / "proposed_eval_case.json"
        source_path = candidate_dir / "source.json"
        if not failure_path.exists() or not proposed_path.exists():
            continue
        failure = _read_json(failure_path)
        proposed = _read_json(proposed_path)
        source = _read_json(source_path) if source_path.exists() else {}
        candidates.append(_candidate_row(candidate_dir, failure, proposed, source))
    return candidates


def _candidate_row(
    candidate_dir: Path,
    failure: dict[str, Any],
    proposed: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    market = proposed.get("market") or {}
    triggered_metrics = list(failure.get("triggered_metrics") or [])
    family = failure.get("mismatch_family") or _fallback_family(triggered_metrics)
    return {
        "candidate_dir": str(candidate_dir),
        "case_id": failure.get("case_id") or proposed.get("case_id") or candidate_dir.name,
        "schema_version": failure.get("schema_version") or proposed.get("schema_version"),
        "family": family,
        "triggered_metrics": triggered_metrics,
        "truth_scope": proposed.get("truth_scope") or source.get("truth_scope"),
        "canonical_truth": bool(proposed.get("canonical_truth", False)),
        "candidate_only": bool(failure.get("candidate_only", True)),
        "human_review_options": list(proposed.get("human_review_options") or []),
        "expected_fit_class": (
            failure.get("expected_fit_class")
            or proposed.get("expected_fit_class")
            or proposed.get("proposed_target_fit_class")
        ),
        "gemini_fit_class": (
            failure.get("observed_gemini_fit_class")
            or proposed.get("observed_gemini_fit_class")
        ),
        "deterministic_fit_class": (
            failure.get("deterministic_fit_class")
            or proposed.get("deterministic_fit_class")
            or failure.get("observed_fit_class")
        ),
        "deterministic_match": failure.get(
            "deterministic_match",
            proposed.get("deterministic_match"),
        ),
        "recommended_market_id": failure.get("observed_recommended_market_id"),
        "market_title": market.get("title"),
        "source_text": proposed.get("source_text") or source.get("source_text"),
        "trap_description": failure.get("trap_description"),
        "phoenix_trace_id": failure.get("phoenix_trace_id"),
        "phoenix_trace_url": failure.get("phoenix_trace_url"),
        "writes_strict_expected_labels": bool(
            proposed.get("writes_strict_expected_labels", False)
        ),
        "writes_policy_code": bool(proposed.get("writes_policy_code", False)),
    }


def _summarize_candidates(
    *,
    candidates: list[dict[str, Any]],
    candidate_date: str,
    source_dir: Path,
) -> dict[str, Any]:
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        families[candidate["family"]].append(candidate)

    family_summaries = {
        family: _summarize_family(family, rows)
        for family, rows in sorted(families.items())
    }
    all_patterns = _top_patterns(candidates)
    mutation_risks = [
        candidate["case_id"]
        for candidate in candidates
        if candidate["writes_strict_expected_labels"] or candidate["writes_policy_code"]
    ]
    missing_review_options = [
        candidate["case_id"]
        for candidate in candidates
        if "disregard" not in set(candidate["human_review_options"])
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "candidate_date": candidate_date,
        "source_dir": str(source_dir),
        "candidate_count": len(candidates),
        "family_count": len(family_summaries),
        "review_options": list(REVIEW_OPTIONS),
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
        "strict_golden_mutation_files": sorted(STRICT_GOLDEN_MUTATION_FILES),
        "mutation_risk_case_ids": mutation_risks,
        "missing_disregard_case_ids": missing_review_options,
        "top_patterns": all_patterns,
        "families": family_summaries,
    }


def _summarize_family(family: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_counts = Counter(_label(row["expected_fit_class"]) for row in rows)
    gemini_counts = Counter(_label(row["gemini_fit_class"]) for row in rows)
    deterministic_counts = Counter(_label(row["deterministic_fit_class"]) for row in rows)
    deterministic_mismatch_count = sum(
        1 for row in rows if row.get("deterministic_match") is False
    )
    traces = sum(1 for row in rows if row.get("phoenix_trace_url"))
    return {
        "candidate_count": len(rows),
        "policy_direction": POLICY_DIRECTIONS.get(
            family,
            "Review repeated candidate failures and decide whether they reflect a "
            "prompt issue, policy rule gap, or synthetic noise.",
        ),
        "expected_fit_counts": dict(sorted(expected_counts.items())),
        "gemini_fit_counts": dict(sorted(gemini_counts.items())),
        "deterministic_fit_counts": dict(sorted(deterministic_counts.items())),
        "deterministic_mismatch_count": deterministic_mismatch_count,
        "phoenix_trace_count": traces,
        "patterns": _top_patterns(rows),
        "candidates": [
            {
                "case_id": row["case_id"],
                "expected_fit_class": row["expected_fit_class"],
                "gemini_fit_class": row["gemini_fit_class"],
                "deterministic_fit_class": row["deterministic_fit_class"],
                "deterministic_match": row["deterministic_match"],
                "market_title": row["market_title"],
                "trap_description": row["trap_description"],
                "phoenix_trace_url": row["phoenix_trace_url"],
                "candidate_dir": row["candidate_dir"],
            }
            for row in sorted(rows, key=lambda item: item["case_id"])
        ],
    }


def _top_patterns(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    pattern_counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        pattern_counts[
            (
                row["family"],
                _label(row["expected_fit_class"]),
                _label(row["gemini_fit_class"]),
                _label(row["deterministic_fit_class"]),
            )
        ] += 1
    patterns: list[dict[str, Any]] = []
    for (family, expected, gemini, deterministic), count in pattern_counts.most_common(
        limit
    ):
        patterns.append(
            {
                "family": family,
                "expected_fit_class": expected,
                "gemini_fit_class": gemini,
                "deterministic_fit_class": deterministic,
                "count": count,
            }
        )
    return patterns


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Policy Review Batch",
        "",
        f"Generated at UTC: `{summary['generated_at_utc']}`",
        f"Candidate date: `{summary['candidate_date']}`",
        f"Source directory: `{summary['source_dir']}`",
        "",
        "## Scope",
        "",
        (
            "This artifact groups candidate-only failure packets into reviewable "
            "policy and prompt proposals. It is not a strict golden dataset and it "
            "does not mutate policy code."
        ),
        "",
        f"- Failure candidates: `{summary['candidate_count']}`",
        f"- Failure families: `{summary['family_count']}`",
        f"- Writes strict expected labels: `{summary['writes_strict_expected_labels']}`",
        f"- Writes policy code: `{summary['writes_policy_code']}`",
        "- Human review options: "
        + ", ".join(f"`{option}`" for option in summary["review_options"]),
        "",
        "## Family Summary",
        "",
        "| Family | Candidates | Phoenix traces | Deterministic mismatches | Direction |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for family, data in summary["families"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{family}`",
                    str(data["candidate_count"]),
                    str(data["phoenix_trace_count"]),
                    str(data["deterministic_mismatch_count"]),
                    _md_escape(data["policy_direction"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Top Repeated Patterns",
            "",
            "| Count | Family | Expected | Gemini advisory | Deterministic |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for pattern in summary["top_patterns"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(pattern["count"]),
                    f"`{pattern['family']}`",
                    f"`{pattern['expected_fit_class']}`",
                    f"`{pattern['gemini_fit_class']}`",
                    f"`{pattern['deterministic_fit_class']}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Family Review Queues",
            "",
        ]
    )
    for family, data in summary["families"].items():
        lines.extend(_render_family_section(family, data))

    lines.extend(
        [
            "## Review Contract",
            "",
            "- `needs_more_rules`: repeated failure looks real enough to write a "
            "targeted prompt or deterministic policy proposal.",
            "- `candidate_only`: keep as stress evidence but do not promote to strict goldens.",
            "- `promote_to_strict_golden_candidate`: reviewer believes the case can "
            "become a defensible frozen eval.",
            "- `disregard`: synthetic trap is unrealistic, duplicate, malformed, or not useful.",
            "",
            "No policy code, strict expected labels, or golden fixtures were mutated "
            "by this batch.",
            "",
        ]
    )
    if summary["mutation_risk_case_ids"]:
        lines.extend(
            [
                "## Mutation Risk Warnings",
                "",
                "These candidate packets unexpectedly claimed write access:",
                "",
            ]
        )
        lines.extend(f"- `{case_id}`" for case_id in summary["mutation_risk_case_ids"])
        lines.append("")
    if summary["missing_disregard_case_ids"]:
        lines.extend(
            [
                "## Missing Disregard Warnings",
                "",
                "These candidate packets lack the `disregard` review option:",
                "",
            ]
        )
        lines.extend(
            f"- `{case_id}`" for case_id in summary["missing_disregard_case_ids"]
        )
        lines.append("")
    return "\n".join(lines)


def _render_family_section(family: str, data: dict[str, Any]) -> list[str]:
    lines = [
        f"### `{family}`",
        "",
        f"Candidates: `{data['candidate_count']}`",
        "",
        f"Review direction: {data['policy_direction']}",
        "",
        "Fit-class counts:",
        "",
        f"- Expected: {_counts_inline(data['expected_fit_counts'])}",
        f"- Gemini advisory: {_counts_inline(data['gemini_fit_counts'])}",
        f"- Deterministic: {_counts_inline(data['deterministic_fit_counts'])}",
        "",
        "| Case | Expected | Gemini | Deterministic | Trace | Trap |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in data["candidates"]:
        trace = (
            f"[trace]({candidate['phoenix_trace_url']})"
            if candidate.get("phoenix_trace_url")
            else "n/a"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{candidate['case_id']}`",
                    f"`{_label(candidate['expected_fit_class'])}`",
                    f"`{_label(candidate['gemini_fit_class'])}`",
                    f"`{_label(candidate['deterministic_fit_class'])}`",
                    trace,
                    _md_escape(candidate.get("trap_description") or ""),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def _fallback_family(triggered_metrics: list[str]) -> str:
    if not triggered_metrics:
        return "unclassified_failure"
    return "+".join(sorted(triggered_metrics))


def _counts_inline(counts: dict[str, int]) -> str:
    return ", ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))


def _label(value: Any) -> str:
    return str(value) if value not in (None, "") else "missing"


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
