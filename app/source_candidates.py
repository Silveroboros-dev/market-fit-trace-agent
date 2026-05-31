from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCE_CANDIDATE_PACKS = {
    "market_fit_v2_candidates": ROOT / "evals" / "market_fit_v2_candidates",
    "market_fit_v3_candidates": ROOT / "evals" / "market_fit_v3_candidates",
}


def list_source_candidate_rows(
    packs: dict[str, Path] | None = None,
) -> dict[str, Any]:
    candidate_packs = packs or DEFAULT_SOURCE_CANDIDATE_PACKS
    rows: list[dict[str, Any]] = []
    pack_summaries: list[dict[str, Any]] = []

    for pack_name, pack_dir in candidate_packs.items():
        examples_path = pack_dir / "examples.jsonl"
        expected_path = pack_dir / "expected_outputs.jsonl"
        examples = _read_jsonl(examples_path)
        expected_by_id = {
            row.get("example_id"): row
            for row in _read_jsonl(expected_path)
            if row.get("example_id")
        }
        pack_summaries.append(
            {
                "pack": pack_name,
                "path": _repo_relative(pack_dir),
                "row_count": len(examples),
                "status": "candidate_pack",
                "canonical_truth": False,
            }
        )
        for example in examples:
            example_id = example.get("example_id", "")
            expected = expected_by_id.get(example_id, {})
            expected_fit = expected.get("expected_fit", {})
            provenance = example.get("source_provenance", {})
            rows.append(
                {
                    "source_case_key": f"{pack_name}::{example_id}",
                    "pack": pack_name,
                    "example_id": example_id,
                    "schema_version": example.get("schema_version"),
                    "as_of_ts": example.get("as_of_ts"),
                    "source_type": example.get("source_type"),
                    "source_text": example.get("source_text", ""),
                    "source_provenance": provenance,
                    "source_name": provenance.get("source_name"),
                    "source_url": provenance.get("source_url"),
                    "fetch_status": provenance.get("fetch_status"),
                    "labels": example.get("labels", {}),
                    "market_snapshot_ref": example.get("market_snapshot_ref", {}),
                    "market_rules_snapshot_ref": example.get(
                        "market_rules_snapshot_ref", {}
                    ),
                    "proposed_fit_class": expected_fit.get("semantic_fit_class"),
                    "proposed_best_market_id": expected_fit.get("best_market_id"),
                    "proposed_case_tags": expected_fit.get("case_tags", []),
                    "canonical_truth": False,
                    "strict_expected_labels_present": False,
                    "source_truth_scope": "source_text_and_provenance_only",
                }
            )

    rows.sort(key=lambda row: (row["pack"], row["example_id"]))
    return {
        "source_candidate_count": len(rows),
        "truth_scope": "source_text_and_provenance_only",
        "canonical_truth": False,
        "packs": pack_summaries,
        "rows": rows,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
