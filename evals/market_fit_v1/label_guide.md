# Market Fit Label Guide v1

Use conservative labels. A safe no-clean answer is better than a confident weak recommendation.

## Semantic Fit Classes

`semantic_fit_class` must be one of:

- `direct`
- `indirect`
- `weak_proxy`
- `no_clean_expression`

### Direct

Use `direct` only when the market maps cleanly to the thesis:

- same event;
- same or very close horizon;
- same direction;
- clear resolution logic;
- no meaningful proxy chain.

Expected behavior: recommend the market as the direct expression and explain why title, rules, horizon, and stance align.

### Indirect

Use `indirect` when the market is related and useful but not exact:

- same theme or causal driver;
- related but different event;
- imperfect horizon;
- plausible but impure exposure.

Expected behavior: show the market as an indirect expression, explain what it captures, and state what it misses.

### Weak Proxy

Use `weak_proxy` when a market is superficially related but too stretched to recommend strongly:

- long causal chain;
- wrong entity;
- wrong horizon;
- wrong resolution target;
- market can move for many unrelated reasons.

Expected behavior: `recommended_market_id` should be null in model outputs. Related markets can appear as alternatives or adjacent markets, with limitations clearly stated.

### No Clean Expression

Use `no_clean_expression` when no available market is a reasonable expression of the thesis.

Expected behavior:

- say no clean expression exists;
- explain why current markets are poor fits;
- draft an objectively resolvable hypothetical contract.

## Scenario Tags

Scenario tags are separate from semantic fit. Use any that apply:

- `ambiguous`
- `overbroad`
- `compound`
- `resolution_risk`
- `duplicate`
- `wrong_market`
- `wrong_horizon`
- `misleading_title`
- `similar_entities`
- `sarcasm_or_irony`
- `unsupported_implication`
- `adversarial`
- `public_figure_signal`
- `market_moving_statement`
- `authority_bias_risk`
- `requires_securities_caution`

## Annotation Rules

1. Inspect market rules, not only titles.
2. Mark horizon mismatch explicitly.
3. Keep semantic fit separate from expected profitability.
4. Record tempting rejected markets.
5. Do not use investment-advice language.
6. Draft contracts must be binary, objective, and time-bounded.
7. Public-figure examples are public-signal stress tests, not celebrity-following examples.

## Minimal Valid Example

A valid example needs all of:

- source text;
- normalized thesis;
- frozen market context;
- expected fit class;
- best, acceptable, adjacent, and rejected markets where relevant;
- explanation constraints;
- draft-contract expectation.
