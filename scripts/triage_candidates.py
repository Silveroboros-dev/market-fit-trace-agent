from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adk_runtime import ADKJsonRuntime

DEFAULT_CANDIDATES_DIR = Path("evals/retrieval_candidates")
OUTPUT_NAME = "llm_review_suggestion.json"
JUDGE_VERSION = "llm_candidate_triage_v0"
REVIEW_STATUSES = ("promote", "reject", "needs_more_rules", "candidate_only")
REVIEW_PRIORITIES = ("high", "medium", "low")
LIKELY_ISSUES = (
    "off_topic_market",
    "missing_resolution_rules",
    "horizon_mismatch",
    "wrong_metric",
    "wrong_entity",
    "weak_proxy_risk",
    "resolution_risk",
    "compound_thesis",
    "inverse_market_check",
    "clean_candidate",
)
FORBIDDEN_OUTPUT_KEYS = {
    "expected_fit_class",
    "expected_best_market_id",
    "best_market_id",
    "semantic_fit_class",
}


class LocalRuleRuntime:
    runtime_name = "local-rule-triage"

    async def generate_json(self, **_kwargs: object) -> None:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate non-canonical LLM review suggestions for retrieval candidate packets."
        )
    )
    parser.add_argument("--candidates-dir", default=str(DEFAULT_CANDIDATES_DIR))
    parser.add_argument("--case-id", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Skip Gemini/ADK and write deterministic local triage suggestions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print triage suggestions without writing llm_review_suggestion.json files.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    candidate_dirs = _candidate_dirs(Path(args.candidates_dir), case_id=args.case_id)
    if args.limit > 0:
        candidate_dirs = candidate_dirs[: args.limit]
    if not candidate_dirs:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "No retrieval candidate packets found.",
                    "candidates_dir": args.candidates_dir,
                    "case_id": args.case_id or None,
                },
                indent=2,
            )
        )
        return 1

    runtime = LocalRuleRuntime() if args.force_local else ADKJsonRuntime()
    rows = []
    for candidate_dir in candidate_dirs:
        suggestion = await triage_candidate_dir(candidate_dir, runtime=runtime)
        output_path = candidate_dir / OUTPUT_NAME
        if not args.dry_run:
            output_path.write_text(
                json.dumps(suggestion, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        rows.append(
            {
                "case_id": suggestion["candidate_id"],
                "candidate_dir": str(candidate_dir),
                "suggestion_path": str(output_path),
                "review_priority": suggestion["review_priority"],
                "suggested_review_status": suggestion["suggested_review_status"],
                "likely_issues": suggestion["likely_issues"],
                "triage_source": suggestion["triage_source"],
            }
        )

    summary = {
        "status": "dry_run" if args.dry_run else "ok",
        "candidate_count": len(rows),
        "judge_version": JUDGE_VERSION,
        "rows": rows,
    }
    print(json.dumps(summary, indent=2))
    return 0


async def triage_candidate_dir(
    candidate_dir: Path,
    *,
    runtime: Any | None = None,
) -> dict[str, Any]:
    packet = _candidate_packet(candidate_dir)
    runtime = runtime or ADKJsonRuntime()
    model_output = await runtime.generate_json(
        prompt=json.dumps(packet, indent=2, sort_keys=True),
        task_name="candidate_triage",
        instruction=_triage_instruction(),
    )
    suggestion = _normalize_model_suggestion(
        model_output,
        packet=packet,
        runtime_name=getattr(runtime, "runtime_name", "unknown"),
    )
    if suggestion is not None:
        return suggestion
    return _local_rule_suggestion(packet)


def _triage_instruction() -> str:
    return f"""
You are a review assistant for Market Fit Trace Agent retrieval candidates.

Return JSON only. Your job is triage, not truth labeling.

You may suggest whether a human reviewer should treat a packet as promote, reject,
needs_more_rules, or candidate_only. You must not output expected_fit_class,
expected_best_market_id, best_market_id, or semantic_fit_class.

Allowed suggested_review_status values: {", ".join(REVIEW_STATUSES)}.
Allowed review_priority values: {", ".join(REVIEW_PRIORITIES)}.
Allowed likely_issues values: {", ".join(LIKELY_ISSUES)}.

Use promote only when the packet appears review-ready, resolution rules are present,
and a human can make a defensible promotion decision from the frozen evidence.
Use needs_more_rules when resolution rules are missing or insufficient.
Use reject when the retrieval appears off-topic or not useful for market-fit governance.
Use candidate_only when it is useful evidence but should not be promoted yet.
Use inverse_market_check when a binary market's opposite outcome may support the
source thesis better than the market title's Yes outcome. This is an advisory
review cue only; do not convert it into strict expected labels.

Required JSON shape:
{{
  "review_priority": "high | medium | low",
  "suggested_review_status": "promote | reject | needs_more_rules | candidate_only",
  "suggested_fit_risk": "likely_weak_proxy | likely_no_clean_expression | unclear",
  "likely_issues": ["off_topic_market", "inverse_market_check"],
  "markets_to_inspect": ["market_id"],
  "judge_rationale": "short explanation for a human reviewer",
  "needs_human_check": true,
  "must_not_promote_without": ["frozen resolution rules", "human adjudication"]
}}
""".strip()


def _candidate_packet(candidate_dir: Path) -> dict[str, Any]:
    source = _read_json(candidate_dir / "source.json")
    retrieval = _read_json(candidate_dir / "retrieval_result.json")
    markets = _read_jsonl(candidate_dir / "market_snapshots.jsonl")
    source_rules = _read_jsonl(candidate_dir / "market_rules_snapshots.jsonl")
    agent_rules = _read_jsonl(candidate_dir / "agent_market_rules_snapshots.jsonl")
    run_result = _read_optional_json(candidate_dir / "run_result.json") or {}
    run_retrieval = run_result.get("market_retrieval") or {}
    review_rules = agent_rules if run_retrieval and agent_rules else source_rules
    retrieved_market_ids = run_retrieval.get("market_ids_considered") or retrieval.get(
        "market_ids_considered", []
    )
    markets_by_id = {str(market.get("market_id")): market for market in markets}
    rules_by_id = {str(rule.get("market_id")): rule for rule in review_rules}
    market_rows = []
    for market_id in retrieved_market_ids:
        market = markets_by_id.get(str(market_id), {})
        rule = rules_by_id.get(str(market_id), {})
        market_rows.append(
            {
                "market_id": str(market_id),
                "title": market.get("title") or rule.get("title") or "",
                "description": _truncate(market.get("description", ""), 800),
                "resolution_rules": _truncate(
                    market.get("resolution_rules") or rule.get("resolution_rules") or "",
                    1200,
                ),
                "rules_status": rule.get("rules_status")
                or ("present" if market.get("resolution_rules") else "missing"),
                "close_date": market.get("close_date"),
                "current_probability": market.get("current_probability"),
                "entity_tags": market.get("entity_tags", []),
            }
        )
    fit = run_result.get("fit") or {}
    eval_metrics = (run_result.get("eval") or {}).get("metrics", {})
    claim = run_result.get("claim") or {}
    return {
        "case_id": source["case_id"],
        "candidate_dir": str(candidate_dir),
        "source_text": source["source_text"],
        "source_type": source.get("source_type", "retrieval_candidate"),
        "retrieval_id": run_retrieval.get("retrieval_id") or retrieval.get("retrieval_id"),
        "snapshot_id": run_retrieval.get("snapshot_id") or retrieval.get("snapshot_id"),
        "as_of_ts": run_retrieval.get("as_of_ts") or retrieval.get("as_of_ts"),
        "normalized_claim": claim,
        "agent_proposed_fit": {
            "recommended_market_id": fit.get("recommended_market_id"),
            "proposed_fit_class": fit.get("semantic_fit_class"),
            "fit_reason": fit.get("fit_reason"),
            "captures": fit.get("captures", []),
            "misses": fit.get("misses", []),
            "rejected_markets": fit.get("rejected_markets", []),
        },
        "eval_metrics": {
            "false_strong_recommendation": eval_metrics.get("false_strong_recommendation"),
            "weak_proxy_detected": eval_metrics.get("weak_proxy_detected"),
            "unsupported_implication": eval_metrics.get("unsupported_implication"),
        },
        "markets": market_rows,
        "rules_status_summary": _rules_status_summary(market_rows),
    }


def _normalize_model_suggestion(
    model_output: object,
    *,
    packet: dict[str, Any],
    runtime_name: str,
) -> dict[str, Any] | None:
    if not isinstance(model_output, dict):
        return None
    if any(key in model_output for key in FORBIDDEN_OUTPUT_KEYS):
        return None
    status = str(model_output.get("suggested_review_status") or "")
    priority = str(model_output.get("review_priority") or "")
    if status not in REVIEW_STATUSES or priority not in REVIEW_PRIORITIES:
        return None
    issues = _normalize_issues(model_output.get("likely_issues"))
    markets_to_inspect = _normalize_market_ids(
        model_output.get("markets_to_inspect"),
        packet=packet,
    )
    rationale = str(model_output.get("judge_rationale") or "").strip()
    if not rationale:
        return None
    suggestion = _base_suggestion(
        packet=packet,
        triage_source="google-adk",
        model=runtime_name,
    )
    suggestion.update(
        {
            "review_priority": priority,
            "suggested_review_status": status,
            "suggested_fit_risk": _normalize_fit_risk(
                model_output.get("suggested_fit_risk")
            ),
            "likely_issues": issues,
            "markets_to_inspect": markets_to_inspect,
            "market_scores": _market_scores(
                packet, markets_to_inspect=markets_to_inspect
            ),
            "judge_rationale": rationale,
            "needs_human_check": True,
            "must_not_promote_without": _normalize_string_list(
                model_output.get("must_not_promote_without")
            )
            or [
                "frozen resolution rules",
                "human adjudication",
                "rejected-market note",
            ],
        }
    )
    return _strip_forbidden_keys(suggestion)


def _local_rule_suggestion(packet: dict[str, Any]) -> dict[str, Any]:
    rules_summary = packet["rules_status_summary"]
    fit = packet["agent_proposed_fit"]
    metrics = packet["eval_metrics"]
    issues: list[str] = []
    if rules_summary.get("missing", 0):
        issues.append("missing_resolution_rules")
    if _looks_off_topic(packet):
        issues.append("off_topic_market")
    if _is_compound(packet["source_text"]):
        issues.append("compound_thesis")
    if metrics.get("false_strong_recommendation") or fit.get("proposed_fit_class") == "weak_proxy":
        issues.append("weak_proxy_risk")
    if _mentions_wrong_metric(fit):
        issues.append("wrong_metric")
    if not issues:
        issues.append("clean_candidate")

    if "off_topic_market" in issues and fit.get("proposed_fit_class") == "no_clean_expression":
        status = "reject"
    elif "missing_resolution_rules" in issues:
        status = "needs_more_rules"
    elif "weak_proxy_risk" in issues or "compound_thesis" in issues:
        status = "candidate_only"
    else:
        status = "candidate_only"

    priority = "high" if {"off_topic_market", "weak_proxy_risk"} & set(issues) else "medium"
    markets_to_inspect = _default_markets_to_inspect(packet)
    rationale = _local_rationale(packet, issues=issues, status=status)
    suggestion = _base_suggestion(
        packet=packet,
        triage_source="local_rule_fallback",
        model="none",
    )
    suggestion.update(
        {
            "review_priority": priority,
            "suggested_review_status": status,
            "suggested_fit_risk": _local_fit_risk(fit),
            "likely_issues": sorted(set(issues), key=issues.index),
            "markets_to_inspect": markets_to_inspect,
            "market_scores": _market_scores(
                packet, markets_to_inspect=markets_to_inspect
            ),
            "judge_rationale": rationale,
            "needs_human_check": True,
            "must_not_promote_without": [
                "frozen resolution rules",
                "human adjudication",
                "rejected-market note",
            ],
        }
    )
    return suggestion


def _base_suggestion(
    *,
    packet: dict[str, Any],
    triage_source: str,
    model: str,
) -> dict[str, Any]:
    return {
        "schema_version": "candidate_triage_suggestion_v0",
        "judge_version": JUDGE_VERSION,
        "candidate_id": packet["case_id"],
        "candidate_dir": packet["candidate_dir"],
        "triaged_at_utc": datetime.now(UTC).isoformat(),
        "triage_source": triage_source,
        "model": model,
        "canonical_truth": False,
        "writes_strict_expected_labels": False,
    }


def _candidate_dirs(root: Path, *, case_id: str = "") -> list[Path]:
    if not root.exists():
        return []
    pattern = f"*/{case_id}/source.json" if case_id else "*/*/source.json"
    return sorted(
        path.parent
        for path in root.glob(pattern)
        if (path.parent / "retrieval_result.json").exists()
    )


def _rules_status_summary(markets: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for market in markets:
        status = str(market.get("rules_status") or "unknown")
        summary[status] = summary.get(status, 0) + 1
    return summary


def _normalize_issues(raw: object) -> list[str]:
    issues = [
        issue
        for issue in _normalize_string_list(raw)
        if issue in LIKELY_ISSUES
    ]
    return issues or ["resolution_risk"]


def _normalize_market_ids(raw: object, *, packet: dict[str, Any]) -> list[str]:
    valid_ids = {market["market_id"] for market in packet["markets"]}
    ids = [market_id for market_id in _normalize_string_list(raw) if market_id in valid_ids]
    return ids or _default_markets_to_inspect(packet)


def _normalize_fit_risk(raw: object) -> str:
    value = str(raw or "").strip()
    allowed = {
        "likely_direct",
        "likely_indirect",
        "likely_weak_proxy",
        "likely_no_clean_expression",
        "unclear",
    }
    return value if value in allowed else "unclear"


def _normalize_string_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _strip_forbidden_keys(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in FORBIDDEN_OUTPUT_KEYS}


def _looks_off_topic(packet: dict[str, Any]) -> bool:
    source_tokens = _semantic_tokens(packet["source_text"])
    if not source_tokens:
        return False
    inspected = packet["markets"][:5]
    if not inspected:
        return True
    overlapping = 0
    for market in inspected:
        market_tokens = _semantic_tokens(
            " ".join(
                [
                    market.get("title") or "",
                    market.get("description") or "",
                    " ".join(market.get("entity_tags") or []),
                ]
            )
        )
        if source_tokens & market_tokens:
            overlapping += 1
    return overlapping == 0


def _semantic_tokens(text: str) -> set[str]:
    stopwords = {
        "about",
        "after",
        "before",
        "from",
        "have",
        "into",
        "more",
        "that",
        "their",
        "there",
        "this",
        "will",
        "with",
        "would",
        "year",
    }
    return {
        token
        for token in "".join(char.lower() if char.isalnum() else " " for char in text).split()
        if len(token) > 3 and token not in stopwords
    }


def _is_compound(text: str) -> bool:
    lowered = text.lower()
    return bool(
        lowered.count(" and ") >= 2
        or "," in lowered
        or any(token in lowered for token in ("package", "bundle", "while", "if "))
    )


def _mentions_wrong_metric(fit: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(fit.get("fit_reason") or ""),
            " ".join(fit.get("misses") or []),
        ]
    ).lower()
    return any(token in text for token in ("metric", "proxy", "not resolve", "wrong"))


def _default_markets_to_inspect(packet: dict[str, Any]) -> list[str]:
    recommended = packet["agent_proposed_fit"].get("recommended_market_id")
    if recommended:
        return [str(recommended)]
    return [market["market_id"] for market in packet["markets"][:3]]


def _market_scores(
    packet: dict[str, Any], *, markets_to_inspect: list[str]
) -> list[dict[str, Any]]:
    source_tokens = _semantic_tokens(packet["source_text"])
    recommended = packet["agent_proposed_fit"].get("recommended_market_id")
    inspect_ids = set(markets_to_inspect)
    rows = []
    for market in packet["markets"]:
        market_text = " ".join(
            [
                market.get("title") or "",
                market.get("description") or "",
                market.get("resolution_rules") or "",
                " ".join(market.get("entity_tags") or []),
            ]
        )
        market_tokens = _semantic_tokens(market_text)
        overlap = len(source_tokens & market_tokens)
        denominator = max(len(source_tokens), 1)
        score = min(55, round((overlap / denominator) * 55))
        if market["market_id"] == recommended:
            score += 25
        if market["market_id"] in inspect_ids:
            score += 15
        if market.get("rules_status") == "missing":
            score -= 10
        score = max(0, min(100, score))
        rows.append(
            {
                "market_id": market["market_id"],
                "review_score": score,
            }
        )
    return sorted(rows, key=lambda row: row["review_score"], reverse=True)


def _local_fit_risk(fit: dict[str, Any]) -> str:
    fit_class = fit.get("proposed_fit_class")
    if fit_class == "direct":
        return "likely_direct"
    if fit_class == "indirect":
        return "likely_indirect"
    if fit_class == "weak_proxy":
        return "likely_weak_proxy"
    if fit_class == "no_clean_expression":
        return "likely_no_clean_expression"
    return "unclear"


def _local_rationale(
    packet: dict[str, Any],
    *,
    issues: list[str],
    status: str,
) -> str:
    parts = [
        f"Local triage suggests `{status}` for `{packet['case_id']}`.",
        f"Detected issues: {', '.join(issues)}.",
    ]
    fit = packet["agent_proposed_fit"]
    if fit.get("fit_reason"):
        parts.append(f"Agent fit reason: {fit['fit_reason']}")
    return " ".join(parts)


def _truncate(value: object, limit: int) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


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
    raise SystemExit(asyncio.run(main()))
