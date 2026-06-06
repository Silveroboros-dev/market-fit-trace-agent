from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUTPUT_DIR = Path("evals/market_fit_governance_50")
OUTPUT_MANIFEST = OUTPUT_DIR / "governance_examples.jsonl"
OUTPUT_SUMMARY = OUTPUT_DIR / "governance_summary.json"
DATASET_NAME = "market_fit_governance_50"

STRICT_PACKS = (
    "market_fit_v1",
    "market_fit_v2",
    "market_fit_v4_live_promoted",
)
CANDIDATE_PACKS = (
    "market_fit_v2_candidates",
    "market_fit_v3_candidates",
)
TRACE_REPAIR_CASES = Path("evals/trace_repair_v1/cases.jsonl")
TRACE_REPAIR_EXPECTED = Path("evals/trace_repair_v1/expected_transitions.jsonl")
TRACE_REPAIR_RESULT = Path("evals/trace_repair_v1/run_results/trace_repair_result.json")
RETRIEVAL_CANDIDATES_DIR = Path("evals/retrieval_candidates")

HERO_CLUSTER = "ai_startup_ipo_stage_mismatch"
HERO_CLUSTER_TARGET = 12
RETRIEVAL_ROW_TARGET = 24
TOTAL_ROW_TARGET = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the 50-row Phoenix governance manifest from strict packs, "
            "trace-repair cases, and live candidate packets."
        )
    )
    parser.add_argument("--output", default=str(OUTPUT_MANIFEST))
    parser.add_argument("--summary-output", default=str(OUTPUT_SUMMARY))
    parser.add_argument("--limit", type=int, default=TOTAL_ROW_TARGET)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for pack in STRICT_PACKS:
        rows.extend(_pack_rows(Path("evals") / pack, truth_scope="strict_golden"))
    rows.extend(_trace_repair_rows())
    rows.extend(_retrieval_candidate_rows(RETRIEVAL_CANDIDATES_DIR))
    for pack in CANDIDATE_PACKS:
        rows.extend(_pack_rows(Path("evals") / pack, truth_scope="failure_mode_golden"))

    curated = _curate_rows(rows, limit=args.limit)
    _assign_governance_ids(curated)
    _assign_hero_cluster(curated)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path, curated)

    summary = _summary(curated)
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if len(curated) == args.limit else 1


def _pack_rows(pack_dir: Path, *, truth_scope: str) -> list[dict[str, Any]]:
    examples_path = pack_dir / "examples.jsonl"
    expected_path = pack_dir / "expected_outputs.jsonl"
    markets_path = pack_dir / "market_snapshots.jsonl"
    if not (examples_path.exists() and expected_path.exists()):
        return []

    expected_by_id = {row["example_id"]: row for row in _read_jsonl(expected_path)}
    trace_urls = _trace_urls_for_pack(pack_dir)
    rows = []
    for example in _read_jsonl(examples_path):
        case_id = example["example_id"]
        expected = expected_by_id.get(case_id)
        if expected is None:
            continue
        fit = expected["expected_fit"]
        expected_fit_class = fit["semantic_fit_class"]
        source_text = example["source_text"]
        failure_modes = _failure_modes(
            source_text=source_text,
            fit_class=expected_fit_class,
            case_tags=fit.get("case_tags", []),
            expected_behavior=fit.get("minimum_expected_behavior", ""),
        )
        row = {
            "case_id": case_id,
            "source_kind": "eval_pack",
            "source_ref": str(pack_dir),
            "source_type": example.get("source_type"),
            "source_text": source_text,
            "topic": example.get("labels", {}).get("topic"),
            "truth_scope": truth_scope,
            "fit_class": expected_fit_class,
            "expected_fit_class": expected_fit_class,
            "expected_best_market_id": fit.get("best_market_id"),
            "acceptable_market_ids": fit.get("acceptable_market_ids", []),
            "adjacent_market_ids": fit.get("adjacent_market_ids", []),
            "rejected_market_ids": fit.get("rejected_market_ids", []),
            "candidate_market_ids": _candidate_market_ids(fit),
            "failure_modes": failure_modes,
            "actual_behavior": (
                "Current deterministic policy is evaluated against this frozen "
                "fixture row in the governance experiment."
            ),
            "expected_behavior": fit.get("minimum_expected_behavior", ""),
            "promotion_blockers": _promotion_blockers_for_scope(truth_scope),
            "trace_url": trace_urls.get(case_id),
            "market_snapshot_path": str(markets_path) if markets_path.exists() else None,
            "source_provenance": example.get("source_provenance", {}),
            "review_status": "locked" if truth_scope == "strict_golden" else "staged",
            "experiment_eligible": True,
            "strict_metric_eligible": truth_scope == "strict_golden",
            "embedding_text": _embedding_text(
                source_text=source_text,
                fit_class=expected_fit_class,
                failure_modes=failure_modes,
                expected_behavior=fit.get("minimum_expected_behavior", ""),
                actual_behavior="frozen fixture row",
            ),
            "curation_priority": _priority(
                source_text=source_text,
                truth_scope=truth_scope,
                failure_modes=failure_modes,
            ),
        }
        rows.append(row)
    return rows


def _trace_repair_rows() -> list[dict[str, Any]]:
    if not (TRACE_REPAIR_CASES.exists() and TRACE_REPAIR_EXPECTED.exists()):
        return []
    expected_by_id = {
        row["case_id"]: row for row in _read_jsonl(TRACE_REPAIR_EXPECTED)
    }
    result = _read_optional_json(TRACE_REPAIR_RESULT) or {}
    rows = []
    for case in _read_jsonl(TRACE_REPAIR_CASES):
        transition = expected_by_id.get(case["case_id"], {})
        first = transition.get("first_run_expected", {})
        second = transition.get("second_run_expected", {})
        trace_url = None
        before_trace_id = result.get("before_trace_id") or result.get("phoenix_trace", {}).get(
            "trace_id"
        )
        if before_trace_id:
            trace_url = _trace_url(before_trace_id)
        failure_modes = [
            "trace_repair_candidate",
            "causal_mechanism_mismatch",
            "resolution_target_mismatch",
            "weak_proxy",
        ]
        expected_behavior = (
            "First run should overstate the leaderboard market, Phoenix MCP should "
            "retrieve mismatch signals, and the deterministic rerun should cap the "
            "fit to weak_proxy."
        )
        actual_behavior = (
            f"first_run={first.get('fit_class')} -> second_run={second.get('fit_class')}; "
            f"fallback_used={result.get('fallback_used')}"
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "source_kind": "trace_repair_pack",
                "source_ref": "evals/trace_repair_v1",
                "source_type": case.get("case_type"),
                "source_text": case["source_text"],
                "topic": "AI",
                "truth_scope": "trace_repair_case",
                "fit_class": second.get("fit_class", "weak_proxy"),
                "expected_fit_class": second.get("fit_class"),
                "expected_best_market_id": second.get("recommended_market_id"),
                "acceptable_market_ids": [],
                "adjacent_market_ids": [first.get("recommended_market_id")]
                if first.get("recommended_market_id")
                else [],
                "rejected_market_ids": [],
                "candidate_market_ids": case.get("candidate_market_ids", []),
                "failure_modes": failure_modes,
                "actual_behavior": actual_behavior,
                "expected_behavior": expected_behavior,
                "promotion_blockers": [
                    "transition_eval_not_single_run_strict_golden",
                ],
                "trace_url": trace_url,
                "market_snapshot_path": "evals/trace_repair_v1/market_snapshots.jsonl",
                "source_provenance": case.get("source_provenance", {}),
                "review_status": "locked_transition",
                "experiment_eligible": False,
                "strict_metric_eligible": False,
                "embedding_text": _embedding_text(
                    source_text=case["source_text"],
                    fit_class=second.get("fit_class", "weak_proxy"),
                    failure_modes=failure_modes,
                    expected_behavior=expected_behavior,
                    actual_behavior=actual_behavior,
                ),
                "curation_priority": 95,
            }
        )
    return rows


def _retrieval_candidate_rows(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows = []
    for candidate_dir in sorted(path.parent for path in root.glob("*/*/source.json")):
        retrieval_path = candidate_dir / "retrieval_result.json"
        if not retrieval_path.exists():
            continue
        source = _read_json(candidate_dir / "source.json")
        retrieval = _read_json(retrieval_path)
        run_result = _read_optional_json(candidate_dir / "run_result.json") or {}
        review = _read_optional_json(candidate_dir / "review_decision.json") or {}
        llm_review = _read_optional_json(candidate_dir / "llm_review_suggestion.json") or {}
        review_notes = _read_optional_text(candidate_dir / "review_notes.md")
        fit = run_result.get("fit", {})
        claim = run_result.get("claim", {})
        source_text = source["source_text"]
        review_status = review.get("human_review_status", "pending")
        expected = _expected_from_reviewed_candidate(
            case_id=source["case_id"],
            review_note=review.get("reviewer_note", ""),
            review_notes=review_notes,
        )
        fit_class = (
            expected.get("fit_class")
            or fit.get("semantic_fit_class")
            or "no_clean_expression"
        )
        failure_modes = _candidate_failure_modes(
            source_text=source_text,
            fit_class=fit_class,
            review=review,
            llm_review=llm_review,
            review_notes=review_notes,
        )
        expected_behavior = expected.get("expected_behavior") or _candidate_expected_behavior(
            review=review,
            llm_review=llm_review,
            review_notes=review_notes,
        )
        actual_behavior = _candidate_actual_behavior(fit=fit, run_result=run_result)
        truth_scope = (
            "failure_mode_golden"
            if expected.get("experiment_eligible")
            else (
                "reviewed_candidate"
                if review_status in {"promote", "needs_more_rules", "candidate_only", "reject"}
                else "draft_candidate"
            )
        )
        rows.append(
            {
                "case_id": source["case_id"],
                "source_kind": "retrieval_candidate",
                "source_ref": str(candidate_dir),
                "source_type": source.get("source_type", "retrieval_candidate"),
                "source_text": source_text,
                "topic": _topic_from_text(source_text),
                "truth_scope": truth_scope,
                "fit_class": fit_class,
                "expected_fit_class": expected.get("fit_class"),
                "expected_best_market_id": expected.get("best_market_id"),
                "acceptable_market_ids": expected.get("acceptable_market_ids", []),
                "adjacent_market_ids": expected.get("adjacent_market_ids", []),
                "rejected_market_ids": expected.get("rejected_market_ids", []),
                "candidate_market_ids": retrieval.get("market_ids_considered", []),
                "failure_modes": failure_modes,
                "actual_behavior": actual_behavior,
                "expected_behavior": expected_behavior,
                "promotion_blockers": _candidate_promotion_blockers(
                    source=source,
                    review=review,
                    expected=expected,
                    run_result=run_result,
                    candidate_dir=candidate_dir,
                ),
                "trace_url": run_result.get("phoenix_trace_url"),
                "market_snapshot_path": str(candidate_dir / "market_snapshots.jsonl"),
                "source_provenance": source.get("source_provenance", {}),
                "normalized_claim": claim,
                "review_status": review_status,
                "experiment_eligible": bool(expected.get("experiment_eligible")),
                "strict_metric_eligible": False,
                "embedding_text": _embedding_text(
                    source_text=source_text,
                    fit_class=fit_class,
                    failure_modes=failure_modes,
                    expected_behavior=expected_behavior,
                    actual_behavior=actual_behavior,
                ),
                "curation_priority": _priority(
                    source_text=source_text,
                    truth_scope=truth_scope,
                    failure_modes=failure_modes,
                ),
            }
        )
    return rows


def _expected_from_reviewed_candidate(
    *,
    case_id: str,
    review_note: str,
    review_notes: str,
) -> dict[str, Any]:
    text = f"{case_id}\n{review_note}\n{review_notes}".lower()
    if "openai" in text and "event_stage_mismatch" in text:
        return {
            "fit_class": "indirect",
            "best_market_id": "2314379",
            "acceptable_market_ids": ["656312", "2314378"],
            "adjacent_market_ids": ["656312", "2314378", "2321571"],
            "rejected_market_ids": [
                "2299990",
                "2299992",
                "2299988",
                "2299989",
                "2299986",
                "2299987",
                "2299991",
                "2299985",
                "2298771",
                "2299995",
                "2298768",
                "2298770",
                "2298775",
            ],
            "expected_behavior": (
                "Classify IPO-completion markets as indirect adjacent evidence for "
                "OpenAI filing/preparation. Do not label IPO completion by date as a "
                "direct expression of confidential filing or preparation."
            ),
            "experiment_eligible": True,
        }
    return {}


def _candidate_failure_modes(
    *,
    source_text: str,
    fit_class: str,
    review: dict[str, Any],
    llm_review: dict[str, Any],
    review_notes: str,
) -> list[str]:
    modes = []
    modes.extend(str(item) for item in llm_review.get("likely_issues", []) if item)
    note_text = " ".join(
        [
            review.get("reviewer_note", ""),
            review_notes,
            llm_review.get("judge_rationale", ""),
        ]
    ).lower()
    for name in (
        "event_stage_mismatch",
        "horizon_mismatch",
        "resolution_risk",
        "missing_resolution_rules",
        "off_topic_market",
        "weak_proxy_risk",
        "compound_thesis",
        "wrong_market",
    ):
        if name in note_text and name not in modes:
            modes.append(name)
    modes.extend(
        _failure_modes(
            source_text=source_text,
            fit_class=fit_class,
            case_tags=[],
            expected_behavior=note_text,
        )
    )
    return sorted(set(modes))


def _candidate_expected_behavior(
    *,
    review: dict[str, Any],
    llm_review: dict[str, Any],
    review_notes: str,
) -> str:
    if review.get("reviewer_note"):
        return review["reviewer_note"]
    if llm_review.get("judge_rationale"):
        return llm_review["judge_rationale"]
    lines = [
        line.strip()
        for line in review_notes.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return lines[0] if lines else "Human review required before strict promotion."


def _candidate_actual_behavior(*, fit: dict[str, Any], run_result: dict[str, Any]) -> str:
    if not run_result:
        return "Retrieval-only candidate packet; no agent run_result was captured."
    recommended = fit.get("recommended_market_id")
    return (
        f"Agent proposed {fit.get('semantic_fit_class')} with "
        f"recommended_market_id={recommended}; reason={fit.get('fit_reason')}"
    )


def _candidate_promotion_blockers(
    *,
    source: dict[str, Any],
    review: dict[str, Any],
    expected: dict[str, Any],
    run_result: dict[str, Any],
    candidate_dir: Path,
) -> list[str]:
    blockers = []
    if not source.get("source_provenance"):
        blockers.append("source_provenance_not_frozen")
    if not run_result:
        blockers.append("missing_run_result")
    claim = run_result.get("claim", {}) if run_result else {}
    if claim.get("confidence") is not None and claim.get("confidence", 1.0) < 0.55:
        blockers.append("low_extraction_confidence")
    if not (candidate_dir / "market_rules_snapshots.jsonl").exists():
        blockers.append("missing_market_rules_snapshot")
    if not expected.get("experiment_eligible"):
        blockers.append("expected_labels_not_locked")
    if review.get("human_review_status") != "promote":
        blockers.append(f"human_review_status_{review.get('human_review_status', 'pending')}")
    return sorted(set(blockers))


def _curate_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    strict_and_trace = [
        row
        for row in rows
        if row["truth_scope"] in {"strict_golden", "trace_repair_case"}
    ]
    retrieval = [
        row for row in rows if row["source_kind"] == "retrieval_candidate"
    ]
    candidate_pack = [
        row
        for row in rows
        if row["truth_scope"] == "failure_mode_golden"
        and row["source_kind"] == "eval_pack"
    ]

    selected = list(_sort_for_demo(strict_and_trace))
    selected.extend(_sort_for_demo(retrieval)[:RETRIEVAL_ROW_TARGET])
    remaining_slots = max(limit - len(selected), 0)
    selected_case_ids = {row["case_id"] for row in selected}
    unique_candidate_pack = [
        row for row in _sort_for_demo(candidate_pack) if row["case_id"] not in selected_case_ids
    ]
    selected.extend(unique_candidate_pack[:remaining_slots])
    return _sort_for_demo(selected)[:limit]


def _assign_governance_ids(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        row["governance_id"] = f"gov_{index:03d}_{_slug(row['case_id'])}"


def _assign_hero_cluster(rows: list[dict[str, Any]]) -> None:
    hero_candidates = [
        row
        for row in rows
        if _is_ai_startup_ipo_row(row["source_text"], row.get("failure_modes", []))
    ]
    hero_ids = {
        row["governance_id"]
        for row in _sort_for_demo(hero_candidates)[:HERO_CLUSTER_TARGET]
    }
    for row in rows:
        is_hero = row["governance_id"] in hero_ids
        row["hero_cluster"] = HERO_CLUSTER if is_hero else None
        row["is_hero_cluster"] = is_hero
        if is_hero and HERO_CLUSTER not in row["failure_modes"]:
            row["failure_modes"] = sorted([*row["failure_modes"], HERO_CLUSTER])
            row["embedding_text"] = _embedding_text(
                source_text=row["source_text"],
                fit_class=row["fit_class"],
                failure_modes=row["failure_modes"],
                expected_behavior=row["expected_behavior"],
                actual_behavior=row["actual_behavior"],
            )


def _sort_for_demo(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, int, str]:
        hero_rank = 0 if _is_ai_startup_ipo_row(row["source_text"], row["failure_modes"]) else 1
        return (hero_rank, -int(row.get("curation_priority", 0)), row["case_id"])

    return sorted(rows, key=key)


def _priority(*, source_text: str, truth_scope: str, failure_modes: list[str]) -> int:
    priority = 0
    if truth_scope == "strict_golden":
        priority += 70
    elif truth_scope == "trace_repair_case":
        priority += 85
    elif truth_scope == "failure_mode_golden":
        priority += 60
    elif truth_scope == "reviewed_candidate":
        priority += 45
    else:
        priority += 25
    if _is_ai_startup_ipo_row(source_text, failure_modes):
        priority += 100
    if "event_stage_mismatch" in failure_modes:
        priority += 30
    if "weak_proxy" in failure_modes or "weak_proxy_risk" in failure_modes:
        priority += 15
    return priority


def _failure_modes(
    *,
    source_text: str,
    fit_class: str,
    case_tags: list[str],
    expected_behavior: str,
) -> list[str]:
    text = f"{source_text}\n{expected_behavior}".lower()
    modes = [str(tag) for tag in case_tags if tag]
    if fit_class == "weak_proxy" and "weak_proxy" not in modes:
        modes.append("weak_proxy")
    if fit_class == "no_clean_expression" and "no_clean_expression" not in modes:
        modes.append("no_clean_expression")
    if "horizon" in text and "horizon_mismatch" not in modes:
        modes.append("horizon_mismatch")
    if "resolution" in text and "resolution_risk" not in modes:
        modes.append("resolution_risk")
    if "wrong market" in text or "wrong_market" in text:
        modes.append("wrong_market")
    if "duplicate" in text or "revisit" in text:
        modes.append("duplicate_or_revisit")
    if _is_stage_mismatch_text(text):
        modes.append("event_stage_mismatch")
    if _is_ai_startup_ipo_row(source_text, modes):
        modes.append("ai_startup_ipo")
    return sorted(set(modes))


def _is_stage_mismatch_text(text: str) -> bool:
    return bool(
        ("filing" in text or "file confidentially" in text or "preparing" in text)
        and "ipo" in text
        and (
            "completion" in text
            or "complete" in text
            or "by september" in text
            or "by december" in text
            or "by date" in text
        )
    )


def _is_ai_startup_ipo_row(source_text: str, failure_modes: list[str]) -> bool:
    text = source_text.lower()
    has_company = any(name in text for name in ("openai", "anthropic", "spacex"))
    has_stage = any(
        word in text
        for word in (
            "ipo",
            "public offering",
            "valuation",
            "file confidentially",
            "filing",
            "preparing to file",
        )
    )
    return bool(
        HERO_CLUSTER in failure_modes
        or "event_stage_mismatch" in failure_modes
        or (has_company and has_stage)
    )


def _candidate_market_ids(fit: dict[str, Any]) -> list[str]:
    ids = []
    for key in (
        "best_market_id",
        "acceptable_market_ids",
        "adjacent_market_ids",
        "rejected_market_ids",
    ):
        value = fit.get(key)
        if isinstance(value, list):
            ids.extend(str(item) for item in value if item)
        elif value:
            ids.append(str(value))
    return sorted(set(ids))


def _promotion_blockers_for_scope(truth_scope: str) -> list[str]:
    if truth_scope == "strict_golden":
        return []
    if truth_scope == "failure_mode_golden":
        return [
            "candidate_pack_not_default_ci",
            "market_rules_need_recheck_before_strict_promotion",
        ]
    return ["truth_scope_not_strict_golden"]


def _topic_from_text(source_text: str) -> str:
    text = source_text.lower()
    if any(word in text for word in ("openai", "anthropic", "gemini", "claude", "gpt", "ai ")):
        return "AI"
    if any(word in text for word in ("fed", "inflation", "rates", "mortgage")):
        return "macro"
    if any(word in text for word in ("iran", "hormuz", "sanctions", "war")):
        return "geopolitics"
    if any(word in text for word in ("sol", "solana", "tokenized", "crypto")):
        return "crypto"
    return "other"


def _embedding_text(
    *,
    source_text: str,
    fit_class: str,
    failure_modes: list[str],
    expected_behavior: str,
    actual_behavior: str,
) -> str:
    return " ".join(
        part.strip()
        for part in (
            f"source: {source_text}",
            f"fit_class: {fit_class}",
            f"failure_modes: {', '.join(failure_modes)}",
            f"actual_behavior: {actual_behavior}",
            f"expected_behavior: {expected_behavior}",
        )
        if part
    )


def _trace_urls_for_pack(pack_dir: Path) -> dict[str, str]:
    result_path = pack_dir / "phoenix_experiment_result.json"
    if not result_path.exists():
        return {}
    payload = _read_optional_json(result_path) or {}
    return {
        row["case_id"]: row["phoenix_trace_url"]
        for row in payload.get("rows", [])
        if row.get("case_id") and row.get("phoenix_trace_url")
    }


def _trace_url(trace_id: str) -> str | None:
    if not trace_id:
        return None
    base_url = None
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PHOENIX_BASE_URL="):
                base_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/traces/{trace_id}"


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scope_counts = Counter(row["truth_scope"] for row in rows)
    failure_counts = Counter(
        failure_mode
        for row in rows
        for failure_mode in row.get("failure_modes", [])
    )
    source_counts = Counter(row["source_kind"] for row in rows)
    return {
        "status": "ready" if len(rows) == TOTAL_ROW_TARGET else "incomplete",
        "dataset_name": DATASET_NAME,
        "row_count": len(rows),
        "hero_cluster": HERO_CLUSTER,
        "hero_cluster_count": sum(1 for row in rows if row.get("is_hero_cluster")),
        "truth_scope_counts": dict(sorted(scope_counts.items())),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "experiment_eligible_count": sum(1 for row in rows if row["experiment_eligible"]),
        "strict_metric_eligible_count": sum(
            1 for row in rows if row["strict_metric_eligible"]
        ),
        "failure_mode_counts": dict(failure_counts.most_common()),
        "strict_metrics_exclude_weak_or_draft_rows": True,
        "governance_metrics_include_all_rows": True,
        "rows": [
            {
                "governance_id": row["governance_id"],
                "case_id": row["case_id"],
                "truth_scope": row["truth_scope"],
                "fit_class": row["fit_class"],
                "hero_cluster": row["hero_cluster"],
                "failure_modes": row["failure_modes"],
                "experiment_eligible": row["experiment_eligible"],
            }
            for row in rows
        ],
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
