from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.candidate_review import DEFAULT_CANDIDATES_DIR, load_candidate_review_detail
from app.models import RunResult


def export_current_run_candidate(
    *,
    source_text: str,
    run: RunResult,
    case_id: str | None = None,
    source_assisted: dict[str, Any] | None = None,
    candidates_dir: Path = DEFAULT_CANDIDATES_DIR,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    candidate_id = case_id or _case_id(source_text, run.run_id, now)
    candidate_dir = candidates_dir / now.date().isoformat() / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    retrieval = run.market_retrieval.model_dump() if run.market_retrieval else {}
    market_ids = retrieval.get("market_ids_considered") or [
        market.market_id for market in run.market_context
    ]
    retrieval_payload = {
        "mode": retrieval.get("mode") or "run_context",
        "snapshot_id": retrieval.get("snapshot_id"),
        "as_of_ts": retrieval.get("as_of_ts"),
        "retrieval_id": retrieval.get("retrieval_id"),
        "query_summary": retrieval.get("query_summary", {}),
        "excluded_summary": retrieval.get("excluded_summary", {}),
        "market_ids_considered": market_ids,
        "raw_markets": [],
    }

    _write_json(
        candidate_dir / "source.json",
        {
            "case_id": candidate_id,
            "source_text": source_text,
            "source_type": (
                "source_assisted_current_run_candidate"
                if source_assisted
                else "ui_current_run_candidate"
            ),
            "created_at_utc": now.isoformat(),
            "source_run_id": run.run_id,
            "source_trace_id": run.phoenix_trace_id,
            "source_assisted": source_assisted,
            "source_truth_scope": (
                "source_text_and_provenance_only"
                if source_assisted
                else "manual_source_text_only"
            ),
        },
    )
    _write_json(candidate_dir / "retrieval_result.json", retrieval_payload)
    _write_jsonl(
        candidate_dir / "market_snapshots.jsonl",
        [market.model_dump() for market in run.market_context],
    )
    rules_rows = [
        {
            "market_id": market.market_id,
            "title": market.title,
            "resolution_rules": market.resolution_rules,
            "rules_status": "present" if market.resolution_rules else "missing",
            "retrieval_id": retrieval_payload["retrieval_id"],
            "snapshot_id": retrieval_payload["snapshot_id"],
            "as_of_ts": retrieval_payload["as_of_ts"],
        }
        for market in run.market_context
    ]
    _write_jsonl(candidate_dir / "market_rules_snapshots.jsonl", rules_rows)
    _write_jsonl(candidate_dir / "agent_market_rules_snapshots.jsonl", rules_rows)
    _write_json(candidate_dir / "run_result.json", _run_summary(run))

    notes_path = candidate_dir / "review_notes.md"
    if not notes_path.exists():
        notes_path.write_text(
            "\n".join(
                [
                    f"# Retrieval Candidate: {candidate_id}",
                    "",
                    "Human review status is candidate governance metadata.",
                    "`promote` means eligible for a later frozen strict-golden promotion.",
                    "This packet does not mutate strict expected labels by itself.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return load_candidate_review_detail(candidate_id, candidates_dir=candidates_dir)


def _run_summary(run: RunResult) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "claim_id": run.claim_id,
        "source_id": run.source_id,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "phoenix_trace_id": run.phoenix_trace_id,
        "phoenix_trace_url": run.phoenix_trace_url,
        "claim": run.claim.model_dump(),
        "fit": run.fit.model_dump(mode="json"),
        "eval": run.eval.model_dump(mode="json"),
        "market_retrieval": (
            run.market_retrieval.model_dump() if run.market_retrieval else None
        ),
        "market_context_ids": [market.market_id for market in run.market_context],
    }


def _case_id(source_text: str, run_id: str, now: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", source_text.lower()).strip("-")[:42]
    suffix = run_id.removeprefix("run_")[:8]
    return f"ui-{now.strftime('%Y%m%d')}-{slug or 'candidate'}-{suffix}"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
