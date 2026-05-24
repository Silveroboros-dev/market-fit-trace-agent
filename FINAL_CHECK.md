# Final Before-Submission Checklist

Use this as a GO / NO-GO gate before submitting to the Google Cloud Rapid Agent Hackathon.

Official source of truth:

- Rapid Agent Hackathon rules: https://rapid-agent.devpost.com/rules
- Rapid Agent Hackathon overview: https://rapid-agent.devpost.com/
- Arize track resources: https://rapid-agent.devpost.com/details/arize-resources

Rule context verified on 2026-05-23: the Devpost rules list a contest period from May 5, 2026 to June 11, 2026 at 2:00 PM PDT. Submission requirements include a hosted project URL, public open-source code repository with visible license, text description, selected partner track, and a public demo video on YouTube or Vimeo that should not exceed 3 minutes. The project must be a functional agent powered by Gemini and Google Cloud Agent Builder, integrate a Partner Entity MCP server, and enter one partner track: Arize, Elastic, Fivetran, GitLab, or MongoDB. Re-check the official rules immediately before submission because rules can change.

## 0. Official Submission Compliance Gate

Skill to invoke: none; do manually first.

Before final submission, verify official rules, deadline, selected track, video, repo, hosted app, and partner integration requirements.

Check:

- [ ] Submission deadline and timezone confirmed against official Devpost rules.
- [ ] Correct hackathon selected: Google Cloud Rapid Agent Hackathon.
- [ ] Selected track is explicit: Arize.
- [ ] Hosted project URL is ready for judging/testing.
- [ ] Public open-source repository URL is ready for judging/testing.
- [ ] Repository contains all necessary source code, assets, and instructions.
- [ ] Repository includes a visible open-source license.
- [ ] Project uses Gemini and Google Cloud tooling in the deployed application.
- [ ] Project meaningfully integrates the Arize/Phoenix partner MCP or clearly shows the Arize partner integration path.
- [ ] Project uses OpenInference/Phoenix traces and evals visibly enough for the Arize track.
- [ ] Any pre-existing code, templates, boilerplate, or framework usage is clearly disclosed.
- [ ] Third-party APIs, SDKs, datasets, and libraries are legally usable.
- [ ] Demo video is public on YouTube or Vimeo and under 3 minutes.
- [ ] Video shows the project functioning on the platform for which it was built.
- [ ] Video has no unauthorized music, trademarks, copyrighted material, or third-party advertising/sponsorship content.
- [ ] Submission materials are in English or include English subtitles/translations.
- [ ] Written project description explains features, functionality, technologies used, data sources, findings/learnings, Arize track relevance, Gemini usage, Google Cloud usage, and why the project matters.

NO-GO if: Gemini, Google Cloud, or Arize/Phoenix are only mentioned in the pitch but not actually used or demonstrated in the deployed app.

## 1. Scope And Asymmetry Check

Skill to invoke:

```text
$hackathon-asymmetry-check Audit the final submission scope. Identify anything that should be cut, stubbed, or simplified before submission. Focus on judge-visible value versus implementation complexity.
```

Check:

- [ ] The project has one clear "Aha!" moment.
- [ ] The demo proves one strong thesis, not five weak ones.
- [ ] Every visible feature supports the judging story.
- [ ] Backend plumbing that judges cannot see is minimized.
- [ ] Non-critical features are cut or stubbed.
- [ ] Demo path works without explaining a complex roadmap.
- [ ] The first 30 seconds of the demo make the value obvious.
- [ ] The project can be described in one sentence.

One-sentence test:

```text
[Product] helps [specific user] achieve [specific outcome] by using Gemini to [specific AI-native mechanism], while [your system/kernel/workflow] makes the result trustworthy/actionable.
```

For this repo:

```text
Market Fit Trace Agent helps prediction-market analysts audit messy theses by using Gemini/ADK to extract and propose market-fit signals, while deterministic evals, human review, Phoenix traces, and a ledger workflow prevent weak proxies from becoming trusted recommendations.
```

NO-GO if: the pitch requires a 10-minute explanation before the judge understands why it matters.

## 2. Architecture Stress-Test

Skill to invoke:

```text
$epistemic-architecture-review Stress-test the final architecture for API assumptions, state complexity, failure modes, and value-to-complexity ratio.
```

Check:

- [ ] Architecture has a clear causal path:

```text
input thesis/source -> Gemini extraction/proposal -> normalized claim -> deterministic market-fit eval -> human verdict -> ledger record -> Phoenix trace/eval output
```

- [ ] Gemini's role is explicit.
- [ ] Deterministic code's role is explicit.
- [ ] Phoenix/OpenInference's role is explicit.
- [ ] Ledger MCP's role is explicit and not ornamental.
- [ ] Phoenix MCP's role is explicit and demo-relevant.
- [ ] The system does not rely on vague "agentic magic."
- [ ] State transitions are minimal and understandable.
- [ ] Async/background complexity is avoided unless absolutely necessary.
- [ ] Every external integration has a fallback or demo-safe fixture.
- [ ] Architecture diagram matches actual code.
- [ ] README claims match actual implemented behavior.
- [ ] No ornamental architecture remains.

Core architecture invariant:

```text
Gemini drafts, extracts, summarizes, reasons, or proposes.
The deterministic layer verifies, gates, decides, logs, and makes the final auditable output.
Phoenix traces and evals make the failure/improvement loop inspectable.
```

NO-GO if: the project claims "verification" but final market-fit decisions are actually made by an LLM without deterministic checks.

## 3. Minimum Viable Experiment / API Spike Check

Skill to invoke:

```text
$minimum-viable-experiment Review the riskiest technical assumptions and confirm each has been tested with the smallest reproducible experiment.
```

Check:

- [ ] Gemini/ADK call works in the deployed app.
- [ ] Gemini output format is tested, not assumed.
- [ ] Structured JSON extraction works on realistic fixtures.
- [ ] Failure behavior is known when Gemini returns malformed/partial output.
- [ ] Phoenix trace export works with live Arize/Phoenix credentials.
- [ ] Phoenix MCP trace inspection works, or the fallback is clearly labelled as local-only.
- [ ] Rate limits, latency, or timeout risks are understood.
- [ ] Required environment variables are documented.
- [ ] App can run from clean setup instructions.
- [ ] There is a fallback path for demo if live API call fails.
- [ ] At least one command proves the core pipeline works.

Minimum acceptable spike:

```bash
uv run --python 3.11 python scripts/smoke_arize_adk.py
```

Offline fallback check:

```bash
uv run --python 3.11 python scripts/smoke_arize_adk.py --offline
```

Expected output should show:

1. Thesis/source loaded
2. Gemini/ADK extraction or fallback path identified
3. Claim normalized
4. Deterministic market-fit eval applied
5. Ledger/audit output generated
6. Phoenix trace ID or explicit local fallback trace ID

NO-GO if: the main AI/trace path only worked once manually in a notebook or local shell.

## 4. Evals And Golden Cases Check

Skill to invoke:

```text
$evals-golden-builder Audit the final eval suite. Confirm that public claims are backed by deterministic tests, golden fixtures, or visible demo cases.
```

Check:

- [ ] There are golden fixtures for the main demo flow.
- [ ] Happy-path examples pass.
- [ ] Ambiguous thesis examples are handled correctly.
- [ ] Missing/unsupported market expression does not produce false certainty.
- [ ] Tempting weak proxies are detected.
- [ ] False strong recommendations are tested.
- [ ] At least one adversarial case is included.
- [ ] Eval command is documented.
- [ ] Eval results are reproducible.
- [ ] README/demo claims link to actual eval behavior.
- [ ] Eval results are visible in the UI or Phoenix trace/annotation flow.

Minimum eval command:

```bash
uv run --python 3.11 python scripts/run_evals.py
```

Minimum eval categories:

- correct extraction
- weak-proxy detection
- false strong recommendation prevention
- no-clean-expression precision
- deterministic policy decision
- audit trace generation

For this repo, the most important eval is:

```text
Does the system prevent a tempting weak-proxy market from being treated as a clean or strong market expression?
```

NO-GO if: the README claims "trustworthy," "verified," "traceable," or "auditable" but there are no evals or fixtures proving that behavior.

## 5. MCP Contract Check

Skill to invoke:

```text
$mcp-contract-designer Audit the MCP surface. Confirm that tools/resources are narrow, useful, safe, and demo-relevant.
```

Check:

- [ ] Ledger MCP exists because it materially improves traceable lifecycle recording.
- [ ] Phoenix MCP exists because it materially improves Arize-track trace inspection.
- [ ] MCP tools are narrow and schema-constrained.
- [ ] Read-only resources are separated from write/action tools where practical.
- [ ] Each MCP tool has one clear purpose.
- [ ] Inputs and outputs are documented.
- [ ] Example request/response is included.
- [ ] Side effects are explicit.
- [ ] Permissions are conservative.
- [ ] MCP is not required for the demo unless it is reliable.
- [ ] MCP does not add unnecessary judging confusion.

Minimum MCP tool documentation:

```text
Tool name:
Purpose:
Input schema:
Output schema:
Side effects:
Failure behavior:
Example:
```

Current Ledger MCP tools to verify:

- propose_claim
- attach_market_fit
- record_eval_result
- record_human_verdict
- query_claim_trace

NO-GO if: MCP is included because it sounds advanced, but the project works better without it.

## 6. Demo-Readiness Audit

Skill to invoke:

```text
$demo-readiness-audit Audit the repo, README, setup, demo script, video path, claims, and fragile points as if submission is due now.
```

Check:

- [ ] Demo can be run from a clean checkout.
- [ ] Setup instructions are complete.
- [ ] `.env.example` exists if needed.
- [ ] No secrets are committed.
- [ ] Demo data/fixtures are included.
- [ ] Demo does not depend on private local files.
- [ ] Demo does not require unexplained manual steps.
- [ ] Hosted app URL works.
- [ ] Public demo link works without login/paywall unless login is explicitly allowed and credentials are provided.
- [ ] Video path is identical to real working product flow.
- [ ] README explains what to click/run.
- [ ] Known limitations are honestly stated.
- [ ] The fallback demo path is ready and labelled as fallback.

Minimum README structure:

```text
# Project Name
## One-sentence summary
## What it does
## Why it matters
## Gemini / Google Cloud integration
## Arize / Phoenix integration
## Architecture
## How to run
## Demo flow
## Evals/tests
## Limitations
```

NO-GO if: the demo works only on your machine after undocumented manual setup.

## 7. Repository Hygiene Check

Skill to invoke: usually `$demo-readiness-audit`, but this can be manual.

Check:

- [ ] Repo name is clean and submission-ready.
- [ ] README is updated.
- [ ] License included and visible.
- [ ] `.gitignore` is correct.
- [ ] `.env.example` included.
- [ ] No API keys, tokens, credentials, private data, or customer info committed.
- [ ] Install command works.
- [ ] Run command works.
- [ ] Test/eval command works.
- [ ] Demo command works.
- [ ] Dependency versions are pinned enough for reproducibility.
- [ ] Dead files, abandoned experiments, and broken notebooks are removed or clearly separated.
- [ ] Screenshots or architecture images are up to date.
- [ ] Public-facing text does not overclaim.

Suggested final commands:

```bash
git status
uv run --python 3.11 --extra dev ruff check .
uv run --python 3.11 --extra dev pytest
uv run --python 3.11 python scripts/run_evals.py
uv run --python 3.11 python scripts/smoke_arize_adk.py --offline
```

NO-GO if: judging requires guessing how to run the project.

## 8. Submission Story Check

Skill to invoke:

```text
$hackathon-asymmetry-check Review the final submission text and video script. Cut weak claims and sharpen the core story.
```

Check:

- [ ] The title is understandable.
- [ ] The tagline is specific.
- [ ] The problem is concrete.
- [ ] The user is clear.
- [ ] Gemini usage is central, not decorative.
- [ ] Arize/Phoenix usage is central for trace/eval proof, not decorative.
- [ ] The demo shows the product, not slides only.
- [ ] The selected Arize track fit is explicit.
- [ ] The final claim is defensible.

Strong structure:

```text
Problem:
Prediction-market users can mistake adjacent markets for clean expressions of a thesis.

Insight:
Finding a related market is easy; proving whether it really expresses the thesis is the hard part.

Solution:
Gemini extracts and proposes candidate market-fit signals. Deterministic evals decide whether the expression is direct, indirect, weak_proxy, or no_clean_expression.

Demo:
A messy Gemini/TPU thesis enters. A tempting leaderboard market is initially overclassified. The eval flags the weak proxy. Human review records a correction. Phoenix trace inspection drives an improved second run.

Track proof:
OpenInference/Phoenix traces, evals, and MCP inspection make the failure/improvement loop visible.
```

NO-GO if: the story sounds like "we built an AI chatbot that helps with prediction markets."

## 9. Arize Track Proof Check

For this Rapid submission, Arize proof is not optional polish. It is the selected partner track.

Check:

- [ ] Phoenix project contains demo traces.
- [ ] Trace includes ADK/Gemini model spans or a clear Google Cloud/Gemini span path.
- [ ] Trace includes product spans: claim extraction, candidate loading, fit classification, eval, ledger, verdict, trace inspection.
- [ ] Eval metrics are visible in app and/or Phoenix annotations.
- [ ] Phoenix MCP is configured and can inspect a failed trace, or local fallback is clearly not presented as live Phoenix MCP.
- [ ] Second run improvement is visible.
- [ ] UI exposes trace ID or Phoenix trace link.
- [ ] README explains how to reproduce the Arize/Phoenix run.

NO-GO if: Arize is only mentioned in README but no trace/eval can be opened by a judge.

## 10. Video Checklist

Skill to invoke:

```text
$demo-readiness-audit Review the demo video script against the actual product. Ensure every claim shown in the video is backed by working software.
```

Check:

- [ ] Under 3 minutes.
- [ ] Publicly visible on YouTube or Vimeo.
- [ ] No copyrighted music/material unless authorized.
- [ ] First 15 seconds state problem and product.
- [ ] Gemini usage is visible or clearly explained.
- [ ] Arize/Phoenix trace/eval usage is visible.
- [ ] Actual product is shown.
- [ ] Core "Aha!" moment happens before 90 seconds.
- [ ] Verification/eval/trust mechanism is shown, not just claimed.
- [ ] Ending states what has been achieved, not only what will be built later.

Suggested 3-minute structure:

```text
0:00-0:20 Problem and stakes
0:20-0:40 Product promise
0:40-1:40 Live demo: thesis -> Gemini extraction -> market-fit eval -> ledger output
1:40-2:20 Arize proof: Phoenix trace, eval failure, trace inspection
2:20-2:45 Second run improvement
2:45-3:00 Why this matters / selected Arize track
```

NO-GO if: the video is mostly conceptual slides and does not show the product working.

## Final Codex Invocation Sequence

Run these in this order before submission:

```text
$hackathon-asymmetry-check
Audit the final scope and identify what must be cut, stubbed, or clarified before submission.

$epistemic-architecture-review
Stress-test the final architecture. Check whether Gemini, deterministic verification, state flow, Phoenix traces/evals, MCP, and audit output are cleanly separated and actually implemented.

$minimum-viable-experiment
Review the riskiest technical assumptions and confirm each has been validated by a reproducible spike, test, or demo command.

$evals-golden-builder
Audit the evals/golden fixtures and confirm they support the public trust, verification, and auditability claims.

$mcp-contract-designer
Audit the MCP layer. Confirm it is useful, narrow, safe, and not ornamental.

$demo-readiness-audit
Audit the repo, setup, demo path, README, video script, submission claims, and fragile points as if judging starts now.
```

## Final GO / NO-GO Decision

Submit only if all five are true:

- [ ] Demo works from clean setup and hosted public link.
- [ ] Gemini and Google Cloud are central and visibly used.
- [ ] Arize/Phoenix trace/eval integration is real and judge-visible.
- [ ] Core claim is proven by working software, not roadmap language.
- [ ] Submission package is complete: hosted app URL, public repo URL, license, description, selected Arize track, video, and Devpost form.

Final rule:

```text
If a judge cannot understand, run, and believe the project in under 5 minutes, cut scope until they can.
```
