# New Session Prompt

We are starting a new Google Cloud Rapid Agent Hackathon project in this fresh folder.

Build a new project called **Market Fit Trace Agent**. It must be original hackathon work, not a fork or extension of the existing Epistemic Ledger app. Epistemic Ledger is only product context.

Goal:

Create a Gemini-powered, Google Cloud-hosted agent that helps a user audit a prediction-market thesis. The agent should:

1. Accept a pasted thesis/source.
2. Extract a normalized claim, entities, horizon, and stance.
3. Compare the claim to candidate prediction-market expressions.
4. Classify the result as `direct`, `indirect`, `weak_proxy`, or `no_clean_expression`.
5. Explain rejected tempting markets without overclaiming.
6. Ask the human to verify, reject, or correct the result.
7. Record the lifecycle through a small Ledger MCP.
8. Emit OpenInference traces to Phoenix.
9. Run trace-linked evals, especially false strong recommendation and weak-proxy detection.
10. Use Phoenix MCP to inspect a failed run and improve a second run.

Track:

Use the **Arize** partner track. The project must visibly use OpenInference tracing, Phoenix Cloud or self-hosted Phoenix, Phoenix MCP, and evals on traces.

Implementation preference:

- Use one deployable agent first.
- Optional second component: a Fit Challenger implemented as either an eval job or a small internal checker.
- Keep total agents under 3.
- Prefer FastAPI backend and a simple Next.js or Streamlit UI.
- Deploy to Cloud Run when practical.
- Use Gemini through Google Cloud tooling.

Public repo boundary:

Open-source the demo app, small Ledger MCP, public-safe schema, eval harness, and seed examples. Do not open-source commercial moat details, authority-band policy, karma economics, proprietary market-fit scoring, private data, or full Epistemic Ledger architecture.

Important constraints:

- Rapid contest period: May 5, 2026 to June 11, 2026 at 2:00 PM PT.
- Public repo must include an open-source license.
- Submission must include hosted app URL, public repo URL, demo video, selected track, and Devpost form.
- Video should be under 3 minutes.
- Use Google Cloud AI tools and the selected partner products. Do not use competing AI tooling.

Please first inspect this folder, read the package docs, then propose the smallest vertical slice. After that, implement unless a specific decision is genuinely blocked.
