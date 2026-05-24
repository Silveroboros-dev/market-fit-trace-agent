# Adjudication Log

Use this file for hard examples, label disagreements, and corrections after review.

Template:

```text
## eval_001

- issue:
- options considered:
- final decision:
- rationale:
- adjudicated by:
- date:
```

After the eval version is locked, do not silently change labels. Record the reason here and create a patch version if needed.

## Seed Intake - 2026-05-03

- issue: Workbook contained six discussed rows, but Kevin Kelly's permanent uncertainty thesis is too broad and philosophical for the first seed batch.
- options considered: include as no-clean overbroad; skip until adversarial expansion.
- final decision: skip for the first five built examples.
- rationale: first seed batch already has several no-clean/overbroad examples; Kevin adds little market-matching tension.
- adjudicated by: Codex with user agreement in thread.
- date: 2026-05-03

## eval_005

- issue: Gemini source signal mentions Gemini 3.2/3.5, while candidate markets resolve on specific versions.
- options considered: label Gemini 3.2 market direct; change thesis to Gemini 3.5; label best expression indirect.
- final decision: label as `indirect` with `wrong_market` and `resolution_risk` tags.
- rationale: the 3.2 market is a plausible best available expression, but if Google releases 3.5 and not 3.2, the broad thesis may be directionally right while the 3.2 market resolves No.
- adjudicated by: user and Codex in thread.
- date: 2026-05-03

## eval_007

- issue: User proposed Anthropic IPO Closing Market Cap / No IPO by June 30 as a direct market for a valuation-hype post.
- options considered: use No IPO by June 30 as direct; use Anthropic $500B+ valuation as direct; treat IPO timing as weak proxy.
- final decision: use Anthropic $500B+ valuation in 2026 as direct.
- rationale: the source text explicitly claims Anthropic valuation above $500B; it does not directly predict no IPO or IPO by June 30.
- adjudicated by: Codex in thread.
- date: 2026-05-03

## eval_009

- issue: Same Anthropic valuation post can produce a different user thesis: valuation hype implies near-term IPO momentum.
- options considered: drop as duplicate; add as weak proxy with duplicate tag.
- final decision: include as weak proxy with `duplicate` and `wrong_market` tags.
- rationale: it tests the system's ability to distinguish valuation from IPO timing and to notice similarity to eval_007.
- adjudicated by: Codex in thread.
- date: 2026-05-03
