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

from app.config import settings
from app.market_provider import _load_polydata_class

DEFAULT_CANDIDATES_DIR = Path("evals/retrieval_candidates")
DEFAULT_OUTPUT = DEFAULT_CANDIDATES_DIR / "rules_backfill_report.json"
RULES_SOURCE = "polydata.markets.description"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill retrieval-candidate market rules from current PolyData metadata."
    )
    parser.add_argument("--candidates-dir", default=str(DEFAULT_CANDIDATES_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be updated without writing candidate packet files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_dirs = _candidate_dirs(Path(args.candidates_dir))
    if not candidate_dirs:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "No retrieval candidate packets found.",
                    "candidates_dir": args.candidates_dir,
                },
                indent=2,
            )
        )
        return 1
    if not settings.poly_data_sas_token:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "POLY_DATA_SAS_TOKEN is required to backfill rules.",
                },
                indent=2,
            )
        )
        return 2

    market_ids = _collect_market_ids(candidate_dirs)
    rules_lookup = _load_polydata_rules(market_ids)
    backfilled_at_utc = datetime.now(UTC).isoformat()
    case_summaries = [
        backfill_candidate_dir(
            candidate_dir,
            rules_lookup=rules_lookup,
            backfilled_at_utc=backfilled_at_utc,
            dry_run=args.dry_run,
        )
        for candidate_dir in candidate_dirs
    ]
    report = _report(
        candidate_dirs=candidate_dirs,
        market_ids=market_ids,
        case_summaries=case_summaries,
        backfilled_at_utc=backfilled_at_utc,
        dry_run=args.dry_run,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


def backfill_candidate_dir(
    candidate_dir: Path,
    *,
    rules_lookup: dict[str, dict[str, Any]],
    backfilled_at_utc: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    source = _read_json(candidate_dir / "source.json")
    market_path = candidate_dir / "market_snapshots.jsonl"
    rules_path = candidate_dir / "market_rules_snapshots.jsonl"
    markets = _read_jsonl(market_path)
    rules = _read_jsonl(rules_path)
    run_result = _read_optional_json(candidate_dir / "run_result.json") or {}
    run_retrieval = run_result.get("market_retrieval") or {}
    agent_market_ids = [
        str(market_id)
        for market_id in run_retrieval.get("market_ids_considered") or []
    ]

    updated_markets: list[dict[str, Any]] = []
    updated_rules: list[dict[str, Any]] = []
    per_market: list[dict[str, Any]] = []

    for market in markets:
        market_id = str(market.get("market_id", ""))
        rule_payload = rules_lookup.get(market_id, {})
        description = _clean_text(rule_payload.get("description"))
        was_missing = not _clean_text(market.get("resolution_rules"))
        if description:
            market = {
                **market,
                "resolution_rules": description,
                "known_fit_risks": [
                    risk
                    for risk in market.get("known_fit_risks", [])
                    if risk != "missing_resolution_rules"
                ],
            }
        updated_markets.append(market)
        per_market.append(
            {
                "market_id": market_id,
                "found_in_polydata": bool(rule_payload),
                "rules_status_after": "present" if description else "missing",
                "was_missing_before": was_missing,
                "backfilled": bool(description and was_missing),
                "title": rule_payload.get("question") or market.get("title"),
            }
        )

    rule_by_id = {str(rule.get("market_id", "")): rule for rule in rules}
    market_ids = [str(market.get("market_id", "")) for market in markets]
    for market_id in market_ids:
        existing = dict(rule_by_id.get(market_id, {"market_id": market_id}))
        rule_payload = rules_lookup.get(market_id, {})
        updated_rules.append(
            _backfilled_rule_record(
                existing=existing,
                market_id=market_id,
                rule_payload=rule_payload,
                retrieval_metadata={},
                backfilled_at_utc=backfilled_at_utc,
            )
        )

    agent_rules: list[dict[str, Any]] = []
    agent_per_market: list[dict[str, Any]] = []
    for market_id in agent_market_ids:
        rule_payload = rules_lookup.get(market_id, {})
        record = _backfilled_rule_record(
            existing={"market_id": market_id},
            market_id=market_id,
            rule_payload=rule_payload,
            retrieval_metadata=run_retrieval,
            backfilled_at_utc=backfilled_at_utc,
        )
        agent_rules.append(record)
        agent_per_market.append(
            {
                "market_id": market_id,
                "found_in_polydata": bool(rule_payload),
                "rules_status_after": record["rules_status"],
                "title": rule_payload.get("question"),
            }
        )

    if not dry_run:
        _write_jsonl(market_path, updated_markets)
        _write_jsonl(rules_path, updated_rules)
        if agent_rules:
            _write_jsonl(candidate_dir / "agent_market_rules_snapshots.jsonl", agent_rules)

    backfilled_count = sum(1 for item in per_market if item["backfilled"])
    present_after = sum(1 for item in per_market if item["rules_status_after"] == "present")
    missing_after = sum(1 for item in per_market if item["rules_status_after"] == "missing")
    agent_present_after = sum(
        1 for item in agent_per_market if item["rules_status_after"] == "present"
    )
    agent_missing_after = sum(
        1 for item in agent_per_market if item["rules_status_after"] == "missing"
    )
    return {
        "case_id": source.get("case_id", candidate_dir.name),
        "candidate_dir": str(candidate_dir),
        "market_count": len(markets),
        "backfilled_count": backfilled_count,
        "rules_present_after": present_after,
        "rules_missing_after": missing_after,
        "markets": per_market,
        "agent_market_count": len(agent_market_ids),
        "agent_rules_present_after": agent_present_after,
        "agent_rules_missing_after": agent_missing_after,
        "agent_markets": agent_per_market,
    }


def _load_polydata_rules(market_ids: set[str]) -> dict[str, dict[str, Any]]:
    PolyData = _load_polydata_class()
    poly = PolyData(settings.poly_data_sas_token, exchange=settings.poly_data_exchange)
    markets = poly.markets()
    columns = [
        column
        for column in (
            "id",
            "question",
            "description",
            "resolution_source",
            "question_id",
            "market_slug",
            "condition_id",
        )
        if column in markets.columns
    ]
    rows = markets.select(columns).to_dicts()
    return {
        str(row.get("id")): row
        for row in rows
        if str(row.get("id")) in market_ids
    }


def _report(
    *,
    candidate_dirs: list[Path],
    market_ids: set[str],
    case_summaries: list[dict[str, Any]],
    backfilled_at_utc: str,
    dry_run: bool,
) -> dict[str, Any]:
    backfilled = sum(case["backfilled_count"] for case in case_summaries)
    market_rows = sum(case["market_count"] for case in case_summaries)
    present = sum(case["rules_present_after"] for case in case_summaries)
    missing = sum(case["rules_missing_after"] for case in case_summaries)
    agent_market_rows = sum(case["agent_market_count"] for case in case_summaries)
    agent_present = sum(case["agent_rules_present_after"] for case in case_summaries)
    agent_missing = sum(case["agent_rules_missing_after"] for case in case_summaries)
    return {
        "status": "dry_run" if dry_run else "ok",
        "mode": "dry_run" if dry_run else "write",
        "rules_source": RULES_SOURCE,
        "backfilled_at_utc": backfilled_at_utc,
        "candidate_count": len(candidate_dirs),
        "market_row_count": market_rows,
        "unique_market_count": len(market_ids),
        "backfilled_market_rows": backfilled,
        "rules_present_after": present,
        "rules_missing_after": missing,
        "agent_market_row_count": agent_market_rows,
        "agent_rules_present_after": agent_present,
        "agent_rules_missing_after": agent_missing,
        "cases": case_summaries,
    }


def _candidate_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path.parent
        for path in root.glob("*/*/source.json")
        if (path.parent / "market_rules_snapshots.jsonl").exists()
        and (path.parent / "market_snapshots.jsonl").exists()
    )


def _collect_market_ids(candidate_dirs: list[Path]) -> set[str]:
    market_ids: set[str] = set()
    for candidate_dir in candidate_dirs:
        for row in _read_jsonl(candidate_dir / "market_rules_snapshots.jsonl"):
            if row.get("market_id"):
                market_ids.add(str(row["market_id"]))
        run_result = _read_optional_json(candidate_dir / "run_result.json") or {}
        run_retrieval = run_result.get("market_retrieval") or {}
        for market_id in run_retrieval.get("market_ids_considered") or []:
            market_ids.add(str(market_id))
    return market_ids


def _backfilled_rule_record(
    *,
    existing: dict[str, Any],
    market_id: str,
    rule_payload: dict[str, Any],
    retrieval_metadata: dict[str, Any],
    backfilled_at_utc: str,
) -> dict[str, Any]:
    record = dict(existing)
    record["market_id"] = market_id
    for key in ("retrieval_id", "snapshot_id", "as_of_ts"):
        if retrieval_metadata.get(key) and not record.get(key):
            record[key] = retrieval_metadata[key]
    description = _clean_text(rule_payload.get("description"))
    if description:
        record["resolution_rules"] = description
        record["rules_status"] = "present"
        record["rules_source"] = RULES_SOURCE
        record["rules_backfilled_at_utc"] = backfilled_at_utc
        if rule_payload.get("resolution_source"):
            record["resolution_source"] = rule_payload["resolution_source"]
        if rule_payload.get("question_id"):
            record["question_id"] = rule_payload["question_id"]
        if rule_payload.get("condition_id"):
            record["condition_id"] = rule_payload["condition_id"]
        if rule_payload.get("market_slug"):
            record["market_slug"] = rule_payload["market_slug"]
    else:
        record["resolution_rules"] = _clean_text(record.get("resolution_rules"))
        record["rules_status"] = record.get("rules_status") or "missing"
        record["rules_backfill_status"] = (
            "description_missing" if rule_payload else "market_not_found"
        )
        record["rules_backfilled_at_utc"] = backfilled_at_utc
    return record


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
