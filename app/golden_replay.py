from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.market_provider import MarketRetrievalResult
from app.models import CandidateMarket, NormalizedClaim

ROOT = Path(__file__).resolve().parents[1]
STRICT_GOLDEN_PACKS = (
    ROOT / "evals" / "market_fit_v1",
    ROOT / "evals" / "market_fit_v2",
    ROOT / "evals" / "market_fit_v4_live_promoted",
)


@dataclass(frozen=True)
class GoldenReplayCase:
    pack: str
    example_id: str
    source_text: str
    expected_fit_class: str
    expected_best_market_id: str | None
    markets: tuple[CandidateMarket, ...]
    expected_market_ids: tuple[str, ...]


@dataclass
class GoldenReplayMarketProvider:
    case: GoldenReplayCase
    name: str = "golden_fixture"

    def retrieve(self, claim: NormalizedClaim | None = None) -> MarketRetrievalResult:
        markets = list(self.case.markets)
        return MarketRetrievalResult(
            mode=self.name,
            markets=markets,
            snapshot_id=f"{self.case.pack}:{self.case.example_id}",
            query_summary={
                "source": "strict_golden_fixture",
                "golden_pack": self.case.pack,
                "example_id": self.case.example_id,
                "claim_present": claim is not None,
                "returned_count": len(markets),
                "expected_market_ids": list(self.case.expected_market_ids),
            },
        )

    def get_markets(self, claim: NormalizedClaim | None = None) -> list[CandidateMarket]:
        return self.retrieve(claim).markets


def resolve_strict_golden_provider(source_text: str) -> GoldenReplayMarketProvider | None:
    case = strict_golden_case_for_source(source_text)
    if case is None:
        return None
    return GoldenReplayMarketProvider(case)


def strict_golden_case_for_source(source_text: str) -> GoldenReplayCase | None:
    return _strict_golden_index().get(_normalize_source(source_text))


def list_strict_golden_options() -> list[dict[str, Any]]:
    pack_rank = {pack_dir.name: rank for rank, pack_dir in enumerate(STRICT_GOLDEN_PACKS)}
    cases = sorted(
        _strict_golden_index().values(),
        key=lambda case: (pack_rank.get(case.pack, 99), case.example_id),
    )
    return [
        {
            "pack": case.pack,
            "example_id": case.example_id,
            "label": _golden_label(case),
            "source_text": case.source_text,
            "expected_fit_class": case.expected_fit_class,
            "expected_best_market_id": case.expected_best_market_id,
            "fixture_market_count": len(case.markets),
            "fixture_market_ids": list(case.expected_market_ids),
        }
        for case in cases
    ]


@lru_cache(maxsize=1)
def _strict_golden_index() -> dict[str, GoldenReplayCase]:
    index: dict[str, GoldenReplayCase] = {}
    for pack_dir in STRICT_GOLDEN_PACKS:
        examples_path = pack_dir / "examples.jsonl"
        expected_path = pack_dir / "expected_outputs.jsonl"
        markets_path = pack_dir / "market_snapshots.jsonl"
        if not (examples_path.exists() and expected_path.exists() and markets_path.exists()):
            continue

        examples = _read_jsonl(examples_path)
        expected_by_id = {row["example_id"]: row for row in _read_jsonl(expected_path)}
        markets_by_id = {
            market.market_id: market
            for market in (_market_from_snapshot(row) for row in _read_jsonl(markets_path))
        }
        for example in examples:
            example_id = example["example_id"]
            expected = expected_by_id[example_id]
            expected_ids = _expected_market_ids(expected)
            selected_markets = tuple(
                market
                for market_id in expected_ids
                if (market := markets_by_id.get(market_id)) is not None
            )
            index[_normalize_source(example["source_text"])] = GoldenReplayCase(
                pack=pack_dir.name,
                example_id=example_id,
                source_text=example["source_text"],
                expected_fit_class=str(expected["expected_fit"]["semantic_fit_class"]),
                expected_best_market_id=expected["expected_fit"].get("best_market_id"),
                markets=selected_markets,
                expected_market_ids=tuple(expected_ids),
            )
    return index


def _golden_label(case: GoldenReplayCase) -> str:
    market_suffix = (
        f" -> {case.expected_best_market_id}" if case.expected_best_market_id else ""
    )
    return (
        f"{case.pack} / {case.example_id} / "
        f"{case.expected_fit_class}{market_suffix}"
    )


def _expected_market_ids(expected: dict[str, Any]) -> list[str]:
    fit = expected["expected_fit"]
    ids: list[str] = []
    best_market_id = fit.get("best_market_id")
    if best_market_id:
        ids.append(str(best_market_id))
    for key in ("acceptable_market_ids", "adjacent_market_ids", "rejected_market_ids"):
        ids.extend(str(market_id) for market_id in fit.get(key, []) if market_id)
    return sorted(set(ids))


def _market_from_snapshot(row: dict[str, Any]) -> CandidateMarket:
    close_time = row.get("close_time") or row.get("close_date") or ""
    close_date = str(close_time).split("T")[0] if close_time else "unspecified"
    return CandidateMarket(
        market_id=str(row["market_id"]),
        title=str(row["title"]),
        venue=str(row["venue"]),
        description=str(row.get("description") or ""),
        resolution_rules=str(row.get("resolution_rules") or ""),
        close_date=close_date,
        outcomes=[str(item) for item in row.get("outcomes", ["Yes", "No"])],
        current_probability=row.get("yes_price", row.get("current_probability")),
        known_fit_risks=[str(item) for item in row.get("known_fit_risks", [])],
        entity_tags=[str(item) for item in row.get("tags", row.get("entity_tags", []))],
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _normalize_source(text: str) -> str:
    return " ".join(text.split())
