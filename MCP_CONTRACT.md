# Ledger MCP Contract

This is the public-safe Product MCP. It is separate from the required partner MCP.

Required partner MCP for Rapid Arize track:

- Phoenix MCP

Internal product MCP:

- Ledger MCP

## Design Rule

Keep the Ledger MCP boring and inspectable. It should record lifecycle events, not expose the full commercial Epistemic Ledger model.

## Tools

### `propose_claim`

Purpose:

Record a normalized claim proposed by the agent.

Input:

```json
{
  "run_id": "string",
  "source_id": "string",
  "claim_text": "string",
  "entities": ["string"],
  "horizon": "string",
  "stance": "string",
  "confidence": 0.0,
  "reasoning_summary": "string"
}
```

Output:

```json
{
  "claim_id": "string",
  "status": "proposed"
}
```

### `attach_market_fit`

Purpose:

Attach the market-fit judgment and rejected tempting markets.

Input:

```json
{
  "claim_id": "string",
  "recommended_market_id": "string|null",
  "semantic_fit_class": "direct|indirect|weak_proxy|no_clean_expression",
  "fit_reason": "string",
  "captures": ["string"],
  "misses": ["string"],
  "rejected_markets": [
    {
      "market_id": "string",
      "reason": "string"
    }
  ]
}
```

Output:

```json
{
  "fit_record_id": "string",
  "status": "recorded"
}
```

### `record_eval_result`

Purpose:

Record trace-linked eval results for the run or claim.

Input:

```json
{
  "run_id": "string",
  "claim_id": "string|null",
  "phoenix_trace_id": "string",
  "metrics": {
    "schema_valid": true,
    "false_strong_recommendation": false,
    "weak_proxy_detected": true,
    "unsupported_implication": false,
    "human_verification_required": true
  },
  "failure_summary": "string|null"
}
```

Output:

```json
{
  "eval_record_id": "string",
  "status": "recorded"
}
```

### `record_human_verdict`

Purpose:

Record human review.

Input:

```json
{
  "claim_id": "string",
  "verdict": "verify|reject|needs_review|corrected",
  "corrected_claim_text": "string|null",
  "corrected_fit_class": "direct|indirect|weak_proxy|no_clean_expression|null",
  "reviewer_note": "string"
}
```

Output:

```json
{
  "verdict_id": "string",
  "claim_status": "verified|rejected|needs_review|revised"
}
```

### `query_claim_trace`

Purpose:

Return the claim lifecycle for UI and agent inspection.

Input:

```json
{
  "claim_id": "string"
}
```

Output:

```json
{
  "claim_id": "string",
  "status": "string",
  "events": [
    {
      "event_type": "string",
      "created_at": "string",
      "summary": "string"
    }
  ]
}
```

## Deliberately Excluded

Do not expose in the public hackathon MCP:

- authority-band policy;
- karma economics;
- commercial trust scoring;
- proprietary market-fit ranking internals;
- private user profiles;
- execution intent logic;
- paid report workflow;
- full institutional data model.
