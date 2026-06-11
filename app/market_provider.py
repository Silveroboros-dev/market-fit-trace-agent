from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings, settings
from app.market_data import load_markets
from app.models import CandidateMarket, NormalizedClaim


class MarketProvider(Protocol):
    name: str

    def retrieve(self, claim: NormalizedClaim | None = None) -> MarketRetrievalResult:
        """Return market context with audit metadata."""

    def get_markets(self, claim: NormalizedClaim | None = None) -> list[CandidateMarket]:
        """Return the bounded market context used by market-fit policy."""


@dataclass
class MarketRetrievalResult:
    mode: str
    markets: list[CandidateMarket]
    snapshot_id: str | None = None
    as_of_ts: str | None = None
    retrieval_id: str | None = None
    query_summary: dict[str, Any] = field(default_factory=dict)
    raw_markets: list[dict[str, object]] = field(default_factory=list)
    excluded_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class StaticMarketProvider:
    markets: list[CandidateMarket]
    name: str = "fixture"

    def retrieve(self, claim: NormalizedClaim | None = None) -> MarketRetrievalResult:
        return MarketRetrievalResult(
            mode=self.name,
            markets=self.markets,
            query_summary={
                "source": "frozen_fixture",
                "claim_present": claim is not None,
                "returned_count": len(self.markets),
            },
        )

    def get_markets(self, claim: NormalizedClaim | None = None) -> list[CandidateMarket]:
        return self.retrieve(claim).markets


@dataclass
class PolyDataMarketProvider:
    settings_obj: Settings = settings
    name: str = "polydata"
    _universe: list[dict[str, object]] | None = field(default=None, init=False, repr=False)
    _loaded_at_monotonic: float | None = field(default=None, init=False, repr=False)

    def retrieve(self, claim: NormalizedClaim | None = None) -> MarketRetrievalResult:
        loaded_rows = self._load_universe()
        rows = [row for row in loaded_rows if _row_is_open_market_context(row)]
        excluded_closed_or_inactive = len(loaded_rows) - len(rows)
        top_k = max(1, min(self.settings_obj.poly_data_top_k, self.settings_obj.poly_data_max_k))
        ranked = _rank_rows(rows, claim)
        selected = [_with_rules_status(row) for row in ranked[:top_k]]
        as_of_ts = _max_timestamp(rows, "bar_ts")
        snapshot_id = (
            f"polydata_{self.settings_obj.poly_data_exchange}_{as_of_ts}"
            if as_of_ts
            else None
        )
        query_summary = {
            "claim_text": claim.claim_text if claim else "",
            "entities": claim.entities if claim else [],
            "horizon": claim.horizon if claim else "",
            "top_k": top_k,
            "min_volume_usd": self.settings_obj.poly_data_min_volume_usd,
            "min_taxonomy_confidence": self.settings_obj.poly_data_min_taxonomy_confidence,
            "l1_allowlist": list(self.settings_obj.poly_data_l1_allowlist),
            "liquidity_metric": _liquidity_metric(loaded_rows),
            "universe_count": len(rows),
            "returned_count": len(selected),
            "rules_status_summary": _rules_status_summary(selected),
        }
        retrieval_id = _retrieval_id(
            mode=self.name,
            as_of_ts=as_of_ts,
            query_summary=query_summary,
            market_ids=[_stringify(row.get("market_id") or row.get("id")) for row in selected],
        )
        return MarketRetrievalResult(
            mode=self.name,
            snapshot_id=snapshot_id,
            as_of_ts=as_of_ts,
            retrieval_id=retrieval_id,
            query_summary=query_summary,
            markets=[_row_to_candidate_market(row) for row in selected],
            raw_markets=selected,
            excluded_summary={
                "after_provider_filters": len(rows),
                "excluded_closed_or_inactive": excluded_closed_or_inactive,
                "not_returned_after_ranking": max(0, len(rows) - len(selected)),
                "rules_status_summary": _rules_status_summary(selected),
            },
        )

    def get_markets(self, claim: NormalizedClaim | None = None) -> list[CandidateMarket]:
        return self.retrieve(claim).markets

    def _load_universe(self) -> list[dict[str, object]]:
        if self._universe is not None and not self._cache_expired():
            return self._universe
        if not self.settings_obj.poly_data_sas_token:
            raise RuntimeError(
                "MARKET_PROVIDER=polydata requires POLY_DATA_SAS_TOKEN. "
                "Use MARKET_PROVIDER=fixture for frozen replay/evals."
            )
        self._universe = self._fetch_polydata_universe()
        self._loaded_at_monotonic = time.monotonic()
        return self._universe

    def _cache_expired(self) -> bool:
        if self._loaded_at_monotonic is None:
            return False
        ttl = self.settings_obj.poly_data_cache_ttl_seconds
        if ttl <= 0:
            return True
        return time.monotonic() - self._loaded_at_monotonic > ttl

    def _fetch_polydata_universe(self) -> list[dict[str, object]]:
        PolyData = _load_polydata_class()

        poly = PolyData(
            self.settings_obj.poly_data_sas_token,
            exchange=self.settings_obj.poly_data_exchange,
        )
        taxonomy = poly.taxonomy()
        markets = poly.markets()
        cross_section = poly.cross_section().df
        market_stats = poly.list_market_stats()

        joined = taxonomy.join(
            cross_section,
            left_on="market_id",
            right_on="id",
            how="inner",
        )

        market_columns = [
            column
            for column in (
                "id",
                "answer1",
                "answer2",
                "market_slug",
                "condition_id",
                "question_id",
                "description",
                "resolution_source",
                "ticker",
                "created_at",
            )
            if column in markets.columns
        ]
        if market_columns:
            joined = joined.join(
                markets.select(market_columns),
                left_on="market_id",
                right_on="id",
                how="left",
            )

        stats_columns = [
            column
            for column in (
                "market_id",
                "trading_days_count",
                "first_trade_date",
                "last_trade_date",
                "total_trades",
                "total_volume_usd",
            )
            if column in market_stats.columns
        ]
        if {"market_id", "total_volume_usd"}.issubset(stats_columns):
            joined = joined.join(
                market_stats.select(stats_columns),
                on="market_id",
                how="left",
            )

        liquidity_field = (
            "total_volume_usd" if "total_volume_usd" in joined.columns else "volume_usd"
        )
        filters = (
            (~joined["is_low_confidence"])
            & (~joined["is_unmapped"])
            & (joined["confidence"] >= self.settings_obj.poly_data_min_taxonomy_confidence)
            & (joined[liquidity_field].fill_null(0.0) >= self.settings_obj.poly_data_min_volume_usd)
        )
        if self.settings_obj.poly_data_l1_allowlist:
            filters = filters & joined["l1"].is_in(list(self.settings_obj.poly_data_l1_allowlist))
        filtered = joined.filter(filters)
        return filtered.to_dicts()


def _load_polydata_class() -> Any:
    try:
        from poly_data_client import PolyData

        return PolyData
    except ImportError as exc:
        added_path = _add_optional_polydata_import_path()
        if added_path:
            try:
                from poly_data_client import PolyData

                return PolyData
            except ImportError:
                pass
        raise RuntimeError(
            "MARKET_PROVIDER=polydata requires the poly_data_client package. "
            "Install it into this environment, or set POLY_DATA_EXPLORER_PATH to a "
            "local poly-data-explorer checkout with an initialized .venv. "
            "For a direct site-packages bridge, set POLY_DATA_CLIENT_PATH."
        ) from exc


def _add_optional_polydata_import_path() -> str | None:
    candidates: list[Path] = []
    explicit_client_path = os.getenv("POLY_DATA_CLIENT_PATH")
    if explicit_client_path:
        candidates.append(Path(explicit_client_path).expanduser())

    explorer_paths = [
        os.getenv("POLY_DATA_EXPLORER_PATH"),
        str(Path(__file__).resolve().parents[2] / "poly-data-explorer"),
    ]
    for raw_path in explorer_paths:
        if not raw_path:
            continue
        explorer_path = Path(raw_path).expanduser()
        candidates.extend(explorer_path.glob(".venv/lib/python*/site-packages"))

    for candidate in candidates:
        import_path = candidate.parent if candidate.name == "poly_data_client" else candidate
        if not (import_path / "poly_data_client").exists():
            continue
        import_path_text = str(import_path)
        if import_path_text not in sys.path:
            sys.path.insert(0, import_path_text)
        return import_path_text
    return None


def build_market_provider(
    *,
    markets: list[CandidateMarket] | None = None,
    settings_obj: Settings = settings,
) -> MarketProvider:
    if markets is not None:
        return StaticMarketProvider(markets=markets)
    if settings_obj.market_provider == "polydata":
        return PolyDataMarketProvider(settings_obj=settings_obj)
    return StaticMarketProvider(markets=load_markets())


def _rank_rows(
    rows: list[dict[str, object]],
    claim: NormalizedClaim | None,
) -> list[dict[str, object]]:
    if not claim:
        return sorted(rows, key=_volume_usd, reverse=True)

    query_text = " ".join(
        [
            claim.claim_text,
            claim.horizon,
            claim.stance,
            " ".join(claim.entities),
        ]
    )
    query_tokens = _tokens(query_text)
    scored: list[tuple[float, int, dict[str, object]]] = []
    for row in rows:
        haystack = _row_haystack(row)
        entity_match_count = _entity_match_count(claim.entities, haystack)
        score = _retrieval_score(
            row,
            query_tokens,
            claim.entities,
            haystack=haystack,
            entity_match_count=entity_match_count,
        )
        scored.append((score, entity_match_count, row))

    positive = [(score, entity_count, row) for score, entity_count, row in scored if score > 0.0]
    entity_matched = [
        (score, entity_count, row)
        for score, entity_count, row in positive
        if entity_count > 0
    ]
    context_matched = [
        item for item in entity_matched if _row_matches_claim_context(item[2], claim)
    ]
    ranked = context_matched or entity_matched or positive
    return [
        row
        for _, _, row in sorted(
            ranked,
            key=lambda item: (
                item[0],
                item[1],
                _volume_usd(item[2]),
                _n_trades(item[2]),
            ),
            reverse=True,
        )
    ]


def _retrieval_score(
    row: dict[str, object],
    query_tokens: set[str],
    entities: list[str],
    *,
    haystack: str | None = None,
    entity_match_count: int | None = None,
) -> float:
    haystack = haystack if haystack is not None else _row_haystack(row)
    haystack_tokens = _tokens(haystack)
    query_semantic_tokens = _semantic_tokens(query_tokens)
    semantic_overlap = _semantic_tokens(query_tokens & haystack_tokens)
    if not query_semantic_tokens:
        overlap_score = 0.0
    else:
        overlap_score = len(semantic_overlap) / len(query_semantic_tokens)

    entity_match_count = (
        entity_match_count
        if entity_match_count is not None
        else _entity_match_count(entities, haystack)
    )
    if entity_match_count == 0 and len(semantic_overlap) < 2:
        return 0.0
    entity_boost = entity_match_count * 0.08
    return overlap_score + entity_boost


def _row_haystack(row: dict[str, object]) -> str:
    return " ".join(
        _stringify(row.get(field_name))
        for field_name in (
            "question",
            "description",
            "resolution_source",
            "category",
            "tags",
            "l1",
            "l2_id",
            "l2_name",
            "agent_rationale",
        )
    )


def _entity_match_count(entities: list[str], haystack: str) -> int:
    return sum(
        1
        for entity in entities
        if _is_retrieval_entity_anchor(entity) and _entity_matches(entity, haystack)
    )


def _is_retrieval_entity_anchor(entity: str) -> bool:
    normalized = _normalize_entity_text(entity)
    if not normalized:
        return False
    if normalized in _NON_ENTITY_ANCHORS:
        return False
    if normalized in _STOPWORDS:
        return False
    if len(normalized) <= 2 and normalized not in _SHORT_ENTITY_ANCHORS:
        return False
    return True


def _row_matches_claim_context(row: dict[str, object], claim: NormalizedClaim) -> bool:
    claim_text = " ".join([claim.claim_text, claim.horizon, claim.stance]).lower()
    row_text = _row_haystack(row).lower()
    if _has_ipo_context(claim_text):
        return _has_ipo_context(row_text)
    return True


def _has_ipo_context(text: str) -> bool:
    return any(
        token in text
        for token in (
            "ipo",
            "initial public offering",
            "public offering",
            "direct listing",
            "market cap",
            "market capitalization",
            "s-1",
            "confidential filing",
            "file confidentially",
            "files confidentially",
        )
    )


def _row_to_candidate_market(row: dict[str, object]) -> CandidateMarket:
    tags = _dedupe(
        [
            *_to_string_list(row.get("tags")),
            _stringify(row.get("category")),
            _stringify(row.get("l1")),
            _stringify(row.get("l2_name")),
        ]
    )
    resolution_rules = _clean_text(row.get("description"))
    rules_status = _rules_status(row)
    risks = ["dynamic_polydata_retrieval"]
    if rules_status != "present":
        risks.append("missing_resolution_rules")
    if bool(row.get("is_low_confidence")):
        risks.append("taxonomy_low_confidence")
    if _field_is_false(row, "enable_order_book") or _field_is_false(row, "enableOrderBook"):
        risks.append("not_orderbook_enabled")
    if _field_is_true(row, "closed") or _field_is_false(row, "active"):
        risks.append("inactive_or_closed_market")
    source_url = _source_url(row)
    description_parts = [
        _stringify(row.get("question")),
        f"event_id: {_stringify(row.get('event_id'))}" if row.get("event_id") else "",
        f"event_slug: {_stringify(row.get('event_slug'))}" if row.get("event_slug") else "",
        f"market_slug: {_stringify(row.get('market_slug'))}" if row.get("market_slug") else "",
        f"condition_id: {_stringify(row.get('condition_id'))}" if row.get("condition_id") else "",
        f"question_id: {_stringify(row.get('question_id'))}" if row.get("question_id") else "",
        f"rules_status: {rules_status}",
        (
            f"resolution_source: {_stringify(row.get('resolution_source'))}"
            if row.get("resolution_source")
            else ""
        ),
        f"L1: {_stringify(row.get('l1'))}" if row.get("l1") else "",
        f"L2: {_stringify(row.get('l2_name'))}" if row.get("l2_name") else "",
        f"total_volume_usd: {_volume_usd(row):.2f}",
        f"current_bar_volume_usd: {_current_bar_volume_usd(row):.2f}",
        f"price: {_probability(row)}" if _probability(row) is not None else "",
        "probability_source: cross_section.price" if _probability(row) is not None else "",
        f"source: {source_url}" if source_url else "",
    ]
    return CandidateMarket(
        market_id=_stringify(row.get("market_id") or row.get("id")),
        title=_stringify(row.get("question")),
        venue="Polymarket",
        description=" | ".join(part for part in description_parts if part),
        resolution_rules=resolution_rules,
        close_date=_stringify(row.get("end_date") or row.get("closed_time")),
        outcomes=_outcomes(row),
        current_probability=_probability(row),
        known_fit_risks=risks,
        entity_tags=tags,
    )


def _with_rules_status(row: dict[str, object]) -> dict[str, object]:
    annotated = dict(row)
    annotated["rules_status"] = _rules_status(row)
    annotated.pop("model", None)
    return annotated


def _rules_status(row: dict[str, object]) -> str:
    return "present" if _clean_text(row.get("description")) else "missing"


def _rules_status_summary(rows: list[dict[str, object]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for row in rows:
        status = _rules_status(row)
        summary[status] = summary.get(status, 0) + 1
    return summary


def _source_url(row: dict[str, object]) -> str | None:
    slug = _stringify(row.get("event_slug") or row.get("market_slug")).strip()
    if not slug:
        return None
    return f"https://polymarket.com/event/{slug}"


def _outcomes(row: dict[str, object]) -> list[str]:
    outcomes = [_stringify(row.get("answer1")), _stringify(row.get("answer2"))]
    outcomes = [outcome for outcome in outcomes if outcome]
    return outcomes or ["Yes", "No"]


def _probability(row: dict[str, object]) -> float | None:
    raw = row.get("price")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0.0 or value > 1.0:
        return None
    return value


def _row_is_open_market_context(row: dict[str, object]) -> bool:
    if _field_is_true(row, "closed") or _field_is_true(row, "archived"):
        return False
    if _field_is_false(row, "active"):
        return False
    raw_days_to_close = row.get("days_to_close")
    if raw_days_to_close is None:
        return True
    try:
        return float(raw_days_to_close) >= 0.0
    except (TypeError, ValueError):
        return True


def _volume_usd(row: dict[str, object]) -> float:
    raw = row.get("total_volume_usd") or row.get("volume_usd") or row.get("volume") or 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _current_bar_volume_usd(row: dict[str, object]) -> float:
    raw = row.get("volume_usd") or 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _liquidity_metric(rows: list[dict[str, object]]) -> str:
    if any("total_volume_usd" in row for row in rows):
        return "total_volume_usd"
    return "volume_usd"


def _n_trades(row: dict[str, object]) -> int:
    raw = row.get("n_trades") or 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _max_timestamp(rows: list[dict[str, object]], field_name: str) -> str | None:
    values = sorted(_stringify(row.get(field_name)) for row in rows if row.get(field_name))
    return values[-1] if values else None


def _retrieval_id(
    *,
    mode: str,
    as_of_ts: str | None,
    query_summary: dict[str, Any],
    market_ids: list[str],
) -> str:
    payload = repr((mode, as_of_ts, sorted(query_summary.items()), market_ids)).encode()
    return f"retr_{sha256(payload).hexdigest()[:16]}"


def _field_is_true(row: dict[str, object], field_name: str) -> bool:
    if field_name not in row:
        return False
    value = row.get(field_name)
    if isinstance(value, bool):
        return value
    return _stringify(value).lower() in {"true", "1", "yes"}


def _field_is_false(row: dict[str, object], field_name: str) -> bool:
    if field_name not in row:
        return False
    value = row.get(field_name)
    if isinstance(value, bool):
        return not value
    return _stringify(value).lower() in {"false", "0", "no"}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _semantic_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if not token.isdigit()}


def _entity_matches(entity: str, haystack: str) -> bool:
    cleaned_entity = _normalize_entity_text(entity)
    if not cleaned_entity:
        return False
    normalized_haystack = _normalize_entity_text(haystack)
    return re.search(
        rf"(?<![a-z0-9]){re.escape(cleaned_entity)}(?![a-z0-9])",
        normalized_haystack,
    ) is not None


def _normalize_entity_text(value: str) -> str:
    normalized = value.lower().replace("u.s.", "us")
    return re.sub(r"\s+", " ", normalized).strip()


def _to_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [_stringify(item) for item in value if _stringify(item)]
    text = _stringify(value)
    return [text] if text else []


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list | tuple | set):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _clean_text(value: object) -> str:
    text = _stringify(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        result.append(cleaned)
    return result


_STOPWORDS = {
    "and",
    "are",
    "end",
    "for",
    "from",
    "has",
    "have",
    "into",
    "not",
    "the",
    "this",
    "that",
    "their",
    "will",
    "with",
    "unspecified",
}

_SHORT_ENTITY_ANCHORS = {"ai", "eu", "uk", "us"}

_NON_ENTITY_ANCHORS = {
    "if",
    "january",
    "jan",
    "february",
    "feb",
    "march",
    "mar",
    "april",
    "apr",
    "may",
    "june",
    "jun",
    "july",
    "jul",
    "august",
    "aug",
    "september",
    "sep",
    "sept",
    "october",
    "oct",
    "november",
    "nov",
    "december",
    "dec",
}
