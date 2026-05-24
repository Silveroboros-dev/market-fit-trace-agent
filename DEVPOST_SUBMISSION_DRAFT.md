# Devpost Submission Draft

Use this as copy for the Google Cloud Rapid Agent Hackathon submission form.

## General Info

Project name:

```text
Market Fit Trace Agent
```

Elevator pitch:

```text
A Gemini + Phoenix agent that audits whether a thesis has a clean prediction-market expression, and uses Phoenix MCP trace context to correct tempting weak-proxy recommendations before users trust them.
```

Thumbnail:

```text
docs/assets/devpost-thumbnail-market-fit-v3.png
```

## Submission Links

Hosted app URL:

```text
TODO: paste Cloud Run URL before submission
```

Code repository:

```text
https://github.com/Silveroboros-dev/market-fit-trace-agent
```

Demo video:

```text
TODO: paste public YouTube or Vimeo URL, under 3 minutes
```

Phoenix trace proof:

```text
https://app.phoenix.arize.com/s/rukar570/traces/1bd413f984576d145b2dd41b32dc6507
```

Phoenix audit/proof docs:

```text
https://github.com/Silveroboros-dev/market-fit-trace-agent/blob/main/evals/market_fit_v1/v1_trace_audit.md
https://github.com/Silveroboros-dev/market-fit-trace-agent/blob/main/docs/phoenix-value-proof.md
```

Selected partner track:

```text
Arize
```

## Short Description

```text
Market Fit Trace Agent helps analysts audit whether a prediction market actually expresses a pasted thesis, or whether it is only a tempting weak proxy. Gemini, running through Google ADK, drafts the normalized claim and candidate fit explanation. Deterministic code classifies the fit as direct, indirect, weak_proxy, or no_clean_expression.

The Arize/Phoenix integration is part of the product loop, not just logging: OpenInference traces and trace-linked evals make a failed first run inspectable, and Phoenix MCP trace context helps the second run improve. A small project-local Ledger MCP records the claim lifecycle and human verdicts.
```

## Inspiration

```text
Prediction-market users often start from messy evidence: a post, a model-release note, a market rumor, or a thesis written in natural language. Agents are good at finding related markets, but related is not the same as correct. The dangerous failure is when an agent presents a weak proxy as a clean expression of the thesis.

This project was built to make that failure visible, auditable, and correctable before a user trusts the recommendation.
```

## What It Does

```text
The app accepts a pasted thesis or source, extracts a normalized claim, identifies entities, horizon, and stance, compares the claim to frozen candidate prediction-market snapshots, and classifies fit as direct, indirect, weak_proxy, or no_clean_expression.

The demo intentionally starts with a tempting market match that looks relevant but is too weak to trust. The first run overstates the fit. A trace-linked eval flags the false strong recommendation. Phoenix/OpenInference traces make the failure inspectable, Phoenix MCP supplies trace context for the improve step, and the second run downgrades the market to weak_proxy.

The practical value is not finding "a related market"; it is preventing a user from mistaking a correlated or adjacent market for a clean expression of their thesis. The result is not open-ended chat. It is a supervised audit workflow with state, tools, evals, human review, and trace-backed correction.
```

## How We Built It

```text
The backend is a FastAPI app wrapped around one deployable Google ADK agent. Gemini is accessed through ADK for claim extraction and proposal steps. Deterministic Python code performs the final market-fit classification, weak-proxy checks, trace-linked evals, and human-verdict handling.

For the Arize track, the app emits OpenInference-compatible traces to Phoenix, including ADK/Gemini spans and product-level fit/eval spans. Phoenix MCP is used by the improve step to inspect failed trace/eval context at runtime. A small Ledger MCP records claim lifecycle events, while seed market snapshots, golden evals, and candidate-intake checks keep the demo replayable.
```

## Built With Partner Track

```text
Arize/Phoenix is used in four ways:
1. OpenInference instrumentation sends ADK/Gemini and product-level spans to Phoenix.
2. Trace-linked evals annotate failures such as false_strong_recommendation and weak_proxy_detected.
3. Phoenix MCP is used during the improve step to inspect failed trace/eval context at runtime.
4. The second run uses that trace context to downgrade an over-strong market recommendation to weak_proxy.

This is why Phoenix is part of the agent's correction loop, not only backend logging.
```

## Technologies Used

```text
Google ADK, Gemini, Google Cloud Run, FastAPI, Python, OpenInference, Arize Phoenix, Phoenix MCP, Model Context Protocol, deterministic eval fixtures, HTML/CSS/JavaScript
```

## Data Sources

```text
The prototype uses public-safe frozen prediction-market snapshots included in the repository. The frozen snapshots make the demo and evals reproducible. The app does not require wallet access, private data, customer data, trading automation, or live market execution.
```

## Challenges

```text
The main challenge was making the Arize/Phoenix integration meaningful rather than decorative. The trace had to become part of the product loop: first run, failed fit judgment, trace-linked eval, Phoenix MCP inspection, improved second run.

The second challenge was maintaining a strict trust boundary: Gemini may draft, extract, and explain, but deterministic code performs the final market-fit classification and eval scoring.
```

## Accomplishments

```text
The project demonstrates a full thesis-to-audit lifecycle: pasted thesis, Gemini-assisted claim extraction, candidate market-fit classification, weak-proxy detection, rejected-market explanations, Phoenix trace/eval visibility, Phoenix MCP-backed improve path, human verdict, and Ledger MCP lifecycle record.

The original 10 baseline goldens were replayed through live ADK/Gemini and Phoenix, passing 10/10 with trace URLs and eval annotations. The observed replay is documented in evals/market_fit_v1/v1_trace_audit.md and linked from the README, alongside a Phoenix value-proof document that defines the live improve pass conditions.
```

## What We Learned

```text
For this workflow, observability is not backend plumbing. It is part of the product. A trace is useful because it shows exactly where the agent overstated market fit, lets evals attach to that failure, and gives the next run concrete context for correction instead of hiding the change behind vague "agent improvement."
```

## What's Next

```text
Next steps are broader promoted golden eval coverage, more candidate market snapshots, a richer Phoenix MCP inspector view in the UI, and support for additional prediction-market platforms. The product should stay narrow: it audits market-fit claims, records human review, and avoids trading automation or broad investment advice.
```

## Suggested Tags

```text
google-cloud
gemini
google-adk
cloud-run
arize
phoenix
openinference
mcp
fastapi
python
evals
agents
```

## Video Script Skeleton

```text
0:00-0:20 Problem: a related prediction market is not always a correct expression of a thesis.
0:20-0:40 Product: Market Fit Trace Agent audits thesis-to-market fit and catches weak proxies.
0:40-1:15 First run: thesis -> Gemini extraction -> candidate market -> over-strong fit.
1:15-1:45 Phoenix proof: OpenInference trace + fit_eval_run span show the false strong recommendation / weak-proxy risk.
1:45-2:15 Phoenix MCP improve step: inspect failed trace context and rerun.
2:15-2:40 Second run: classification downgrades to weak_proxy; eval clears; ledger records lifecycle.
2:40-3:00 Close: trace-backed market-fit audit, not trading advice and not generic claim checking.
```

## Final Proof Gate Before Paste

- Hosted app URL inserted.
- Public video URL inserted.
- Phoenix trace proof link or screenshot inserted.
- README has the same story as Devpost.
- The video shows the improve response with `inspection_source: phoenix_mcp` and `fallback_used: false` before claiming observed Phoenix MCP correction.
- No claim says "10/10 live" unless the trace audit artifact remains linked.
- "What's Next" does not include basic final verification.
- Video shows Phoenix before the final minute.
