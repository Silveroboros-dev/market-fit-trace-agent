# Minimal Data Model

Use SQLite, Postgres, Firestore, or simple JSON persistence for the demo. The model should be boring. The novelty is the traceable lifecycle.

## `sources`

- `id`
- `title`
- `source_type`
- `uri`
- `raw_text`
- `content_hash`
- `created_at`

## `agent_runs`

- `id`
- `user_goal`
- `model`
- `prompt_version`
- `phoenix_trace_id`
- `status`
- `eval_summary_json`
- `created_at`

## `claims`

- `id`
- `run_id`
- `source_id`
- `claim_text`
- `entities_json`
- `horizon`
- `stance`
- `status`: `proposed | verified | rejected | revised | needs_review`
- `confidence`
- `created_at`

## `market_fit_records`

- `id`
- `claim_id`
- `recommended_market_id`
- `semantic_fit_class`: `direct | indirect | weak_proxy | no_clean_expression`
- `fit_reason`
- `captures_json`
- `misses_json`
- `rejected_markets_json`
- `created_at`

## `human_verdicts`

- `id`
- `claim_id`
- `verdict`: `verify | reject | needs_review | corrected`
- `corrected_claim_text`
- `corrected_fit_class`
- `reviewer_note`
- `created_at`

## `eval_results`

- `id`
- `run_id`
- `claim_id`
- `phoenix_trace_id`
- `metrics_json`
- `failure_summary`
- `created_at`

## `ledger_events`

- `id`
- `run_id`
- `claim_id`
- `event_type`
- `event_payload_json`
- `created_at`

## Seed Market Object

For the hackathon, frozen candidate markets are acceptable:

- `market_id`
- `title`
- `venue`
- `description`
- `resolution_rules`
- `close_date`
- `outcomes`
- `current_probability`
- `known_fit_risks`

Do not depend on live market APIs for the first demo unless the basic trace/eval loop already works.
