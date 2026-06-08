from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402

DEFAULT_OUT_DIR = Path("evals/failure_candidates")
SCHEMA_VERSION = "failure_eval_candidate_v0"
POLICY_PROPOSAL_VERSION = "policy_pr_candidate_v0"
FAILURE_METRICS = (
    "false_strong_recommendation",
    "unsupported_implication",
    "causal_mechanism_mismatch",
    "resolution_target_mismatch",
    "horizon_mismatch",
    "entity_mismatch",
    "no_clean_expression_expected",
)
HUMAN_REVIEW_OPTIONS = (
    "promote_to_strict_golden_candidate",
    "needs_more_rules",
    "candidate_only",
    "disregard",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a failed run into candidate-only eval memory and a PR-ready "
            "policy proposal for human review."
        )
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--ledger-store-path",
        default=str(settings.ledger_store_path),
        help="Path to the local LedgerStore JSON file.",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing candidate packet for the same run id.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = export_failure_eval_candidate(
            run_id=args.run_id,
            ledger_store_path=Path(args.ledger_store_path),
            out_dir=Path(args.out_dir),
            force=args.force,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                    "run_id": args.run_id,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def export_failure_eval_candidate(
    *,
    run_id: str,
    ledger_store_path: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    force: bool = False,
) -> dict[str, Any]:
    ledger = _read_ledger(ledger_store_path)
    packet = build_failure_eval_packet(ledger=ledger, run_id=run_id)
    candidate_dir = out_dir / datetime.now(UTC).date().isoformat() / run_id
    if candidate_dir.exists() and not force:
        raise FileExistsError(
            f"Candidate packet already exists: {candidate_dir}. Re-run with --force."
        )
    candidate_dir.mkdir(parents=True, exist_ok=True)

    _write_json(candidate_dir / "source.json", packet["source"])
    _write_json(candidate_dir / "run_result.json", packet["run_result"])
    _write_json(candidate_dir / "failure_signal.json", packet["failure_signal"])
    _write_json(candidate_dir / "proposed_eval_case.json", packet["proposed_eval_case"])
    (candidate_dir / "policy_gap.md").write_text(
        _policy_gap_markdown(packet),
        encoding="utf-8",
    )
    (candidate_dir / "PR_DESCRIPTION.md").write_text(
        _pr_description_markdown(packet),
        encoding="utf-8",
    )
    (candidate_dir / "review_notes.md").write_text(
        _review_notes_markdown(packet),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "policy_proposal_version": POLICY_PROPOSAL_VERSION,
        "run_id": run_id,
        "candidate_dir": str(candidate_dir),
        "failure_metrics": packet["failure_signal"]["triggered_metrics"],
        "human_review_options": list(HUMAN_REVIEW_OPTIONS),
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
    }


def build_failure_eval_packet(
    *, ledger: dict[str, list[dict[str, Any]]], run_id: str
) -> dict[str, Any]:
    run = dict(_find(ledger, "agent_runs", run_id))
    claim = _latest(
        [item for item in ledger.get("claims", []) if item.get("run_id") == run_id],
        f"No claim found for run_id={run_id}",
    )
    source = dict(_find(ledger, "sources", claim["source_id"]))
    fit = _latest(
        [
            item
            for item in ledger.get("market_fit_records", [])
            if item.get("claim_id") == claim["id"]
        ],
        f"No market-fit record found for claim_id={claim['id']}",
    )
    eval_record = _latest(
        [item for item in ledger.get("eval_results", []) if item.get("run_id") == run_id],
        f"No eval record found for run_id={run_id}",
    )
    metrics = _loads_dict(eval_record.get("metrics_json"))
    triggered_metrics = [
        key for key in FAILURE_METRICS if bool(metrics.get(key))
    ]
    if not triggered_metrics:
        triggered_metrics = ["review_requested_no_failure_metric"]
    retrieval = _latest_event_payload(
        ledger,
        run_id=run_id,
        event_type="market_retrieval_run",
    )

    normalized_claim = {
        "claim_id": claim["id"],
        "claim_text": claim["claim_text"],
        "entities": _loads_list(claim.get("entities_json")),
        "horizon": claim.get("horizon"),
        "stance": claim.get("stance"),
        "confidence": claim.get("confidence"),
        "reasoning_summary": claim.get("reasoning_summary"),
    }
    current_fit = {
        "fit_record_id": fit["id"],
        "recommended_market_id": fit.get("recommended_market_id"),
        "semantic_fit_class": _fit_value(fit.get("semantic_fit_class")),
        "fit_reason": fit.get("fit_reason"),
        "supporting_outcome": fit.get("supporting_outcome"),
        "polarity": fit.get("polarity"),
        "captures": _loads_list(fit.get("captures_json")),
        "misses": _loads_list(fit.get("misses_json")),
        "rejected_markets": _loads_list(fit.get("rejected_markets_json")),
    }
    market_ids = list(retrieval.get("market_ids_considered") or [])
    proposed_target = _proposed_target_fit_class(
        metrics=metrics,
        current_fit_class=current_fit["semantic_fit_class"],
    )

    trace_id = eval_record.get("phoenix_trace_id") or run.get("phoenix_trace_id")
    failure_signal = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "claim_id": claim["id"],
        "phoenix_trace_id": trace_id,
        "phoenix_trace_url": _phoenix_trace_url(trace_id),
        "failure_summary": eval_record.get("failure_summary"),
        "triggered_metrics": triggered_metrics,
        "metrics": metrics,
        "observed_fit_class": current_fit["semantic_fit_class"],
        "observed_recommended_market_id": current_fit["recommended_market_id"],
        "candidate_only": True,
    }
    proposed_eval_case = {
        "schema_version": SCHEMA_VERSION,
        "policy_proposal_version": POLICY_PROPOSAL_VERSION,
        "case_id": f"failure-{run_id}",
        "source_kind": "failure_trace_candidate",
        "truth_scope": "failure_candidate",
        "canonical_truth": False,
        "writes_strict_expected_labels": False,
        "writes_policy_code": False,
        "human_review_required": True,
        "human_review_options": list(HUMAN_REVIEW_OPTIONS),
        "recommended_default_review": _default_review(triggered_metrics),
        "disregard_when": [
            "the failure is duplicate noise",
            "the source text is malformed or not reviewable",
            "the market context is incomplete enough that no useful eval can be frozen",
            "the reviewer cannot assign a defensible expected behavior",
        ],
        "source_text": source["raw_text"],
        "normalized_claim": normalized_claim,
        "candidate_market_ids": market_ids,
        "observed_fit": current_fit,
        "proposed_target_fit_class": proposed_target,
        "promotion_blockers": [
            "human_review_status_pending",
            "strict_expected_labels_not_locked",
            "candidate_packet_not_promoted",
        ],
        "policy_gap_summary": _policy_gap_summary(
            metrics=metrics,
            current_fit=current_fit,
            proposed_target=proposed_target,
        ),
    }
    run_result = {
        "run": run,
        "source": {
            "source_id": source["id"],
            "title": source.get("title"),
            "source_type": source.get("source_type"),
            "raw_text": source.get("raw_text"),
        },
        "claim": normalized_claim,
        "fit": current_fit,
        "eval": {
            "eval_record_id": eval_record["id"],
            "phoenix_trace_id": eval_record.get("phoenix_trace_id"),
            "failure_summary": eval_record.get("failure_summary"),
            "metrics": metrics,
        },
        "market_retrieval": retrieval,
    }
    source_packet = {
        "schema_version": SCHEMA_VERSION,
        "case_id": f"failure-{run_id}",
        "source_type": "failure_trace_candidate",
        "source_text": source["raw_text"],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "source_id": source["id"],
        "claim_id": claim["id"],
        "canonical_truth": False,
    }
    return {
        "source": source_packet,
        "run_result": run_result,
        "failure_signal": failure_signal,
        "proposed_eval_case": proposed_eval_case,
    }


def _proposed_target_fit_class(*, metrics: dict[str, Any], current_fit_class: str) -> str:
    if metrics.get("false_strong_recommendation"):
        return "weak_proxy"
    if metrics.get("entity_mismatch") or metrics.get("no_clean_expression_expected"):
        return "no_clean_expression"
    if metrics.get("unsupported_implication") or metrics.get("causal_mechanism_mismatch"):
        return "weak_proxy"
    if metrics.get("resolution_target_mismatch") or metrics.get("horizon_mismatch"):
        return "indirect"
    return current_fit_class or "needs_human_review"


def _default_review(triggered_metrics: list[str]) -> str:
    if "review_requested_no_failure_metric" in triggered_metrics:
        return "disregard"
    if "false_strong_recommendation" in triggered_metrics:
        return "promote_to_strict_golden_candidate"
    return "candidate_only"


def _policy_gap_summary(
    *,
    metrics: dict[str, Any],
    current_fit: dict[str, Any],
    proposed_target: str,
) -> str:
    current = current_fit.get("semantic_fit_class") or "unknown"
    recommended = current_fit.get("recommended_market_id") or "none"
    if metrics.get("false_strong_recommendation"):
        return (
            f"Observed `{current}` recommendation `{recommended}` was flagged false-strong. "
            f"Proposed reviewed target is `{proposed_target}`."
        )
    return (
        f"Observed `{current}` recommendation `{recommended}` triggered failure metrics. "
        f"Proposed reviewed target is `{proposed_target}`."
    )


def _policy_gap_markdown(packet: dict[str, Any]) -> str:
    proposed = packet["proposed_eval_case"]
    signal = packet["failure_signal"]
    fit = proposed["observed_fit"]
    trace_ref = signal.get("phoenix_trace_url") or signal.get("phoenix_trace_id") or "n/a"
    return "\n".join(
        [
            f"# Policy Gap Candidate: {proposed['case_id']}",
            "",
            "## Failure Signal",
            "",
            f"- Triggered metrics: {', '.join(signal['triggered_metrics'])}",
            f"- Observed fit class: `{fit.get('semantic_fit_class')}`",
            f"- Observed recommended market: `{fit.get('recommended_market_id') or 'none'}`",
            f"- Proposed target fit class: `{proposed['proposed_target_fit_class']}`",
            f"- Phoenix trace: {trace_ref}",
            "",
            "## Proposed Policy Direction",
            "",
            proposed["policy_gap_summary"],
            "",
            "Do not apply this automatically. A reviewer must decide whether this is a",
            "real policy gap, a duplicate, bad source text, or incomplete market context.",
            "",
            "## Human Review Outcomes",
            "",
            "- `promote_to_strict_golden_candidate`: freeze expected behavior in a reviewed pack.",
            "- `needs_more_rules`: backfill or inspect resolution rules before deciding.",
            "- `candidate_only`: keep as trace evidence but do not make it strict truth.",
            "- `disregard`: explicitly reject the candidate as noise or not useful.",
            "",
            "## Test Plan Candidate",
            "",
            "- Add/confirm a deterministic eval that fails on the observed behavior.",
            "- Confirm the proposed target class does not create a false direct/indirect upgrade.",
            "- Run `make evals` and any focused policy tests before changing policy code.",
            "",
        ]
    )


def _pr_description_markdown(packet: dict[str, Any]) -> str:
    proposed = packet["proposed_eval_case"]
    return "\n".join(
        [
            f"# PR Candidate: Guard {proposed['case_id']}",
            "",
            "## Why",
            "",
            proposed["policy_gap_summary"],
            "",
            "## Scope",
            "",
            "- Candidate eval memory only.",
            "- No automatic mutation of `expected_outputs.jsonl`.",
            "- No automatic mutation of deterministic policy code.",
            "",
            "## Reviewer Decision",
            "",
            "Choose one: promote to strict-golden candidate, needs more rules,",
            "candidate only, or disregard.",
            "",
        ]
    )


def _review_notes_markdown(packet: dict[str, Any]) -> str:
    proposed = packet["proposed_eval_case"]
    return "\n".join(
        [
            f"# Review Notes: {proposed['case_id']}",
            "",
            "## Decision",
            "",
            "- Status: TODO (`promote_to_strict_golden_candidate` / "
            "`needs_more_rules` / `candidate_only` / `disregard`)",
            "- Reviewer: TODO",
            "- Rationale: TODO",
            "",
            "## Disregard Checklist",
            "",
            "- Duplicate failure candidate?",
            "- Malformed source or missing provenance?",
            "- Incomplete market context?",
            "- No defensible expected behavior?",
            "",
        ]
    )


def _read_ledger(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError(f"Ledger store not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _find(
    ledger: dict[str, list[dict[str, Any]]],
    collection: str,
    item_id: str,
) -> dict[str, Any]:
    for item in ledger.get(collection, []):
        if item.get("id") == item_id:
            return item
    raise KeyError(f"{collection} item not found: {item_id}")


def _latest(rows: list[dict[str, Any]], error_message: str) -> dict[str, Any]:
    if not rows:
        raise KeyError(error_message)
    return dict(rows[-1])


def _latest_event_payload(
    ledger: dict[str, list[dict[str, Any]]],
    *,
    run_id: str,
    event_type: str,
) -> dict[str, Any]:
    events = [
        event
        for event in ledger.get("ledger_events", [])
        if event.get("run_id") == run_id and event.get("event_type") == event_type
    ]
    if not events:
        return {}
    payload = events[-1].get("event_payload_json") or {}
    return payload if isinstance(payload, dict) else {}


def _loads_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _loads_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    return []


def _fit_value(raw: object) -> str:
    text = str(raw or "")
    return text.split(".")[-1] if "." in text else text


def _phoenix_trace_url(trace_id: object) -> str | None:
    if not trace_id or not settings.phoenix_base_url:
        return None
    return f"{settings.phoenix_base_url.rstrip('/')}/traces/{trace_id}"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
