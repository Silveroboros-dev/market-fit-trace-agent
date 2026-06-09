"""Build a human-reviewable policy change proposal from a policy review batch.

This script reads evals/policy_review_batches/<date>/summary.json and writes a
proposal artifact. It does not edit prompts, policy code, strict goldens, or
expected output fixtures.

Usage:
    python scripts/build_policy_change_proposal.py
    python scripts/build_policy_change_proposal.py --date 2026-06-08
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_INPUT_DIR = Path("evals/policy_review_batches")
SCHEMA_VERSION = "policy_change_proposal_v0"
PROPOSAL_FILENAME = "POLICY_CHANGE_PROPOSAL.md"
REVIEW_OPTIONS = (
    "approve_prompt_only_patch",
    "approve_deterministic_guard",
    "keep_candidate_only",
    "disregard",
)

PROMPT_GUARDS = {
    "event_stage_mismatch": (
        "Before assigning `indirect` or stronger, verify that the market resolves "
        "the same event stage as the thesis. Preparation, confidential filing, "
        "roadshow, pricing, IPO completion, and post-IPO valuation are different "
        "stages. If stage differs materially, downgrade to `weak_proxy` or "
        "`no_clean_expression`."
    ),
    "horizon_mismatch": (
        "Check whether the thesis horizon overlaps the market close date and "
        "resolution window. If the market resolves a materially different year, "
        "quarter, or milestone window, do not treat entity/topic overlap as enough "
        "for `indirect`."
    ),
    "metric_mismatch": (
        "Check whether the market resolution metric is the thesis metric. Revenue, "
        "users, margin, benchmark scores, valuation, release timing, and share "
        "price are separate metrics; evidence for one is not resolution of another."
    ),
    "inverse_framing": (
        "If a binary market is framed opposite to the thesis, explicitly identify "
        "which outcome supports the thesis before assigning fit. Inverse framing "
        "is review guidance, not automatic direct evidence."
    ),
    "composite_thesis": (
        "For compound claims, list every material condition and check whether the "
        "market resolves all of them. If it resolves only one component, classify "
        "as partial coverage and avoid strong fit labels."
    ),
    "entity_mismatch": (
        "Verify entity, product family, and version. Same ecosystem or supplier "
        "relationship is not enough when the market resolves a different company, "
        "model, product version, or venue."
    ),
    "causal_mechanism": (
        "Identify whether the market resolves the thesis outcome or merely one "
        "input in a causal chain. Hardware, funding, regulation, rates, and energy "
        "costs require an explicit bridge before `indirect`."
    ),
}

DETERMINISTIC_GUARDS = {
    "event_stage_mismatch": {
        "name": "event_stage_alignment_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Detect mismatched IPO/startup stages in claim and resolution rules. "
            "If the claim is about filing/preparation and the market resolves "
            "completion or valuation, cap fit at `weak_proxy` or "
            "`no_clean_expression` depending on horizon."
        ),
    },
    "horizon_mismatch": {
        "name": "horizon_alignment_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Extract obvious years, quarters, and deadline phrases from claim and "
            "resolution text. If they do not overlap, cap fit below `indirect` "
            "unless the market tests a named intermediate milestone."
        ),
    },
    "metric_mismatch": {
        "name": "resolution_metric_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Identify metric families such as valuation, revenue, users, margin, "
            "release timing, benchmark, and share price. Prevent raw term overlap "
            "from producing `indirect` when metric families differ."
        ),
    },
    "inverse_framing": {
        "name": "outcome_polarity_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "When market wording is inverse to the thesis, require a supporting "
            "outcome and polarity explanation. Do not upgrade fit only because the "
            "opposite outcome could be useful."
        ),
    },
    "composite_thesis": {
        "name": "compound_claim_coverage_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Detect material conjunctions in the claim. If a market resolves only "
            "one component, label the case as partial coverage and route to review "
            "unless local policy has a specific exception."
        ),
    },
    "entity_mismatch": {
        "name": "entity_version_alignment_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Compare named companies, model families, and versions between claim "
            "and market. Cap fit when only ecosystem adjacency is present."
        ),
    },
    "causal_mechanism": {
        "name": "causal_bridge_guard",
        "target": "app/policy/fit.py",
        "behavior": (
            "Treat infrastructure, funding, regulation, rates, and cost inputs as "
            "weak-proxy candidates unless the resolution rule directly tests the "
            "downstream thesis outcome."
        ),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Turn a candidate-only policy review batch into a human-reviewable "
            "prompt and deterministic-policy proposal."
        )
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument(
        "--date",
        default=None,
        help="Policy review batch date. Defaults to latest folder with summary.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_policy_change_proposal(
            input_dir=Path(args.input_dir),
            date=args.date,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_policy_change_proposal(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    date: str | None = None,
) -> dict[str, Any]:
    batch_date = date or _latest_batch_date(input_dir)
    batch_dir = input_dir / batch_date
    summary_path = batch_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Policy review summary not found: {summary_path}")

    summary = _read_json(summary_path)
    proposal = _build_proposal(summary=summary, batch_date=batch_date)
    proposal_path = batch_dir / PROPOSAL_FILENAME
    proposal_path.write_text(_render_markdown(proposal), encoding="utf-8")

    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "candidate_date": batch_date,
        "candidate_count": proposal["candidate_count"],
        "family_count": proposal["family_count"],
        "proposal_path": str(proposal_path),
        "writes_prompt_code": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
    }


def _latest_batch_date(input_dir: Path) -> str:
    if not input_dir.exists():
        raise FileNotFoundError(f"Policy review batch directory not found: {input_dir}")
    dates = [
        path.name
        for path in input_dir.iterdir()
        if path.is_dir() and (path / "summary.json").exists()
    ]
    if not dates:
        raise FileNotFoundError(f"No policy review summaries found in {input_dir}")
    return sorted(dates)[-1]


def _build_proposal(*, summary: dict[str, Any], batch_date: str) -> dict[str, Any]:
    families = summary.get("families") or {}
    family_proposals = [
        _family_proposal(family, data)
        for family, data in sorted(
            families.items(),
            key=lambda item: (
                -int(item[1].get("deterministic_mismatch_count", 0)),
                -int(item[1].get("candidate_count", 0)),
                item[0],
            ),
        )
    ]
    prompt_only_families = [
        item["family"]
        for item in family_proposals
        if item["recommended_first_action"] == "prompt_only_patch"
    ]
    guard_families = [
        item["family"]
        for item in family_proposals
        if item["recommended_first_action"] == "deterministic_guard_review"
    ]
    positive_signal_families = [
        {
            "family": item["family"],
            "candidate_count": item["candidate_count"],
            "deterministic_mismatch_count": item["deterministic_mismatch_count"],
            "interpretation": (
                "Deterministic policy already handled this family in the stress "
                "batch. A prompt-only guard may still reduce Gemini advisory noise."
            ),
        }
        for item in family_proposals
        if item["deterministic_mismatch_count"] == 0
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "candidate_date": batch_date,
        "source_summary": summary.get("source_dir"),
        "candidate_count": int(summary.get("candidate_count", 0)),
        "family_count": len(family_proposals),
        "writes_prompt_code": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
        "review_options": list(REVIEW_OPTIONS),
        "recommended_sequence": [
            "Review this proposal as a human-owned patch plan.",
            "Approve prompt-only guardrails first, because they are lower risk.",
            "Use deterministic guards only for families with repeated policy misses.",
            "Rerun stress and full tests before any promotion to strict goldens.",
        ],
        "prompt_only_families": prompt_only_families,
        "deterministic_guard_families": guard_families,
        "positive_signal_families": positive_signal_families,
        "families": family_proposals,
        "test_plan": [
            "make test",
            "make run-stress-40",
            "make policy-review-batch",
            "python scripts/build_policy_change_proposal.py",
            "Compare new stress_summary.json against the committed baseline.",
            "Promote only reviewed cases; do not mutate expected_outputs.jsonl here.",
        ],
    }


def _family_proposal(family: str, data: dict[str, Any]) -> dict[str, Any]:
    deterministic_mismatches = int(data.get("deterministic_mismatch_count", 0))
    candidate_count = int(data.get("candidate_count", 0))
    recommended_first_action = (
        "deterministic_guard_review"
        if deterministic_mismatches >= 2
        else "prompt_only_patch"
    )
    guard = DETERMINISTIC_GUARDS.get(
        family,
        {
            "name": f"{family}_guard_candidate",
            "target": "app/policy/fit.py",
            "behavior": "Review repeated failures and decide whether a guard is needed.",
        },
    )
    return {
        "family": family,
        "candidate_count": candidate_count,
        "deterministic_mismatch_count": deterministic_mismatches,
        "recommended_first_action": recommended_first_action,
        "prompt_target": "app/prompts.py",
        "prompt_guardrail": PROMPT_GUARDS.get(
            family,
            "Ask Gemini to verify stage, metric, horizon, entity, and outcome polarity "
            "before assigning strong fit classes.",
        ),
        "deterministic_guard": guard,
        "top_patterns": list(data.get("patterns") or []),
        "cases": list(data.get("candidates") or []),
    }


def _render_markdown(proposal: dict[str, Any]) -> str:
    lines = [
        "# Policy Change Proposal",
        "",
        f"Generated at UTC: `{proposal['generated_at_utc']}`",
        f"Candidate date: `{proposal['candidate_date']}`",
        f"Source summary: `{proposal['source_summary']}`",
        "",
        "## Scope",
        "",
        (
            "This is an autonomous proposal artifact generated from clustered "
            "candidate failures. It proposes prompt and deterministic-policy changes "
            "for human review, but applies none of them."
        ),
        "",
        f"- Candidate failures reviewed: `{proposal['candidate_count']}`",
        f"- Failure families: `{proposal['family_count']}`",
        f"- Writes prompt code: `{proposal['writes_prompt_code']}`",
        f"- Writes policy code: `{proposal['writes_policy_code']}`",
        f"- Writes strict expected labels: `{proposal['writes_strict_expected_labels']}`",
        "- Review options: "
        + ", ".join(f"`{option}`" for option in proposal["review_options"]),
        "",
        "## Recommended Sequence",
        "",
    ]
    lines.extend(
        f"{index}. {step}"
        for index, step in enumerate(proposal["recommended_sequence"], 1)
    )
    lines.extend(
        [
            "",
            "## Priority Families",
            "",
            "| Family | Candidates | Policy misses | First action |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for family in proposal["families"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{family['family']}`",
                    str(family["candidate_count"]),
                    str(family["deterministic_mismatch_count"]),
                    f"`{family['recommended_first_action']}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Positive Signals",
            "",
        ]
    )
    if proposal["positive_signal_families"]:
        lines.extend(
            [
                (
                    "These families produced Gemini advisory mismatches, but the "
                    "deterministic gate matched the synthetic expected labels. "
                    "They are prompt-noise candidates, not evidence that final "
                    "policy is broken."
                ),
                "",
                "| Family | Candidates | Policy misses | Interpretation |",
                "| --- | ---: | ---: | --- |",
            ]
        )
        for item in proposal["positive_signal_families"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{item['family']}`",
                        str(item["candidate_count"]),
                        str(item["deterministic_mismatch_count"]),
                        _md_escape(item["interpretation"]),
                    ]
                )
                + " |"
            )
    else:
        lines.append(
            "No family had zero deterministic misses in this batch. Treat every "
            "family as needing human review before patching."
        )

    lines.extend(
        [
            "",
            "## Prompt Proposal",
            "",
            "Target file for human-approved patch: `app/prompts.py`",
            "",
            (
                "Add an explicit market-fit checklist before Gemini assigns "
                "`direct`, `indirect`, `weak_proxy`, or `no_clean_expression`."
            ),
            "",
        ]
    )
    for family in proposal["families"]:
        lines.extend(
            [
                f"### `{family['family']}`",
                "",
                family["prompt_guardrail"],
                "",
            ]
        )

    lines.extend(
        [
            "## Deterministic Guard Candidates",
            "",
            (
                "These are review candidates for `app/policy/fit.py`. They are not "
                "implemented by this script. Prefer prompt-only patches for families "
                "where deterministic policy already matched most synthetic labels."
            ),
            "",
            "| Family | Guard candidate | Target | Proposed behavior |",
            "| --- | --- | --- | --- |",
        ]
    )
    for family in proposal["families"]:
        guard = family["deterministic_guard"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{family['family']}`",
                    f"`{guard['name']}`",
                    f"`{guard['target']}`",
                    _md_escape(guard["behavior"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Evidence Links",
            "",
        ]
    )
    for family in proposal["families"]:
        lines.extend(_render_family_evidence(family))

    lines.extend(
        [
            "## Test Plan",
            "",
        ]
    )
    lines.extend(
        f"- `{step}`"
        if step.startswith("make") or step.startswith("python")
        else f"- {step}"
        for step in proposal["test_plan"]
    )
    lines.extend(
        [
            "",
            "## Human Review Decision",
            "",
            "- `approve_prompt_only_patch`: implement only the prompt guardrail text.",
            "- `approve_deterministic_guard`: implement a scoped deterministic "
            "guard and targeted tests.",
            "- `keep_candidate_only`: keep the evidence but do not change product behavior.",
            "- `disregard`: reject the family or individual cases as synthetic noise.",
            "",
            (
                "This proposal does not apply changes. A reviewer must decide which "
                "families become patches, which become candidate-only memory, and "
                "which get disregarded."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _render_family_evidence(family: dict[str, Any]) -> list[str]:
    lines = [
        f"### `{family['family']}`",
        "",
        "| Case | Expected | Gemini | Deterministic | Trace |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in family["cases"]:
        trace = (
            f"[trace]({case['phoenix_trace_url']})"
            if case.get("phoenix_trace_url")
            else "n/a"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{case.get('case_id', 'missing')}`",
                    f"`{case.get('expected_fit_class', 'missing')}`",
                    f"`{case.get('gemini_fit_class', 'missing')}`",
                    f"`{case.get('deterministic_fit_class', 'missing')}`",
                    trace,
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
