# PolyData Provider Contract

This is the contract Market Fit Trace Agent needs from the
`poly-data-explorer` / PolyData provider to retrieve a bounded set of relevant
current Polymarket markets.

The goal is simple:

> Given a normalized thesis, return a small, current, provenance-rich set of
> relevant Polymarket markets without scanning the entire market universe for
> every user request.

The provider does not decide whether a market is `direct`, `indirect`,
`weak_proxy`, or `no_clean_expression`. It returns real market context. Market
fit remains the responsibility of Market Fit Trace Agent.

## Product Need

The agent needs current markets, not only hand-frozen fixtures.

For a user request, the app should:

1. normalize the thesis with ADK/Gemini;
2. ask PolyData for a bounded set of relevant open Polymarket markets;
3. classify fit conservatively using title, rules, horizon, entity, and metric;
4. record Phoenix traces/evals and optional user verdicts.

Strict evals still replay frozen fixtures. Live retrieval is for production/demo
mode and for acquiring new eval examples.

## MVP Retrieval Rule

Start with one simple universe filter:

- venue: `polymarket`;
- status: `open`;
- liquidity/open-interest/volume proxy: `>= 10000` USD;
- snapshot recency: latest available snapshot, ideally daily or every 4 hours;
- max returned markets: default `20`, hard max `50`.

The exact liquidity metric can be provider-defined, but it must be named in the
response as `liquidity_metric`.

## Observed PolyData Surface As Of 2026-05-24

The current `poly-data-explorer` client already supports the bounded discovery
part of this contract through:

- `poly.taxonomy()`
- `poly.markets()`

Observed `poly.taxonomy()` shape:

- rows: `133305`
- `market_id`
- `as_of_date`
- `l1`
- `l2_id`
- `l2_name`
- `confidence`
- `is_low_confidence`
- `is_unmapped`
- `taxonomy_version`
- `model`
- `classified_at`
- `agent_rationale`
- `classified_by`

Observed `poly.markets()` shape:

- rows: `1160823`
- `id`
- `question`
- `answer1`
- `answer2`
- `token1`
- `token2`
- `condition_id`
- `market_slug`
- `neg_risk`
- `volume`
- `ticker`
- `tags`
- `created_at`
- `closed_time`
- `end_date`

The current join key is:

```text
taxonomy.market_id == markets.id
```

This is enough for an MVP bounded market provider:

1. choose product-controlled L1 buckets from the normalized thesis;
2. fetch live L2 buckets from taxonomy;
3. join taxonomy to markets;
4. filter `closed_time IS NULL`;
5. filter `is_low_confidence = false` and `is_unmapped = false`;
6. filter `confidence >= 0.85`;
7. cast `volume` to USD float and filter `volume >= 10000`;
8. rank within L1/L2 by a simple retrieval score plus volume;
9. return top `20`, hard max `50`.

The current client does **not** expose full market-resolution rules,
descriptions, current prices, `open_interest`, or a separate `liquidity` field
through `poly.markets()`. Therefore the first integration should treat PolyData
as a bounded discovery provider, not yet a complete rules provider.

For now:

- use `volume` as `liquidity_metric = "volume_usd"`;
- map `answer1` / `answer2` to outcomes;
- map `question` to `title`;
- derive `source_url` from `market_slug`;
- set `resolution_rules = ""` and `rules_status = "missing"` unless another
  provider method is added;
- treat missing rules as a conservative fit-risk signal.

This preserves the product boundary:

> PolyData retrieves a bounded real-market set. Market Fit Trace Agent decides
> whether any returned market is direct, indirect, weak proxy, or no clean
> expression.

## Required Provider Surface

The provider may expose these as Python client methods or HTTP endpoints. The
contract below uses endpoint language for clarity.

### 1. Snapshot Manifest

Returns the latest available market snapshot and metadata needed for audit.

```http
GET /polymarket/snapshots/latest
```

Response:

```json
{
  "snapshot_id": "polymarket_2026_05_24_1200",
  "as_of_ts": "2026-05-24T12:00:00Z",
  "exchange": "polymarket",
  "cadence": "4h",
  "market_count": 18342,
  "open_market_count": 4120,
  "default_min_liquidity_usd": 10000,
  "taxonomy_version": "taxonomy_v1",
  "embedding_index_version": "embeddings_2026_05_24",
  "source": "poly-data-explorer"
}
```

### 2. L2 Buckets For A Fixed L1

L1 taxonomy can be controlled by the product. L2 should be fetched dynamically
from the current snapshot so the app can narrow search efficiently.

```http
GET /polymarket/snapshots/{snapshot_id}/taxonomy/l2?l1=macro
```

Response:

```json
{
  "snapshot_id": "polymarket_2026_05_24_1200",
  "l1": "macro",
  "taxonomy_version": "taxonomy_v1",
  "buckets": [
    {
      "l2_id": "fed-rates",
      "l2_name": "Federal Reserve rates",
      "market_count": 42,
      "open_market_count": 18,
      "example_market_titles": [
        "How many Fed rate cuts in 2026?",
        "Fed rate cut by September?"
      ]
    }
  ]
}
```

If taxonomy is not ready, this endpoint can return provider categories as a
temporary fallback, with:

```json
{ "taxonomy_status": "fallback_provider_category" }
```

### 3. Bounded Market Search

Main retrieval call. It returns a ranked set of current candidate markets for
the agent to inspect.

```http
POST /polymarket/markets/search
```

Request:

```json
{
  "snapshot_id": "polymarket_2026_05_24_1200",
  "query_text": "The Federal Reserve is not expected to cut rates until at least 2028.",
  "entities": ["Federal Reserve", "Fed funds rate", "inflation"],
  "horizon": "through 2027 / until 2028",
  "l1_allowlist": ["macro"],
  "l2_allowlist": ["fed-rates"],
  "status": "open",
  "min_liquidity_usd": 10000,
  "top_k": 20,
  "include_rules": true
}
```

Response:

```json
{
  "snapshot_id": "polymarket_2026_05_24_1200",
  "as_of_ts": "2026-05-24T12:00:00Z",
  "retrieval_id": "retr_01J...",
  "query_summary": {
    "query_text": "The Federal Reserve is not expected to cut rates until at least 2028.",
    "entities": ["Federal Reserve", "Fed funds rate", "inflation"],
    "l1_used": ["macro"],
    "l2_used": ["fed-rates"],
    "min_liquidity_usd": 10000,
    "top_k": 20
  },
  "markets": [
    {
      "rank": 1,
      "market_id": "polymarket_fed_rate_cuts_2026_count",
      "venue": "polymarket",
      "title": "How many Fed rate cuts in 2026?",
      "description": "Multi-outcome market on the number of Federal Reserve rate cuts in 2026.",
      "resolution_rules": "Counts 25 bps-equivalent reductions in the Federal Reserve target federal funds rate during calendar year 2026, based on official FOMC/Federal Reserve decisions.",
      "resolution_source": "Federal Reserve / FOMC",
      "outcomes": ["0 cuts", "1 cut", "2 cuts", "3+ cuts"],
      "yes_price": null,
      "current_probability": null,
      "close_time": "2026-12-31T23:59:59-05:00",
      "status": "open",
      "liquidity_metric": "volume_usd",
      "liquidity_usd": 82345.12,
      "volume_usd": 82345.12,
      "open_interest_usd": null,
      "source_url": "https://polymarket.com/event/how-many-fed-rate-cuts-in-2026",
      "l1": "macro",
      "l2_id": "fed-rates",
      "l2_name": "Federal Reserve rates",
      "tags": ["Federal Reserve", "FOMC", "interest rates"],
      "retrieval_score": 0.84,
      "retrieval_reasons": [
        "entity_match: Federal Reserve",
        "topic_match: rates",
        "horizon_partial_match: 2026 market vs through-2027 thesis"
      ],
      "retrieval_risk_flags": ["wrong_horizon"]
    }
  ],
  "excluded_summary": {
    "below_liquidity_threshold": 231,
    "closed_or_resolved": 18,
    "outside_l1_or_l2": 1190
  }
}
```

## Required Market Fields

Each returned market must provide enough information to map into the app's
current `CandidateMarket` shape and support future eval freezing.

Required:

- `market_id`;
- `venue`;
- `title`;
- `description`;
- `resolution_rules`;
- `close_time`;
- `status`;
- `outcomes`;
- `source_url`;
- `as_of_ts` through the enclosing snapshot;
- one named liquidity field: `liquidity_usd`, `volume_usd`, or
  `open_interest_usd`;
- `retrieval_score`;
- `retrieval_reasons`.

Strongly preferred:

- `resolution_source`;
- `l1`;
- `l2_id`;
- `l2_name`;
- `tags`;
- `yes_price` / `no_price` or current outcome prices;
- `market_slug`;
- `condition_id`;
- `question`;
- `retrieval_risk_flags`.

## Mapping To Market Fit Trace Agent

The app can map provider records into `CandidateMarket` as:

| Provider field | App field |
| --- | --- |
| `market_id` | `market_id` |
| `title` or `question` | `title` |
| `venue` | `venue` |
| `description` | `description` |
| `resolution_rules` | `resolution_rules` |
| `close_time` | `close_date` |
| `outcomes` | `outcomes` |
| `yes_price` or best binary price | `current_probability` |
| `retrieval_risk_flags` | `known_fit_risks` |
| `tags` + `l1` + `l2_name` | `entity_tags` |

## Evaluation Contract

We do not evaluate whether returned markets are "real"; the provider is the
source of market reality. We evaluate:

1. **Retrieval quality**
   - gold/acceptable market appears in top 5;
   - tempting wrong market appears when expected;
   - irrelevant markets are not dominant.

2. **Fit judgment**
   - final fit class is correct;
   - weak proxies are not presented as clean expressions;
   - rules/horizon/entity mismatches are mentioned.

3. **Traceability**
   - response includes `snapshot_id`, `as_of_ts`, `retrieval_id`, filters, and
     retrieval reasons;
   - returned markets can be frozen into `market_snapshots.jsonl` and
     `market_rules_snapshots.jsonl`.

## Non-Goals

The provider does not need to:

- classify market fit as `direct` / `indirect` / `weak_proxy`;
- provide trading advice;
- scan all Polymarket markets per request;
- support Kalshi in the first version;
- guarantee perfect resolution-rule capture for every market.

If full rules are not available for a returned market, set:

```json
{
  "resolution_rules": "",
  "rules_status": "missing"
}
```

The app will treat missing rules as a fit-risk signal.

## Minimal Acceptance Test

Given this request:

```json
{
  "query_text": "The Fed is not expected to cut rates until 2028.",
  "entities": ["Federal Reserve", "rates"],
  "l1_allowlist": ["macro"],
  "status": "open",
  "min_liquidity_usd": 10000,
  "top_k": 10,
  "include_rules": true
}
```

The provider should return a ranked list that includes at least one Fed rate-cut
market, includes the market rules or marks them missing, and records why it was
retrieved. The app will decide that a 2026 cut-count market is at most
`indirect` for a no-cuts-until-2028 thesis.
