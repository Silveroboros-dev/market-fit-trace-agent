# Demo Golden Trio

Status: recommended demo selection. The Arize correction loop now lives in the
separate `evals/trace_repair_v1` transition pack, not in the strict golden pack.

## Recommendation

Use this demo set:

| Role | Case | Fit class | Why it belongs in the demo |
|---|---|---|---|
| Arize correction loop | `trace_repair_tpu_frontier_gap_001` | `indirect -> weak_proxy` | Best main demo case. It shows the required transition: first run overstates a tempting market, Phoenix MCP retrieves the failed trace/eval context, and the deterministic repair gate downgrades the rerun. |
| Strict weak-proxy correctness | `eval_008` | `weak_proxy` | Source-backed strict golden proving that the corrected TPU / Gemini weak-proxy behavior is stable on first deterministic replay. |
| Clean positive fit | `eval_007` | `direct` | Shows the app is not only a rejection engine. The Anthropic valuation thesis cleanly maps to the Anthropic $500B valuation market, while IPO timing markets are rejected as different claims. |
| Refusal / no-clean fit | `eval_003` | `no_clean_expression` | Shows disciplined refusal. AI research-agent capability is not the same as an IMO benchmark market, so the app explains why no clean current market expression exists. |

This trio is better for the main video than trying to cover every class. It
shows the three user-facing outcomes that matter most:

```text
clean fit -> safe recommendation
weak proxy -> tempting market downgraded
no clean expression -> no false precision
```

The fourth class, `indirect`, can be mentioned as part of the full four-class
taxonomy and shown in eval coverage, but it does not need a dedicated demo slot.

## Case Details

### 1. `trace_repair_tpu_frontier_gap_001`: Phoenix Trace Repair

Use as the primary Arize-track proof.

- Thesis: Google TPU progress means Gemini closes the frontier-model gap in
  2026.
- Tempting market: `pm-gemini-arena-2026`
- First run: `indirect`, with `false_strong_recommendation=true`,
  `causal_mechanism_mismatch=true`, and `trace_repair_candidate=true`.
- Required inspection: Phoenix MCP, not local fallback.
- Corrected run: `weak_proxy`, with `trace_repair_gate_applied=true`.
- Demo line: "This market is related, but it resolves on Chatbot Arena rank, not
  TPU hardware causality or a durable frontier-gap closure."
- Why it matters: this is the formal proof that Phoenix is not passive logging.
  It supplies the trace/eval context that activates the deterministic repair
  gate.

### 2. `eval_008`: Google TPU / Gemini Strict Weak Proxy

Use as the source-backed correctness check after the correction-loop demo.

- Thesis: Google's TPU 8t/8i performance claims could help Google close the
  frontier AI model gap by the end of June 2026.
- Tempting market: `polymarket_best_ai_model_google_end_june_2026`
- Correct class: `weak_proxy` on first deterministic replay.
- Demo line: "The strict golden already knows the corrected answer; it is not
  supposed to fail first."
- Trace evidence: `evals/market_fit_v1/phoenix_experiment_result.json` contains
  a passing row and Phoenix trace URL for `eval_008`.

### 3. `eval_007`: Anthropic $500B Valuation Direct Fit

Use as the clean positive contrast.

- Thesis: Anthropic will achieve or has achieved a valuation above $500B in
  2026, based on private-market bids and reported revenue acceleration.
- Recommended market: `polymarket_anthropic_500b_valuation_2026`
- Correct class: `direct`
- Demo line: "Here the claim and market resolve on the same thing: Anthropic's
  valuation confirmation by the end of 2026."
- Why it matters: judges see that the system can recommend a clean market when
  one exists, while still rejecting IPO timing as a different question.

### 4. `eval_003`: AI Research Agents No-Clean Expression

Use as the disciplined refusal case.

- Thesis: AI agents are approaching the ability to independently reconstruct
  complex academic papers from methods and data, suggesting research-agent
  products may arrive soon.
- Tempting adjacent market: `polymarket_ai_wins_imo_gold_2026`
- Correct class: `no_clean_expression`
- Demo line: "An IMO benchmark is an AI capability signal, but it does not
  resolve whether general-purpose AI research agents are released."
- Why it matters: this prevents the product from looking like generic market
  search. It shows the trust boundary: no clean market means no clean
  recommendation.

## Demo Order

For a three-minute video:

1. Start with `trace_repair_tpu_frontier_gap_001`.
   Show the full Phoenix story: first run, eval warning, Phoenix trace, MCP
   inspection, deterministic gate, second-run downgrade to `weak_proxy`.
2. Flash `eval_008`.
   Show that the source-backed strict golden now passes on first replay.
3. Flash `eval_007`.
   Show that clean direct fits are allowed when the market actually expresses
   the thesis.
4. Flash `eval_003`.
   Show that the app refuses tempting benchmark proxies when no clean market
   exists.
5. Optional, if there is time: show the OpenAI IPO filing live candidate.
   Start `make api-live`, paste the source text, and show that PolyData retrieves
   real OpenAI IPO markets while the review note preserves the key boundary:
   IPO filing/preparation is not the same event stage as IPO completion.

Use this closing line:

> The product is not trying to find any related market. It is deciding whether
> the market actually expresses the thesis.

## Optional Live Candidate: OpenAI IPO Filing vs IPO Completion

Use this only after the main Phoenix repair proof is clear. It demonstrates the
candidate-governance path, not a strict golden that already belongs in CI.

- Candidate packet:
  `evals/retrieval_candidates/2026-06-06/ui-20260606-openai-is-preparing-to-file-confidentially-df1370c1`
- Source text: OpenAI is preparing to file confidentially for an initial public
  offering in the coming weeks.
- Retrieval mode: PolyData live snapshot
  `polydata_polymarket_2026-06-06 09:00:00+00:00`
- Human review status: `promote`, meaning eligible for later frozen strict
  promotion, not canonical truth yet.
- Current policy class: `indirect`
- Demo line: "PolyData found real OpenAI IPO markets, but the harness separates
  filing/preparation evidence from markets that resolve on completed IPO
  timing."

Markets to show:

| Market | Demo role |
|---|---|
| `2314379` - Will OpenAI IPO by September 30 2026? | Best visual adjacent market: relevant, but still IPO completion rather than filing/preparation. |
| `656312` - Will OpenAI IPO by December 31 2026? | Broader adjacent market the live run recommended. Useful for discussing best-market adjudication before strict promotion. |
| `2321571` - Will OpenAI file for an IPO by June 5, 2026? | Stage-aligned market, but stale/wrong horizon for the source. Shows why resolution target and horizon both matter. |
| OpenAI valuation threshold markets | Wrong metric; reject as valuation rather than filing or IPO completion. |

Promotion blockers before making this strict:

- attach source provenance;
- freeze the normalized thesis instead of relying on fallback extraction;
- adjudicate whether `2314379` or `656312` should be the expected best adjacent
  market;
- add the promoted fixture through the normal intake process rather than
  editing `expected_outputs.jsonl` directly.

Arize/Phoenix value for this example is governance, not repair: the live run is
traceable, the candidate packet is reviewable, and human review decides whether
the case is worth turning into a deterministic golden.

## Alternates

- Use `eval_006` instead of `eval_007` if you want a SpaceX / IPO example rather
  than another AI-lab example.
- Use `eval_009` instead of `eval_007` if you want to show same-entity nuance:
  Anthropic valuation can be direct for a valuation thesis but weak proxy for an
  IPO-momentum thesis.
- Use `eval_005` only if the video needs an explicit `indirect` example. It is a
  good eval case, but less visually important than the three user-facing
  outcomes above.

## Live-Promoted Hormuz Cases

The reviewed Hormuz PolyData packets now live in
`evals/market_fit_v4_live_promoted` as strict frozen goldens:

- `demo-hormuz-candidate`: `indirect`, best market `2155023`;
- `live-iran-sanctions-relief-package`: `weak_proxy`, no clean best market,
  with `2155023` as a tempting adjacent market.

Use these as secondary evidence for the live-retrieval promotion story. Keep the
main 3-minute Arize proof focused on the stable v1 weak-proxy correction loop
unless there is enough time to show the governance path.

For demo wording:

```text
The stable proof uses promoted frozen goldens. Live PolyData retrieval creates
candidate evidence; reviewed cases can become strict goldens after rules and
expected labels are frozen.
```
