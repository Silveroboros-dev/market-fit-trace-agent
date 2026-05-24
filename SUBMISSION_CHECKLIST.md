# Submission Checklist

## Rapid Requirements

- Project created during contest period: May 5, 2026 to June 11, 2026 at 2:00 PM PT.
- Uses Gemini / Google Cloud AI tools.
- Uses selected partner product: Arize.
- Integrates partner MCP: Phoenix MCP.
- Runs on web, Android, or iOS. Web is recommended.
- Hosted project URL.
- Public open-source repository.
- License visible in repo.
- README includes setup instructions.
- Demo video is public on YouTube or Vimeo.
- Demo video is not longer than 3 minutes.
- Written/demo content supports English.
- Devpost form completed.

## Technical Proof

- Code-owned agent runtime, not visual Agent Builder alone.
- OpenInference traces emitted.
- Phoenix project has traces for demo runs.
- Phoenix MCP configured.
- Trace IDs stored in app run records.
- Eval summary visible in UI.
- Ledger MCP records claim lifecycle.
- Human verdict changes record status.
- Second run improves after trace inspection.
- Live improve response shows `inspection_source: phoenix_mcp`.
- Live improve response shows `fallback_used: false`.
- Public proof links include either an accessible Phoenix trace or a video segment
  showing the Phoenix trace, plus the GitHub audit artifact.

## Product Proof

- One clear target user.
- One concrete real-world workflow.
- One weak-proxy or false-strong-recommendation failure.
- One human correction.
- One before/after comparison.
- No trading automation.
- No broad investment advice.

## Final Demo Flow

- Paste thesis.
- Run agent.
- Show extracted claim.
- Show candidate market fit.
- Show eval failure.
- Open Phoenix trace.
- Show `fit_eval_run` span and eval annotations.
- Trigger self-improvement.
- Show `inspection_source: phoenix_mcp` and `fallback_used: false`.
- Show improved second run.
- Show human verdict or ledger lifecycle event.

## Final Proof Gate

- Hosted app URL works.
- Public video URL works and is under 3 minutes.
- Public repository URL works and license is visible.
- Phoenix trace link works publicly, or the video clearly shows the trace and the
  GitHub audit artifact is linked.
- Video shows Phoenix before the final minute.
- Video shows the improve response or UI evidence for
  `inspection_source: phoenix_mcp`.
- Video or proof docs show `fallback_used: false` for the live proof.
- `docs/phoenix-value-proof.md` has no unfilled public TODO section.
- Devpost text does not include internal checklist or script sections.

## Recommended Submission Category

Selected track:

- Arize

Project title:

- Market Fit Trace Agent

Short description:

> A Gemini-powered, Phoenix-instrumented agent that audits prediction-market thesis matches, catches weak proxies, records human verdicts in a Ledger MCP, and improves after inspecting failed traces.
