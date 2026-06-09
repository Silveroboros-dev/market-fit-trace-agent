# Final Demo Script

This is the recommended 3-minute hackathon video script. The goal is to show one
governed loop, fully observable in Arize Phoenix:

```text
trace -> failure signal -> Phoenix MCP inspection -> deterministic repair -> governed eval memory
```

Intro visual: a simple `propose -> decide -> observe` spine (Section 1). Save the
richer two-loop diagram `docs/assets/mfta-two-loops.svg` for the governance /
NO-GO section, where the inner-vs-outer-loop detail earns its screen time.

Optional Veo cold-open (a Google-hackathon flourish — keep it from stealing Arize
time): the cleanest use is an ~8s Veo clip played as the visual bed *under* the
0:00-0:18 hook. You narrate over it, so it costs no extra time. Make it do
narrative work (a belief, a wall of look-alike markets, a hand grabbing the wrong
one), match the cream/amber/ink palette, and keep audio out from under the VO. If
it is not clearly good, cut it: a clean live open beats a mediocre generated one.

Target timing:

```text
0:00-0:18  hook: a thesis needs the right market (the matching trap)
0:18-0:30  what it is + why it matters ("unit tests for beliefs")
0:30-0:42  architecture: the propose -> decide -> observe spine
0:42-1:05  TPU hero trace repair (core improvement proof)
1:05-1:45  Governance 50 (supporting review memory)
1:45-2:20  repair-loop NO-GO (the payoff: the agent can reject its own fix)
2:20-2:40  Stress-40 (breadth footnote)
2:40-3:00  close: the whole Arize platform is load-bearing
```

## Framing

The emotional landing: **the agent is fully observable, repairable, and governed
— it can even reject its own proposed fix.**

- Core improvement proof: the live trace-repair loop (Section 1). Phoenix MCP
  exposes a false-strong recommendation and deterministic policy repairs it.
- Supporting evidence: Governance 50 (Section 2) shows the same truth-boundary
  discipline holding on curated review memory.
- Payoff: the bounded repair loop (Section 3) ranks a guard candidate and emits
  NO-GO. Propose a repair, and the verifier can still refuse to ship it.
- Footnote: Stress-40 (Section 4) shows the deterministic boundary holding across
  many adversarial cases; Gemini advisory numbers are variance, not a result.

## 0. Opening — Hook + What It Is — 0:00-0:30

### 0:00-0:18 — Hook (concrete, no jargon)

Visual: the live app; type the thesis in. Optional Veo clip as the visual bed
here (see the Veo note at the top) — you narrate over it, so it adds no time.

Say:

```text
If you follow AI, you have theses about how 2026 plays out - who is ahead, what
ships. Prediction markets are where a thesis actually gets tested: turned into a
resolvable, priced question. The hard part is matching your thesis to a market
that really resolves it. Take a real one: Google's TPU progress means Gemini
closes the gap. The tempting market - "is Gemini number one on the leaderboard?"
- looks right. It isn't.
```

### 0:18-0:30 — What it is + why it matters

Say:

```text
Prediction markets are basically unit tests for beliefs: they force a claim into
something resolvable and priced. So I built an agent that does this matching -
analytical support for the people who use these markets as evidence. Anyone can
call an LLM; the real engineering is catching it when it is confidently wrong.
```

## 1. Architecture + Trace Repair Proof — 0:30-1:05

### 0:30-0:42 — Architecture: the spine

Visual: `docs/assets/mfta-spine.svg` — a simple three-box graphic (the two-loop
diagram comes later, in the governance section):

```text
Gemini proposes  ->  deterministic policy decides  ->  Phoenix traces + evaluates
```

Say:

```text
The shape is simple. Gemini proposes a structured claim. Deterministic policy -
not the model - decides the fit. And Arize Phoenix traces and evaluates every
step, so when it is wrong, I can see exactly where. That observability is the
point.
```

### 0:42-1:05 — TPU hero: it catches itself

Start from the default fixture-backed demo path:

```bash
make api
```

The thesis is already on screen from the hook:

```text
Google TPU progress means Gemini closes the frontier-model gap in 2026.
```

Say, pointing at each Phoenix surface as it appears:

```text
Watch it. First pass, it overstates - it grabs that Gemini leaderboard market as
strong evidence. But the Phoenix trace flags it: weak_proxy_detected and
causal_mechanism_mismatch are right there on the span. The agent reads its own
failed trace back through Phoenix MCP, and the deterministic gate repairs the
call to weak_proxy. It caught itself - and I can prove why
(inspection_source = phoenix_mcp, fallback_used = false).
```

## 2. Governance 50 — Supporting Review Memory — 1:05-1:45

Keep this tight (≈40s). Have the local fallback JSON open in case the UI lags.

Open the Governance Dataset:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo1
```

Say:

```text
Governance 50 is the review-memory surface: a Phoenix dataset mixing strict
goldens, failure-mode goldens, reviewed candidates, drafts, and a trace-repair
case, each tagged with a truth_scope.
```

In the `Examples` tab, search `ai_startup_ipo_stage_mismatch`, then open the hero
row:

```text
gov_001_ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1
```

Point out, then move on:

```text
fit_class = indirect | truth_scope = failure_mode_golden
The source is a confidential IPO filing; the tempting market is IPO completion.
Related is not the same as resolved by the same contract.
```

Open the Phoenix Experiment:

```text
https://app.phoenix.arize.com/s/rukar570/datasets/RGF0YXNldDo2/compare?experimentId=RXhwZXJpbWVudDo3
```

Say:

```text
The experiment scores only rows with usable expected labels, so review-only data
stays visible without polluting strict accuracy: 50 governed rows, 26 scored, 19
strict, and zero stage-mismatch direct false positives.
```

## 3. Repair-Loop NO-GO — The Payoff — 1:45-2:20

This is the landing. Show the committed verdict artifact:

```text
evals/repair_loop/TOP_CANDIDATE_PROPOSAL.md
evals/repair_loop/LOOP_STATE.md
```

Say:

```text
We turn governance into an offline loop. It ranked event-stage mismatch as the
top repair candidate, drafted a minimal guard - and never applied it. The
verifier then returned NO-GO: that guard would reduce zero deterministic direct
false positives and would regress the gov_001 hero golden, downgrading cases that
are correctly indirect.

So the agent proposed a repair, and the verifier rejected it. That is the whole
point: a governed agent that can say no to itself, instead of silently rewriting
truth.
```

Optionally show the human-review artifacts the loop builds on:

```text
evals/policy_review_batches/2026-06-08/POLICY_REVIEW.md
evals/policy_review_batches/2026-06-08/POLICY_CHANGE_PROPOSAL.md
```

## 4. Stress-40 — Breadth Footnote — 2:20-2:40

Keep this to ≈15-20s. It is breadth, not the finale.

Say:

```text
Stress-40 is the breadth check. Across four committed runs of forty adversarial
cases, the deterministic class is identical on every run and deterministic direct
false positives stay at zero. Gemini's advisory proposals swing run to run, and
that variance is visible in Phoenix - but it never owns the final class.
See evals/stress_test_v1/STRESS_40_APPENDIX.md.
```

## 5. Close — The Whole Arize Platform Is Load-Bearing — 2:40-3:00

Say:

```text
None of this is logging bolted on at the end. Every Arize primitive is
load-bearing here:

- OpenInference traces make each ADK/Gemini and policy step observable.
- Trace-linked eval annotations name the failure modes.
- Phoenix MCP reads failed traces back in at runtime to drive repair.
- Phoenix Datasets hold the governed review memory.
- Phoenix Experiments score policy against expected labels.

Failures become traced, repairable, governed artifacts - not silent rewrites.
That is the submission.
```

## What To Use In The Final Demo

Primary surfaces, in order of the script:

```text
1. Product/API trace-repair run (Section 1) - the failure-to-repair loop.
2. Phoenix Dataset market_fit_governance_50 (Section 2) - governed eval memory.
3. Phoenix Experiment (Section 2) - scored policy on eligible rows.
4. evals/repair_loop/TOP_CANDIDATE_PROPOSAL.md (Section 3) - the NO-GO payoff.
```

Supporting local artifacts (show only if there is screen time):

```text
5. evals/repair_loop/LOOP_STATE.md (full bounded-loop state + gate table)
6. evals/policy_review_batches/2026-06-08/POLICY_REVIEW.md
7. evals/policy_review_batches/2026-06-08/POLICY_CHANGE_PROPOSAL.md
8. evals/stress_test_v1/STRESS_40_APPENDIX.md (deterministic stability + variance)
```

If the Phoenix UI is slow, fall back to the committed local copies:

```text
evals/market_fit_governance_50/governance_summary.json
evals/market_fit_governance_50/phoenix_experiment_result.json
```

Do not show `make api-live` in the 3-minute video. Refer to live PolyData as the
candidate-evidence path only if asked.

## What Not To Claim

Do not say all 50 rows are strict goldens.

Do not say Phoenix decides market fit.

Do not say Gemini locks expected labels.

Do not say live PolyData retrieval mutates strict eval truth.

Do not say Phoenix automatically discovered the IPO cluster through embeddings in
this version. The current demo exposes a repo-governed cluster through Phoenix
Dataset search and Experiment comparison.

Do not say the policy-review batch mutates policy code or promotes strict
goldens. It is a candidate-only human review artifact.

Do not say the current evals prove Gemini extraction quality. They prove
deterministic market-fit policy behavior and trace-backed repair; Gemini proposal
quality is trace-visible and a separate future eval target.

Do not claim "zero false positives" unqualified. The exact, defensible claim is
"deterministic direct false positives = 0 across the four committed Stress-40
runs" and "zero stage-mismatch direct false positives" in the Governance 50
experiment.
