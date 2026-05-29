from app.config import Settings
from app.market_data import load_markets
from app.market_provider import PolyDataMarketProvider, StaticMarketProvider, build_market_provider
from app.models import NormalizedClaim


def test_static_market_provider_returns_fixture_markets():
    markets = load_markets()
    provider = StaticMarketProvider(markets=markets)

    assert provider.name == "fixture"
    assert provider.get_markets() == markets
    retrieval = provider.retrieve()
    assert retrieval.mode == "fixture"
    assert retrieval.query_summary["source"] == "frozen_fixture"


def test_polydata_provider_ranks_cached_universe_without_live_client():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_top_k=2,
            poly_data_max_k=50,
        )
    )
    provider._universe = [
        {
            "market_id": "iran-hormuz",
            "question": "Strait of Hormuz traffic returns to normal by end of June?",
            "answer1": "Yes",
            "answer2": "No",
            "l1": "politics",
            "l2_name": "Maritime chokepoint closure",
            "tags": ["Iran", "shipping"],
            "category": "Politics",
            "agent_rationale": "Hormuz reopening and Iran conflict",
            "volume_usd": 25000,
            "n_trades": 22,
            "price": 0.51,
            "end_date": "2026-06-30",
            "market_slug": "strait-of-hormuz-traffic-returns-to-normal-by-end-of-june",
            "enable_order_book": False,
        },
        {
            "market_id": "fed-cuts",
            "question": "Will the Fed cut interest rates in 2026?",
            "answer1": "Yes",
            "answer2": "No",
            "l1": "macro",
            "l2_name": "Federal Reserve rates",
            "tags": ["Federal Reserve", "rates"],
            "category": "Economics",
            "agent_rationale": "Fed policy",
            "volume_usd": 500000,
            "n_trades": 200,
            "price": 0.29,
            "end_date": "2026-12-31",
            "market_slug": "will-the-fed-cut-interest-rates-in-2026",
        },
    ]
    claim = NormalizedClaim(
        claim_text="US and Iran will reopen the Strait of Hormuz after a ceasefire deal.",
        entities=["Iran", "Strait of Hormuz"],
        horizon="by end of June 2026",
        stance="will happen",
    )

    retrieval = provider.retrieve(claim)
    markets = retrieval.markets

    assert [market.market_id for market in markets] == ["iran-hormuz"]
    assert retrieval.mode == "polydata"
    assert retrieval.retrieval_id
    assert retrieval.query_summary["liquidity_metric"] == "volume_usd"
    assert retrieval.query_summary["returned_count"] == 1
    assert retrieval.query_summary["rules_status_summary"] == {"missing": 1}
    assert retrieval.raw_markets[0]["rules_status"] == "missing"
    assert retrieval.excluded_summary["rules_status_summary"] == {"missing": 1}
    assert markets[0].venue == "Polymarket"
    assert markets[0].current_probability == 0.51
    assert "missing_resolution_rules" in markets[0].known_fit_risks
    assert "dynamic_polydata_retrieval" in markets[0].known_fit_risks
    assert "not_orderbook_enabled" in markets[0].known_fit_risks
    assert "Maritime chokepoint closure" in markets[0].entity_tags


def test_polydata_provider_does_not_fill_claim_results_with_unrelated_volume():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_top_k=5,
            poly_data_max_k=50,
        )
    )
    provider._universe = [
        {
            "market_id": "hormuz",
            "question": "Will the Strait of Hormuz reopen by June 30?",
            "volume_usd": 12000,
        },
        {
            "market_id": "sports-high-volume",
            "question": "Will Crystal Palace win today?",
            "description": "This market resolves at the end of the match in June.",
            "volume_usd": 1_000_000,
        },
    ]
    claim = NormalizedClaim(
        claim_text="US and Iran will reopen the Strait of Hormuz after a ceasefire deal.",
        entities=["Iran", "Strait of Hormuz"],
        horizon="by end of June 2026",
        stance="will happen",
    )

    retrieval = provider.retrieve(claim)

    assert [market.market_id for market in retrieval.markets] == ["hormuz"]
    assert retrieval.query_summary["returned_count"] == 1


def test_polydata_provider_does_not_match_short_entities_as_substrings():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_top_k=5,
            poly_data_max_k=50,
        )
    )
    provider._universe = [
        {
            "market_id": "related-us-market",
            "question": "Will the US announce a new Iran agreement?",
            "tags": ["U.S. x Iran"],
            "volume_usd": 12000,
        },
        {
            "market_id": "substring-noise",
            "question": "Will Ivan Cepeda Castro win the election?",
            "agent_rationale": "Candidates must win a national vote.",
            "volume_usd": 1_000_000,
        },
    ]
    claim = NormalizedClaim(
        claim_text="US and Iran will announce an agreement.",
        entities=["US", "Iran"],
        horizon="2026",
        stance="will happen",
    )

    retrieval = provider.retrieve(claim)

    assert [market.market_id for market in retrieval.markets] == ["related-us-market"]


def test_polydata_provider_maps_description_to_resolution_rules():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_top_k=1,
            poly_data_max_k=50,
        )
    )
    provider._universe = [
        {
            "market_id": "hormuz-blockade-lifted",
            "question": "Will the United States blockade of the Strait of Hormuz be lifted?",
            "description": (
                "This market resolves Yes if official US government sources announce "
                "that the blockade has been lifted by the close date."
            ),
            "resolution_source": "Official US government announcement",
            "question_id": "0xquestion",
            "condition_id": "0xcondition",
            "l1": "politics",
            "l2_name": "Maritime chokepoint",
            "volume_usd": 25000,
            "price": 0.83,
            "end_date": "2026-06-30",
        }
    ]

    retrieval = provider.retrieve()
    market = retrieval.markets[0]

    assert market.resolution_rules.startswith("This market resolves Yes")
    assert "missing_resolution_rules" not in market.known_fit_risks
    assert "dynamic_polydata_retrieval" in market.known_fit_risks
    assert "rules_status: present" in market.description
    assert "resolution_source: Official US government announcement" in market.description
    assert "question_id: 0xquestion" in market.description
    assert retrieval.raw_markets[0]["rules_status"] == "present"
    assert retrieval.query_summary["rules_status_summary"] == {"present": 1}
    assert retrieval.excluded_summary["rules_status_summary"] == {"present": 1}


def test_polydata_provider_excludes_explicitly_closed_or_inactive_rows():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_top_k=10,
            poly_data_max_k=50,
        )
    )
    provider._universe = [
        {
            "market_id": "open-market",
            "question": "Open market?",
            "volume_usd": 25000,
            "days_to_close": 5,
        },
        {
            "market_id": "closed-market",
            "question": "Closed market?",
            "volume_usd": 25000,
            "closed": True,
        },
        {
            "market_id": "inactive-market",
            "question": "Inactive market?",
            "volume_usd": 25000,
            "active": False,
        },
        {
            "market_id": "expired-market",
            "question": "Expired market?",
            "volume_usd": 25000,
            "days_to_close": -1,
        },
    ]

    retrieval = provider.retrieve()

    assert [market.market_id for market in retrieval.markets] == ["open-market"]
    assert retrieval.excluded_summary["excluded_closed_or_inactive"] == 3


def test_explicit_markets_override_polydata_for_strict_evals():
    markets = load_markets()
    provider = build_market_provider(
        markets=markets,
        settings_obj=Settings(market_provider="polydata", poly_data_sas_token="unused"),
    )

    assert provider.name == "fixture"
    assert provider.get_markets() == markets


def test_explicit_markets_override_invalid_polydata_environment_for_strict_evals():
    markets = load_markets()
    provider = build_market_provider(
        markets=markets,
        settings_obj=Settings(market_provider="polydata", poly_data_sas_token="invalid"),
    )

    assert provider.name == "fixture"
    assert provider.retrieve().mode == "fixture"


def test_polydata_provider_refreshes_expired_cache():
    provider = PolyDataMarketProvider(
        settings_obj=Settings(
            market_provider="polydata",
            poly_data_sas_token="unused",
            poly_data_cache_ttl_seconds=1,
        )
    )
    calls = []

    def fetch_rows():
        calls.append(len(calls) + 1)
        return [{"market_id": f"market-{calls[-1]}", "question": "Question", "volume_usd": 1}]

    provider._fetch_polydata_universe = fetch_rows

    assert provider._load_universe()[0]["market_id"] == "market-1"
    assert provider._load_universe()[0]["market_id"] == "market-1"
    assert calls == [1]

    provider._loaded_at_monotonic = 0

    assert provider._load_universe()[0]["market_id"] == "market-2"
    assert calls == [1, 2]
