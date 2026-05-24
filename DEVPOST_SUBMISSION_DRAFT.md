# Devpost Submission Draft

Use this as copy for the Google Cloud Rapid Agent Hackathon submission form.

## General Info

Project name:

```text
Market Fit Trace Agent
```

Elevator pitch:

```text
Runs a supervised Gemini market-fit audit mission with Phoenix traces and evals so tempting weak prediction-market proxies are caught before users trust them.
```

Thumbnail:

```text
docs/assets/devpost-thumbnail-market-fit-v3.png
```

## Submission Links

Hosted app URL:

```text
TODO: paste Cloud Run URL
```

Code repository:

```text
TODO: paste public GitHub repository URL
```

Demo video:

```text
TODO: paste public YouTube or Vimeo URL, under 3 minutes
```

Selected partner track:

```text
Arize
```

## Short Description

```text
Market Fit Trace Agent helps analysts audit whether a prediction market actually expresses a pasted thesis, or whether it is only a tempting weak proxy. It is a multi-step agent mission under human oversight: Gemini drafts the normalized claim and candidate fit explanation, deterministic evals classify the market-fit risk, Phoenix/OpenInference traces make the failed first run inspectable, and Phoenix MCP trace context helps the second run improve. A small project-local Ledger MCP records the claim lifecycle and human verdict.
```

## Inspiration

```text
Prediction-market users often start from messy evidence: a post, a model-release note, a market rumor, or a thesis written in natural language. Agents are good at finding related markets, but related is not the same as correct. The dangerous failure is when an agent presents a weak proxy as a clean expression of the thesis. This project was built to make that failure visible, auditable, and correctable.
```

## What It Does

```text
The app accepts a pasted thesis or source, extracts a normalized claim, identifies entities, horizon, and stance, compares the claim to candidate prediction-market expressions, and classifies the fit as direct, indirect, weak_proxy, or no_clean_expression.

The demo intentionally starts with a tempting market match that looks useful but is too weak to trust. The system flags the false strong recommendation, explains rejected markets without overclaiming, asks the human to verify or correct the result, records the lifecycle, and shows a second run that improves after inspecting the failed Phoenix trace/eval. The result is not chat; it is a supervised audit workflow with state, tools, evals, and trace-backed correction.
```

## How We Built It

```text
The backend is a FastAPI app wrapped around one deployable Google ADK agent, MarketFitTraceAgent. Gemini is accessed through ADK for claim extraction and proposal steps. Deterministic Python code performs the final market-fit classification, weak-proxy checks, trace-linked evals, and human-verdict handling.

The app emits OpenInference traces to Phoenix when configured with Phoenix credentials. It also includes a Phoenix MCP bridge for trace inspection and a small Ledger MCP for claim lifecycle events. Seed market snapshots, golden evals, and an intake gate for candidate goldens keep the demo replayable, while the Cloud Run deployment path keeps the hosted app simple.
```

## Technologies Used

```text
Google ADK, Gemini, Google Cloud Run, FastAPI, Python, OpenInference, Arize Phoenix, Phoenix MCP, MCP, deterministic eval fixtures, HTML/CSS/JavaScript UI
```

## Data Sources

```text
The prototype uses public-safe seed prediction-market snapshots included in the repository. The demo does not require wallet access, private data, customer data, trading automation, or live market execution.
```

## Challenges

```text
The main challenge was keeping the architecture narrow enough for a reliable hackathon demo while still making the Arize/Phoenix integration meaningful. Another challenge was separating what Gemini may draft or explain from what deterministic code must decide, so the demo could show traceability without turning the LLM output into the final authority.
```

## Accomplishments

```text
The project demonstrates a full thesis-to-audit lifecycle: pasted thesis, Gemini-assisted claim extraction, candidate market-fit classification, weak-proxy detection, rejected market explanations, Phoenix trace/eval visibility, Phoenix MCP-supported improvement, human verdict, and Ledger MCP lifecycle record. The original 10 baseline goldens were replayed through live ADK/Gemini and Phoenix, passing 10/10 with trace URLs and eval annotations.
```

## What We Learned

```text
For this workflow, observability is not backend plumbing. It is part of the product. A trace is useful because it lets the user see exactly where the agent overstated a market fit, run evals against that failure, and improve the next run without hiding the correction behind vague agentic behavior.
```

## What's Next

```text
Next steps are final hosted Cloud Run verification, broader promoted golden eval coverage, more candidate market snapshots, and a clearer Phoenix MCP inspector view in the UI. The product should stay narrow: it audits market-fit claims, records human review, and avoids trading automation or broad investment advice.
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
0:00-0:20 Problem: related markets are not always correct market expressions.
0:20-0:40 Product: Market Fit Trace Agent catches tempting weak proxies.
0:40-1:30 First run: thesis -> Gemini extraction -> candidate market -> false strong recommendation eval.
1:30-2:00 Human review: reject or downgrade, Ledger MCP records the verdict.
2:00-2:40 Trace inspection: Phoenix trace/eval explains the failure, second run improves.
2:40-3:00 Close: auditable market-fit judgment, not trading advice or generic claim checking.
```

## Final Placeholders To Replace

- Hosted app URL
- Public GitHub repository URL
- Public YouTube or Vimeo video URL
- Phoenix trace URL or screenshot used in the video
- Final Cloud Run region/project wording, if shown in the description
