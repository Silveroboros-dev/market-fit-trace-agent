# Market Fit Label Guide v1

Use conservative labels. A safe no-clean answer is better than a confident weak recommendation.

## No-Drift Rule

This guide clarifies the current evaluation process; it does not relabel existing
goldens by itself. The canonical v1 labels remain the rows in
`expected_outputs.jsonl`.

Any change that would move an existing case between `direct`, `indirect`,
`weak_proxy`, and `no_clean_expression` must be handled as an eval change:

1. update the reviewed expected output row;
2. preserve the frozen market snapshot and market rules snapshot;
3. record the reason in notes or review artifacts;
4. run the strict eval command before treating the new label as accepted.

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

The market must still capture the core thesis in a defensible way. Minor
differences in source, exact terms, or horizon can make a market indirect; a
different metric, different resolution target, or materially incomplete
subcomponent should not be upgraded to indirect merely because the topic or
entities overlap.

Expected behavior: show the market as an indirect expression, explain what it captures, and state what it misses.

### Weak Proxy

Use `weak_proxy` when a market is superficially related but too stretched to recommend strongly:

- long causal chain;
- wrong entity;
- wrong horizon;
- wrong resolution target;
- market can move for many unrelated reasons.

Expected behavior: `recommended_market_id` should be null in model outputs. Related markets can appear as alternatives or adjacent markets, with limitations clearly stated.

Core thesis test: ask whether the market resolving `Yes` would substantially
verify the user's thesis, and whether resolving `No` would substantially weaken
it. If neither is true, the market is a weak proxy or no clean expression, not
an indirect fit.

Compound-thesis rule: if a thesis requires multiple material conditions and a
market resolves only one subcomponent, do not classify it as direct. Use
`indirect` only when that subcomponent is the central outcome and the omitted
conditions are secondary. Use `weak_proxy` when the omitted conditions
materially change the claim, especially when the market could resolve `Yes`
while the user's thesis is mostly false.

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

## Draft Contract Requirements

For `no_clean_expression` cases, and for weak-proxy cases where a cleaner
contract would clarify the missing expression, draft contracts should include:

- binary `Yes` / `No` outcomes;
- an objective public resolution source;
- a precise deadline;
- operational definitions for ambiguous terms;
- enough scope constraints that the contract resolves the thesis rather than a
  broad related narrative.

## Minimal Valid Example

A valid example needs all of:

- source text;
- normalized thesis;
- frozen market context;
- expected fit class;
- best, acceptable, adjacent, and rejected markets where relevant;
- explanation constraints;
- draft-contract expectation.
