from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from app.market_provider import PolyDataMarketProvider
from app.models import NormalizedClaim


DEFAULT_THESIS = (
    "US and Iran will extend a ceasefire and reopen the Strait of Hormuz by the end of June."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a live PolyData retrieval as a candidate future golden."
    )
    parser.add_argument("--thesis", default=DEFAULT_THESIS)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--min-volume-usd", type=float, default=10000.0)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument("--l1", default="")
    parser.add_argument("--out-dir", default="evals/retrieval_candidates")
    parser.add_argument(
        "--run-agent",
        action="store_true",
        help="Also run the Market Fit Trace Agent and attach proposed fit/eval/trace data.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("POLY_DATA_SAS_TOKEN")
    if not token:
        print("POLY_DATA_SAS_TOKEN is required in the environment.", file=sys.stderr)
        return 2

    now = datetime.now(UTC)
    case_id = args.case_id or _case_id(args.thesis, now)
    output_dir = Path(args.out_dir) / now.date().isoformat() / case_id
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_sas_token=token,
            poly_data_exchange=os.getenv("POLY_DATA_EXCHANGE", "polymarket"),
            poly_data_l1_allowlist=tuple(
                item.strip() for item in args.l1.split(",") if item.strip()
            ),
            poly_data_min_volume_usd=args.min_volume_usd,
            poly_data_min_taxonomy_confidence=args.min_confidence,
            poly_data_top_k=args.top_k,
            poly_data_max_k=max(args.top_k, 50),
        )
    )
    claim = NormalizedClaim(
        claim_text=args.thesis,
        entities=[],
        horizon="unspecified",
        stance="unspecified",
        confidence=0.5,
    )
    retrieval = provider.retrieve(claim)

    _write_json(
        output_dir / "source.json",
        {
            "case_id": case_id,
            "source_text": args.thesis,
            "source_type": "manual_live_retrieval_candidate",
            "created_at_utc": now.isoformat(),
        },
    )
    _write_json(
        output_dir / "retrieval_result.json",
        {
            "mode": retrieval.mode,
            "snapshot_id": retrieval.snapshot_id,
            "as_of_ts": retrieval.as_of_ts,
            "retrieval_id": retrieval.retrieval_id,
            "query_summary": retrieval.query_summary,
            "excluded_summary": retrieval.excluded_summary,
            "market_ids_considered": [market.market_id for market in retrieval.markets],
            "raw_markets": retrieval.raw_markets,
        },
    )
    _write_jsonl(
        output_dir / "market_snapshots.jsonl",
        [market.model_dump() for market in retrieval.markets],
    )
    _write_jsonl(
        output_dir / "market_rules_snapshots.jsonl",
        [
            {
                "market_id": market.market_id,
                "resolution_rules": market.resolution_rules,
                "rules_status": "present" if market.resolution_rules else "missing",
                "retrieval_id": retrieval.retrieval_id,
                "snapshot_id": retrieval.snapshot_id,
                "as_of_ts": retrieval.as_of_ts,
            }
            for market in retrieval.markets
        ],
    )
    run_summary = None
    if args.run_agent:
        store = LedgerStore(output_dir / "ledger_store.json")
        agent = MarketFitTraceAgent(store=store, market_provider=provider)
        result = asyncio.run(
            agent.run(
                thesis=args.thesis,
                title=f"Retrieval candidate {case_id}",
            )
        )
        run_summary = {
            "run_id": result.run_id,
            "claim_id": result.claim_id,
            "source_id": result.source_id,
            "model": result.model,
            "prompt_version": result.prompt_version,
            "phoenix_trace_id": result.phoenix_trace_id,
            "phoenix_trace_url": result.phoenix_trace_url,
            "claim": result.claim.model_dump(),
            "fit": result.fit.model_dump(),
            "eval": result.eval.model_dump(),
            "market_retrieval": (
                result.market_retrieval.model_dump() if result.market_retrieval else None
            ),
            "market_context_ids": [market.market_id for market in result.market_context],
        }
        _write_json(output_dir / "run_result.json", run_summary)
    (output_dir / "review_notes.md").write_text(
        "\n".join(
            [
                f"# Retrieval Candidate: {case_id}",
                "",
                "## Human Review",
                "",
                "- Expected fit class: TODO",
                "- Best market id: TODO",
                "- Acceptable market ids: TODO",
                "- Adjacent / tempting wrong market ids: TODO",
                "- Review note: TODO",
                "",
                "Do not promote this candidate until source provenance, frozen markets,",
                "rules status, and expected labels have been reviewed.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "case_id": case_id,
                "output_dir": str(output_dir),
                "retrieval_id": retrieval.retrieval_id,
                "returned_count": len(retrieval.markets),
                "agent_run_id": run_summary["run_id"] if run_summary else None,
                "phoenix_trace_id": (
                    run_summary["phoenix_trace_id"] if run_summary else None
                ),
            },
            indent=2,
        )
    )
    return 0


def _case_id(thesis: str, now: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", thesis.lower()).strip("-")[:48]
    return f"{now.strftime('%Y%m%d')}-{slug or 'retrieval'}"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
