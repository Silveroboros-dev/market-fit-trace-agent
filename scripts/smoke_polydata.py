from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.market_provider import PolyDataMarketProvider
from app.models import NormalizedClaim


DEFAULT_THESIS = (
    "US and Iran will extend a ceasefire and reopen the Strait of Hormuz by the end of June."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test the optional PolyData bounded market provider."
    )
    parser.add_argument("--thesis", default=DEFAULT_THESIS)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-volume-usd", type=float, default=5000.0)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument(
        "--l1",
        default="",
        help="Optional comma-separated L1 allowlist, e.g. politics,macro,crypto.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("POLY_DATA_SAS_TOKEN")
    if not token:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "POLY_DATA_SAS_TOKEN is required in the environment.",
                },
                indent=2,
            )
        )
        return 2

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
    rules_status_summary = {
        "present": sum(1 for market in retrieval.markets if market.resolution_rules.strip()),
        "missing": sum(1 for market in retrieval.markets if not market.resolution_rules.strip()),
    }
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": retrieval.mode,
                "snapshot_id": retrieval.snapshot_id,
                "as_of_ts": retrieval.as_of_ts,
                "retrieval_id": retrieval.retrieval_id,
                "query_summary": retrieval.query_summary,
                "excluded_summary": retrieval.excluded_summary,
                "rules_status_summary": rules_status_summary,
                "markets": [
                    {
                        "market_id": market.market_id,
                        "title": market.title,
                        "current_probability": market.current_probability,
                        "close_date": market.close_date,
                        "known_fit_risks": market.known_fit_risks,
                        "entity_tags": market.entity_tags,
                    }
                    for market in retrieval.markets
                ],
            },
            indent=2,
            default=str,
        )
    )
    return 0 if retrieval.markets else 1


if __name__ == "__main__":
    raise SystemExit(main())
