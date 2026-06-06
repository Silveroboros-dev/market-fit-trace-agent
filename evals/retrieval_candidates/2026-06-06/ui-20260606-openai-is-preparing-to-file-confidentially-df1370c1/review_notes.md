# Retrieval Candidate: ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1

Human review status is candidate governance metadata. `promote` means eligible
for a later frozen strict-golden promotion. This packet does not mutate strict
expected labels by itself.

## Promotion Readiness

- Human review status: `promote`
- Reviewed at: `2026-06-06T11:27:27.464436+00:00`
- Candidate status: keep as candidate evidence until source provenance, expected
  labels, and best-market adjudication are frozen.
- Suggested future example id: `live_openai_ipo_filing_stage_mismatch`

## Claim Being Evaluated

OpenAI is preparing to file confidentially for an initial public offering in the
coming weeks.

## Golden Claim This Could Support

IPO filing or preparation evidence is not the same as a market resolving on
whether OpenAI completes an IPO by a later date. IPO completion markets can be
relevant adjacent evidence, but they should not be classified as a direct fit
for a filing/preparation thesis.

This is an `event_stage_mismatch` case:

```text
filing / confidential preparation
!= completed IPO by date
```

## Retrieved Market Roles

| Market | Role for promotion | Notes |
|---|---|---|
| `2314379` - Will OpenAI IPO by September 30 2026? | salient adjacent market | Good demo contrast. It is relevant to the thesis but resolves on IPO completion, not confidential filing/preparation. Expected class should be `indirect`, not `direct`. |
| `656312` - Will OpenAI IPO by December 31 2026? | broader adjacent market | The live run recommended this market. It is also an IPO-completion market, so it remains `indirect`; it may be less crisp for the "coming weeks" source text. |
| `2314378` - Will OpenAI IPO by August 31 2026? | adjacent market | Same event-stage mismatch as `2314379`, with a different horizon. |
| `2321571` - Will OpenAI file for an IPO by June 5, 2026? | stage-aligned but stale/wrong horizon | This market resolves on filing rather than IPO completion, but its date is already too narrow/stale for the source. Do not promote it as a clean direct market without separate adjudication. |
| OpenAI valuation threshold markets | reject / wrong metric | These resolve on valuation thresholds, not filing or IPO completion. |

## Proposed Future Strict Labels

Do not promote these labels until the blockers below are closed.

```json
{
  "expected_fit_class": "indirect",
  "expected_best_market_id": "2314379",
  "acceptable_adjacent_market_ids": ["656312", "2314378"],
  "rejected_market_ids": ["2299990", "2299992", "2299988", "2299989", "2299986", "2299987", "2299991", "2299985", "2298771", "2299995", "2298768", "2298770", "2298775"],
  "promotion_note": "IPO completion timing is relevant adjacent evidence for IPO filing/preparation, but not a direct expression of the source thesis."
}
```

## Promotion Blockers

- `source_provenance` is currently null. A source-assisted public link or saved
  source record should be attached before strict promotion.
- Extraction used fallback normalization with confidence `0.48`; freeze a
  reviewed normalized thesis or rerun with Gemini configured before promotion.
- Human review centers `2314379`, while the run recommended `656312`. Decide
  whether the future strict best market should be the narrower September market
  or the broader December market.
- No `llm_review_suggestion.json` is present for this packet. That is not fatal
  for strict promotion, but it weakens the candidate-triage audit trail.

## Demo Use

Use this as an optional live-candidate extension, not as the primary Arize trace
repair demo. The demo point is:

```text
PolyData can retrieve real OpenAI IPO markets, but the harness does not treat
IPO-completion markets as direct evidence of IPO filing/preparation.
```

Phoenix value: the live run has trace context and candidate governance metadata;
human review marks the case eligible for future promotion; only a later frozen
fixture can make it canonical eval truth.
