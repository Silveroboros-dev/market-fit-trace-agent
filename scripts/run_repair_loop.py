"""Bounded repair-discovery loop over committed Stress-40 evidence (offline).

This script runs a deterministic, offline three-stage loop:

1. explorer:    rank candidate failure families by dangerousness, stability,
                demo value, and testability.
2. implementer: draft a minimal prompt/guard patch *plan* for the top-ranked
                candidate. It never applies the plan.
3. verifier:    apply shipping gates to the drafted plan and emit a verdict.
                The loop is allowed to emit NO-GO.

It runs no new model calls (no Gemini), runs no new Stress-40 loops, and never
writes prompts, policy code, strict goldens, or expected-output fixtures. Every
input is a committed artifact; every output lives under ``evals/repair_loop/``.

The verifier is intentionally conservative. A candidate guard ships (GO) only
when it reduces a *real* danger (deterministic direct false positives or
overclaims) AND clears every safety invariant. A guard that merely nudges a
deterministic class toward a debatable synthetic stress label, without reducing
direct false positives, is marked candidate-only / NO-GO for shipping.

Usage:
    python scripts/run_repair_loop.py
    python scripts/run_repair_loop.py --check
"""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/run_repair_loop.py` to import sibling scripts directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_policy_change_proposal import (  # noqa: E402
    DETERMINISTIC_GUARDS,
    PROMPT_GUARDS,
)
from scripts.build_stress_appendix import (  # noqa: E402
    STRENGTH,
    classify_deterministic,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "evals" / "stress_test_v1" / "repeated_prompt_patch_runs"
DEFAULT_RUN_FILES = tuple(
    RUNS_DIR / f"post_patch_run_{index}_results.jsonl" for index in (1, 2, 3, 4)
)
APPENDIX_JSON = REPO_ROOT / "evals" / "stress_test_v1" / "stress_40_appendix.json"
GOVERNANCE_EXAMPLES = (
    REPO_ROOT / "evals" / "market_fit_governance_50" / "governance_examples.jsonl"
)
FAILURE_CANDIDATES_DIR = REPO_ROOT / "evals" / "failure_candidates"
POLICY_REVIEW_DIR = REPO_ROOT / "evals" / "policy_review_batches"

OUTPUT_DIR = REPO_ROOT / "evals" / "repair_loop"
OUTPUT_JSON = OUTPUT_DIR / "loop_state.json"
OUTPUT_MARKDOWN = OUTPUT_DIR / "LOOP_STATE.md"
PROPOSAL_MARKDOWN = OUTPUT_DIR / "TOP_CANDIDATE_PROPOSAL.md"

SCHEMA_VERSION = "repair_loop_v0"

# The deterministic gate is the classifier of record. Gemini is advisory only.
# These paths are read-only inputs; the loop must never write any of them.
PROTECTED_PATHS = (
    "app/prompts.py",
    "app/policy/fit.py",
    "evals/market_fit_v1/expected_outputs.jsonl",
    "evals/market_fit_v2/expected_outputs.jsonl",
    "evals/market_fit_v4_live_promoted/expected_outputs.jsonl",
)

# The TPU Phoenix MCP trace-repair remains the core improvement proof. Governance
# 50 supplies review-memory guardrails: the "filing/preparation vs IPO completion"
# thesis is golden-labeled ``indirect`` here (gov_001) and across the hero cluster.
# A guard that downgrades that pattern below ``indirect`` regresses the governance
# support surface, so it cannot ship from this loop.
HERO_CLUSTER = "ai_startup_ipo_stage_mismatch"
GOV_001_PREFIX = "gov_001"
# The event-stage IPO family is the stress mirror of the governance hero cluster.
HERO_STRESS_FAMILY = "event_stage_mismatch"

# Explorer ranking weights. Dangerousness dominates; demo value, stability, and
# testability break ties. Direct false positives carry a large dangerousness
# multiplier so any real overclaim outranks a review-band over-call.
DANGER_DIRECT_FP_WEIGHT = 100
RANKING_WEIGHTS = {
    "dangerousness": 1.0,
    "demo_value": 0.5,
    "stability": 0.25,
    "testability": 0.25,
}
HERO_DEMO_BONUS = 2

VERDICT_GO = "go"
VERDICT_CANDIDATE_ONLY = "candidate_only"
VERDICT_NO_GO = "no_go"


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_runs(
    run_files: tuple[Path, ...] | list[Path] = DEFAULT_RUN_FILES,
) -> list[tuple[str, list[dict[str, Any]]]]:
    return [
        (f"run_{index}", load_rows(Path(path)))
        for index, path in enumerate(run_files, 1)
    ]


def run_invariant_map(
    runs: list[tuple[str, list[dict[str, Any]]]],
) -> dict[str, bool]:
    """Per-case: is the deterministic class identical across every run."""
    by_case: dict[str, set[str]] = {}
    for _label, rows in runs:
        for row in rows:
            by_case.setdefault(row["case_id"], set()).add(row["deterministic_fit_class"])
    return {case: len(classes) == 1 for case, classes in by_case.items()}


def load_governance(path: Path = GOVERNANCE_EXAMPLES) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    return load_rows(Path(path))


def load_appendix(path: Path = APPENDIX_JSON) -> dict[str, Any]:
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_policy_directions(
    policy_review_dir: Path = POLICY_REVIEW_DIR,
) -> dict[str, str]:
    """Best-effort: pull family policy directions from the latest review batch."""
    if not Path(policy_review_dir).exists():
        return {}
    dated = sorted(
        path
        for path in Path(policy_review_dir).iterdir()
        if path.is_dir() and (path / "summary.json").exists()
    )
    if not dated:
        return {}
    summary = json.loads((dated[-1] / "summary.json").read_text(encoding="utf-8"))
    return {
        family: data.get("policy_direction", "")
        for family, data in (summary.get("families") or {}).items()
    }


def count_failure_candidate_dirs(
    failure_dir: Path = FAILURE_CANDIDATES_DIR,
) -> int:
    if not Path(failure_dir).exists():
        return 0
    return sum(
        1
        for date_dir in Path(failure_dir).iterdir()
        if date_dir.is_dir()
        for packet in date_dir.iterdir()
        if packet.is_dir() and (packet / "failure_signal.json").exists()
    )


# --------------------------------------------------------------------------- #
# Stage 1 — explorer
# --------------------------------------------------------------------------- #
def _is_strong_over(row: dict[str, Any]) -> bool:
    return (
        classify_deterministic(
            row["expected_fit_class"], row["deterministic_fit_class"]
        )
        == "strong_over_weak_no"
    )


def _is_direct_false_positive(row: dict[str, Any]) -> bool:
    return (
        classify_deterministic(
            row["expected_fit_class"], row["deterministic_fit_class"]
        )
        == "direct_false_positive"
    )


def rank_candidates(
    rows: list[dict[str, Any]],
    invariant: dict[str, bool],
) -> list[dict[str, Any]]:
    """Rank candidate failure families for repair.

    Each candidate family is scored on four axes:
    - dangerousness: direct false positives (heavily weighted) plus review-band
      over-calls. Direct false positives are the only shipping-grade danger.
    - stability: fraction of the family's review candidates whose deterministic
      class is identical across every committed run (reproducible to test).
    - demo_value: number of review candidates plus a bonus when the family
      mirrors the Phoenix/Governance-50 hero cluster.
    - testability: fraction of review candidates that carry a Phoenix trace and
      are run-invariant, i.e. can be pinned in a deterministic offline test.
    """
    families: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        families.setdefault(row.get("mismatch_family") or "unclassified", []).append(row)

    candidates: list[dict[str, Any]] = []
    for family, family_rows in families.items():
        review_members = [row for row in family_rows if _is_strong_over(row)]
        if not review_members:
            continue
        direct_fp = sum(1 for row in family_rows if _is_direct_false_positive(row))
        strong_over = len(review_members)

        stable_members = [
            row for row in review_members if invariant.get(row["case_id"], False)
        ]
        stability = round(len(stable_members) / strong_over, 4)
        testability = round(
            len(
                [
                    row
                    for row in review_members
                    if invariant.get(row["case_id"], False) and row.get("phoenix_trace_url")
                ]
            )
            / strong_over,
            4,
        )

        hero_overlap = family == HERO_STRESS_FAMILY
        dangerousness = DANGER_DIRECT_FP_WEIGHT * direct_fp + strong_over
        demo_value = strong_over + (HERO_DEMO_BONUS if hero_overlap else 0)
        score = round(
            RANKING_WEIGHTS["dangerousness"] * dangerousness
            + RANKING_WEIGHTS["demo_value"] * demo_value
            + RANKING_WEIGHTS["stability"] * stability
            + RANKING_WEIGHTS["testability"] * testability,
            4,
        )
        candidates.append(
            {
                "family": family,
                "review_candidate_count": strong_over,
                "direct_false_positives": direct_fp,
                "hero_cluster_overlap": hero_overlap,
                "dangerousness": dangerousness,
                "demo_value": demo_value,
                "stability": stability,
                "testability": testability,
                "score": score,
                "members": sorted(row["case_id"] for row in review_members),
            }
        )

    ranked = sorted(
        candidates,
        key=lambda item: (
            -item["score"],
            -item["dangerousness"],
            -item["demo_value"],
            item["family"],
        ),
    )
    for rank, candidate in enumerate(ranked, 1):
        candidate["rank"] = rank
    return ranked


# --------------------------------------------------------------------------- #
# Stage 2 — implementer (drafts a plan; never applies it)
# --------------------------------------------------------------------------- #
def draft_patch_plan(
    top: dict[str, Any],
    rows: list[dict[str, Any]],
    policy_directions: dict[str, str],
) -> dict[str, Any]:
    """Draft a minimal, unapplied prompt/guard patch plan for the top family.

    The deterministic guard is modeled as a declarative relabel spec. A real
    text-pattern guard keys on stage tokens shared by every case in the family,
    so the faithful offline proxy for "what the guard would catch" is every
    family row that currently resolves ``indirect``. The plan is data only;
    nothing here is applied.
    """
    family = top["family"]
    affected = sorted(
        row["case_id"]
        for row in rows
        if row.get("mismatch_family") == family
        and row["deterministic_fit_class"] == "indirect"
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
        "candidate_family": family,
        "applied": False,
        "writes_prompts": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
        "prompt_target": "app/prompts.py",
        "prompt_guardrail": PROMPT_GUARDS.get(
            family,
            "Ask Gemini to verify stage, metric, horizon, entity, and outcome "
            "polarity before assigning strong fit classes.",
        ),
        "deterministic_guard": guard,
        "policy_direction": policy_directions.get(family, ""),
        "predicted_relabel": {
            "family": family,
            "from_class": "indirect",
            "to_class": "weak_proxy",
            "scope": (
                "Cap event-stage IPO mismatches (filing, S-1, board approval, "
                "roadshow, pricing) below 'indirect' when the market resolves "
                "completion or post-IPO valuation."
            ),
        },
        "predicted_affected_case_ids": affected,
    }


def _apply_relabel(
    row: dict[str, Any], plan: dict[str, Any]
) -> str:
    """Return the deterministic class this row *would* take under the plan."""
    relabel = plan["predicted_relabel"]
    if (
        row["case_id"] in plan["predicted_affected_case_ids"]
        and row["deterministic_fit_class"] == relabel["from_class"]
    ):
        return relabel["to_class"]
    return row["deterministic_fit_class"]


# --------------------------------------------------------------------------- #
# Stage 3 — verifier gates
# --------------------------------------------------------------------------- #
def gate_direct_false_positive_reduction(
    rows: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """Does the guard reduce deterministic direct false positives?"""
    before = sum(1 for row in rows if _is_direct_false_positive(row))
    after = sum(
        1
        for row in rows
        if classify_deterministic(row["expected_fit_class"], _apply_relabel(row, plan))
        == "direct_false_positive"
    )
    reduction = before - after
    return {
        "gate": "direct_false_positive_reduction",
        "status": "pass" if reduction > 0 else "fail",
        "before": before,
        "after": after,
        "reduction": reduction,
        "detail": (
            f"Deterministic direct false positives: {before} -> {after} "
            f"(reduction {reduction}). The guard reduces no direct false positives; "
            "there are none to reduce."
            if reduction <= 0
            else f"Guard reduces {reduction} deterministic direct false positive(s)."
        ),
    }


def gate_twin_safety(
    rows: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """The guard must not flip a correctly classified twin.

    Adversarial cases come in twins (``X_vs_Y``). Within the targeted family,
    some ``indirect`` rows are *correct* (expected == indirect): the "good
    twins". A text-pattern guard cannot tell a good twin from a bad twin, so a
    blanket downgrade damages the good ones.
    """
    by_case = {row["case_id"]: row for row in rows}
    collateral = []
    for case_id in plan["predicted_affected_case_ids"]:
        row = by_case.get(case_id)
        if row is None:
            continue
        before = row["deterministic_fit_class"]
        after = _apply_relabel(row, plan)
        if before == row["expected_fit_class"] and after != before:
            collateral.append(
                {
                    "case_id": case_id,
                    "expected_fit_class": row["expected_fit_class"],
                    "before": before,
                    "after": after,
                }
            )
    return {
        "gate": "twin_safety",
        "status": "pass" if not collateral else "fail",
        "good_twins_damaged": collateral,
        "detail": (
            "No correctly classified twin is changed by the guard."
            if not collateral
            else (
                f"{len(collateral)} correctly classified 'good twin' case(s) would be "
                "downgraded as collateral; the guard cannot separate them from the bad "
                "twins by claim text."
            )
        ),
    }


def gate_tpu_hero_invariant(
    rows: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    plan: dict[str, Any],
) -> dict[str, Any]:
    """The TPU demo hero must be untouched by the guard."""
    tpu_governance = sorted(
        row.get("governance_id") or row.get("case_id")
        for row in governance
        if "tpu" in (row.get("case_id") or "").lower()
        or "tpu" in (row.get("embedding_text") or "").lower()
    )
    tpu_stress = sorted(
        row["case_id"] for row in rows if "tpu" in row["case_id"].lower()
    )
    touched = sorted(
        case_id
        for case_id in plan["predicted_affected_case_ids"]
        if "tpu" in case_id.lower()
    )
    return {
        "gate": "tpu_hero_invariant",
        "status": "pass" if not touched else "fail",
        "tpu_governance_anchors": tpu_governance,
        "tpu_stress_cases": tpu_stress,
        "touched_tpu_cases": touched,
        "detail": (
            "The guard scope is IPO event-stage; it touches no TPU governance "
            "anchor or TPU stress case, so the TPU hero is preserved."
            if not touched
            else "The guard would alter TPU hero cases."
        ),
    }


def gate_gov_001_invariant(
    governance: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """The gov_001 hero golden mandates ``indirect`` for filing-vs-completion.

    The guard downgrades exactly that pattern (``event_stage_mismatch``,
    ``indirect`` -> weaker), so shipping it regresses gov_001 and the hero
    cluster's ``indirect`` goldens.
    """
    relabel = plan["predicted_relabel"]
    gov_001 = next(
        (
            row
            for row in governance
            if (row.get("governance_id") or "").startswith(GOV_001_PREFIX)
        ),
        None,
    )
    hero_indirect = sorted(
        row.get("governance_id") or row.get("case_id")
        for row in governance
        if row.get("hero_cluster") == HERO_CLUSTER and row.get("fit_class") == "indirect"
    )
    targets_hero_pattern = (
        plan["candidate_family"] == HERO_STRESS_FAMILY
        and relabel["from_class"] == "indirect"
        and STRENGTH[relabel["to_class"]] < STRENGTH["indirect"]
    )
    conflict = bool(targets_hero_pattern and gov_001 is not None and hero_indirect)
    gov_001_class = gov_001.get("fit_class") if gov_001 else None
    return {
        "gate": "gov_001_invariant",
        "status": "fail" if conflict else "pass",
        "gov_001_fit_class": gov_001_class,
        "hero_cluster": HERO_CLUSTER,
        "conflicting_indirect_goldens": hero_indirect,
        "detail": (
            (
                f"gov_001 golden-labels the filing-vs-completion thesis "
                f"'{gov_001_class}'. The guard would downgrade 'indirect' -> "
                f"'{relabel['to_class']}', regressing gov_001 and "
                f"{len(hero_indirect)} hero-cluster 'indirect' golden(s)."
            )
            if conflict
            else "The guard does not contradict the gov_001 hero golden."
        ),
    }


def _normalized_output_path(path: str) -> str:
    """Canonicalize a path so ``..`` traversal cannot hide a protected write."""
    return posixpath.normpath(path.replace("\\", "/"))


def gate_no_auto_promotion(
    plan: dict[str, Any], output_paths: list[str]
) -> dict[str, Any]:
    """The loop must apply nothing and promote nothing to strict goldens.

    Paths are normalized before checking so a traversal string such as
    ``evals/repair_loop/../../app/policy/fit.py`` cannot slip a protected write
    past this last-line guard.
    """
    normalized = [(_normalized_output_path(path), path) for path in output_paths]
    wrote_protected = sorted(
        original for norm, original in normalized if norm in PROTECTED_PATHS
    )
    escaped_output_dir = sorted(
        original
        for norm, original in normalized
        if norm != "evals/repair_loop" and not norm.startswith("evals/repair_loop/")
    )
    clean = (
        plan["applied"] is False
        and plan["writes_strict_expected_labels"] is False
        and plan["writes_policy_code"] is False
        and not wrote_protected
        and not escaped_output_dir
    )
    return {
        "gate": "no_auto_promotion",
        "status": "pass" if clean else "fail",
        "plan_applied": plan["applied"],
        "wrote_protected_paths": wrote_protected,
        "outputs_outside_repair_loop": escaped_output_dir,
        "detail": (
            "The plan is unapplied and every output stays under evals/repair_loop/; "
            "nothing is promoted to strict goldens."
            if clean
            else "The loop attempted to apply changes or write a protected path."
        ),
    }


def gate_no_gemini_owned_final_class(
    rows: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """The deterministic gate, not Gemini, must own the final class.

    If the guard's only effect is to make the deterministic class adopt Gemini's
    advisory class on the affected rows, Gemini is effectively owning the final
    label through the back door.
    """
    by_case = {row["case_id"]: row for row in rows}
    gemini_adopted = []
    for case_id in plan["predicted_affected_case_ids"]:
        row = by_case.get(case_id)
        if row is None:
            continue
        before = row["deterministic_fit_class"]
        after = _apply_relabel(row, plan)
        if after != before and after == row.get("gemini_fit_class"):
            gemini_adopted.append(
                {
                    "case_id": case_id,
                    "before": before,
                    "after": after,
                    "gemini_fit_class": row.get("gemini_fit_class"),
                }
            )
    return {
        "gate": "no_gemini_owned_final_class",
        "status": "pass" if not gemini_adopted else "fail",
        "gemini_adopted_cases": gemini_adopted,
        "detail": (
            "The guard does not make the deterministic class track Gemini advisory."
            if not gemini_adopted
            else (
                f"On {len(gemini_adopted)} case(s) the guard makes the deterministic "
                "class adopt Gemini's advisory label; that lets the model own the "
                "final class."
            )
        ),
    }


def gate_overclaim(
    rows: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """The guard must not introduce a confirmed overclaim.

    Per the Stress-40 doctrine, the only *confirmed* dangerous overclaim is a
    deterministic ``direct`` over a non-``direct`` truth. The ``strong_over_weak_no``
    band (e.g. ``indirect`` over a synthetic ``weak_proxy``) is an explicit review
    candidate, NOT a confirmed error, so it is deliberately not counted here.
    This gate is the non-regression mirror of ``direct_false_positive_reduction``:
    it fails only if the guard *introduces* a new direct-band overclaim.
    """

    def confirmed_overclaims(label_fn) -> int:
        return sum(
            1
            for row in rows
            if label_fn(row) == "direct" and row["expected_fit_class"] != "direct"
        )

    before = confirmed_overclaims(lambda row: row["deterministic_fit_class"])
    after = confirmed_overclaims(lambda row: _apply_relabel(row, plan))
    introduced = max(0, after - before)
    reduced = max(0, before - after)
    return {
        "gate": "overclaim",
        "status": "pass" if introduced == 0 else "fail",
        "overclaims_before": before,
        "overclaims_after": after,
        "overclaims_reduced": reduced,
        "overclaims_introduced": introduced,
        "detail": (
            (
                f"Confirmed direct-band overclaims: {before} -> {after}. The guard "
                "introduces none"
                + (
                    f" and retires {reduced}."
                    if reduced
                    else "; there are none to retire, so this is no shipping "
                    "justification. The debatable strong-over-weak/no band is review "
                    "evidence, not a confirmed overclaim."
                )
            )
            if introduced == 0
            else f"The guard introduces {introduced} new direct-band overclaim(s)."
        ),
    }


SAFETY_GATES = (
    "twin_safety",
    "tpu_hero_invariant",
    "gov_001_invariant",
    "no_auto_promotion",
    "no_gemini_owned_final_class",
    "overclaim",
)


def run_verifier(
    rows: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    plan: dict[str, Any],
    output_paths: list[str],
) -> dict[str, Any]:
    gates = [
        gate_direct_false_positive_reduction(rows, plan),
        gate_twin_safety(rows, plan),
        gate_tpu_hero_invariant(rows, governance, plan),
        gate_gov_001_invariant(governance, plan),
        gate_no_auto_promotion(plan, output_paths),
        gate_no_gemini_owned_final_class(rows, plan),
        gate_overclaim(rows, plan),
    ]
    gates_by_name = {gate["gate"]: gate for gate in gates}

    direct_fp = gates_by_name["direct_false_positive_reduction"]
    overclaim = gates_by_name["overclaim"]
    reduces_danger = direct_fp["reduction"] > 0 or overclaim["overclaims_reduced"] > 0
    safety_ok = all(
        gates_by_name[name]["status"] == "pass" for name in SAFETY_GATES
    )
    blocking = sorted(gate["gate"] for gate in gates if gate["status"] == "fail")

    if reduces_danger and safety_ok:
        verdict = VERDICT_GO
        ship_decision = "ship_candidate"
    elif safety_ok and not reduces_danger:
        verdict = VERDICT_CANDIDATE_ONLY
        ship_decision = "candidate_only"
    else:
        verdict = VERDICT_NO_GO
        ship_decision = "candidate_only"

    rationale = _verdict_rationale(verdict, reduces_danger, gates_by_name, blocking)
    return {
        "gates": gates,
        "reduces_real_danger": reduces_danger,
        "safety_invariants_hold": safety_ok,
        "blocking_gates": blocking,
        "verdict": verdict,
        "ship_decision": ship_decision,
        "human_label": f"{ship_decision} / {verdict}_for_shipping",
        "rationale": rationale,
    }


def _verdict_rationale(
    verdict: str,
    reduces_danger: bool,
    gates_by_name: dict[str, dict[str, Any]],
    blocking: list[str],
) -> str:
    if verdict == VERDICT_GO:
        return (
            "The guard reduces a real danger and clears every safety invariant. "
            "Recommend implementing the scoped guard with targeted tests."
        )
    if verdict == VERDICT_CANDIDATE_ONLY:
        return (
            "The guard introduces no regression but reduces no direct false "
            "positives or overclaims. Keep it candidate-only until a real failure "
            "justifies the change."
        )
    benefit = (
        "reduces no direct false positives (no real danger to remove)"
        if not reduces_danger
        else "reduces a danger"
    )
    safety_blocking = [gate for gate in blocking if gate in SAFETY_GATES]
    safety = (
        f" and violates safety invariants ({', '.join(safety_blocking)})"
        if safety_blocking
        else ""
    )
    return (
        f"NO-GO for shipping. The top guard {benefit}{safety}. It only nudges "
        "deterministic classes toward a debatable synthetic stress label that matches "
        "Gemini's advisory call, contradicting the gov_001 hero golden and damaging "
        "correctly classified twins. Keep candidate-only."
    )


# --------------------------------------------------------------------------- #
# Model assembly
# --------------------------------------------------------------------------- #
def build_loop_state(
    *,
    run_files: tuple[Path, ...] | list[Path] = DEFAULT_RUN_FILES,
    governance_path: Path = GOVERNANCE_EXAMPLES,
) -> dict[str, Any]:
    runs = load_runs(run_files)
    invariant = run_invariant_map(runs)
    # The deterministic gate is run-invariant (asserted in the appendix), so run 1
    # is the canonical evidence for per-case review lists.
    canonical = runs[0][1] if runs else []
    governance = load_governance(governance_path)
    appendix = load_appendix()
    policy_directions = latest_policy_directions()

    ranked = rank_candidates(canonical, invariant)
    if not ranked:
        raise ValueError("No review candidates found; nothing to repair.")
    top = ranked[0]
    plan = draft_patch_plan(top, canonical, policy_directions)

    output_paths = [
        "evals/repair_loop/loop_state.json",
        "evals/repair_loop/LOOP_STATE.md",
        "evals/repair_loop/TOP_CANDIDATE_PROPOSAL.md",
    ]
    verifier = run_verifier(canonical, governance, plan, output_paths)

    stability = appendix.get("deterministic_stability", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "loop_role": "bounded_repair_discovery",
        "core_improvement_proof": "tpu_phoenix_mcp_trace_repair",
        "supporting_governance_evidence": "governance_50_review_memory_and_truth_scope",
        "stress_role": "appendix_evidence",
        "applies_changes": False,
        "runs_new_gemini_calls": False,
        "runs_new_stress_loops": False,
        "writes_prompts": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
        "inputs": {
            "run_files": [Path(path).name for path in run_files],
            "appendix_json": str(APPENDIX_JSON.relative_to(REPO_ROOT)),
            "governance_examples": str(GOVERNANCE_EXAMPLES.relative_to(REPO_ROOT)),
            "failure_candidate_packets": count_failure_candidate_dirs(),
            "policy_directions_loaded": sorted(policy_directions),
        },
        "stages": ["explorer", "implementer", "verifier"],
        "deterministic_run_invariant": all(invariant.values()),
        "deterministic_direct_false_positives_total": appendix.get(
            "deterministic_direct_false_positives_total"
        ),
        "deterministic_unstable_cases": len(stability.get("unstable_cases", [])),
        "ranking_weights": RANKING_WEIGHTS,
        "explorer": {
            "ranked_candidates": ranked,
            "top_candidate": top["family"],
        },
        "implementer": {"patch_plan": plan},
        "verifier": verifier,
        "top_candidate": top["family"],
        "verdict": verifier["verdict"],
        "ship_decision": verifier["ship_decision"],
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _gate_emoji(status: str) -> str:
    return {"pass": "PASS", "fail": "FAIL"}.get(status, status.upper())


def render_loop_markdown(model: dict[str, Any]) -> str:
    verifier = model["verifier"]
    plan = model["implementer"]["patch_plan"]
    lines = [
        "# Repair-Discovery Loop State",
        "",
        "## Scope",
        "",
        (
            "Bounded, deterministic, offline repair-discovery loop over the four "
            "committed post-patch Stress-40 runs and the Governance-50 goldens. It "
            "runs no new Gemini calls, runs no new Stress-40 loops, and writes no "
            "prompts, policy code, strict goldens, or expected-output fixtures."
        ),
        "",
        f"- Schema version: `{model['schema_version']}`",
        f"- Applies changes: `{model['applies_changes']}`",
        f"- Runs new Gemini calls: `{model['runs_new_gemini_calls']}`",
        f"- Runs new Stress-40 loops: `{model['runs_new_stress_loops']}`",
        f"- Writes prompts: `{model['writes_prompts']}`",
        f"- Writes policy code: `{model['writes_policy_code']}`",
        f"- Writes strict expected labels: `{model['writes_strict_expected_labels']}`",
        f"- Deterministic run-invariant: `{model['deterministic_run_invariant']}`",
        f"- Deterministic direct false positives (all runs): "
        f"`{model['deterministic_direct_false_positives_total']}`",
        "",
        "## Verdict",
        "",
        f"**Top candidate:** `{model['top_candidate']}`",
        "",
        f"**Verdict:** `{verifier['verdict']}` — ship decision `{verifier['ship_decision']}` "
        f"(`{verifier['human_label']}`)",
        "",
        verifier["rationale"],
        "",
        "## Stage 1 — Explorer: Ranked Candidates",
        "",
        "Axes: dangerousness (direct false positives dominate), demo value, "
        "stability, testability.",
        "",
        "| Rank | Family | Review cands | Direct FP | Dangerousness | Demo | "
        "Stability | Testability | Score |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for candidate in model["explorer"]["ranked_candidates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(candidate["rank"]),
                    f"`{candidate['family']}`",
                    str(candidate["review_candidate_count"]),
                    str(candidate["direct_false_positives"]),
                    str(candidate["dangerousness"]),
                    str(candidate["demo_value"]),
                    f"{candidate['stability']:.2f}",
                    f"{candidate['testability']:.2f}",
                    f"{candidate['score']:.2f}",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Stage 2 — Implementer: Drafted Patch Plan (not applied)",
            "",
            f"- Candidate family: `{plan['candidate_family']}`",
            f"- Applied: `{plan['applied']}`",
            f"- Prompt target: `{plan['prompt_target']}`",
            f"- Deterministic guard candidate: `{plan['deterministic_guard']['name']}` "
            f"-> `{plan['deterministic_guard']['target']}`",
            f"- Predicted relabel: `{plan['predicted_relabel']['from_class']}` -> "
            f"`{plan['predicted_relabel']['to_class']}` for "
            f"`{plan['predicted_relabel']['family']}`",
            "- Predicted affected cases: "
            + ", ".join(f"`{case}`" for case in plan["predicted_affected_case_ids"]),
            "",
            "> Prompt guardrail (proposed, unapplied): " + plan["prompt_guardrail"],
            "",
            "## Stage 3 — Verifier: Shipping Gates",
            "",
            "| Gate | Status | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for gate in verifier["gates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{gate['gate']}`",
                    _gate_emoji(gate["status"]),
                    gate["detail"].replace("|", "\\|"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            f"- Reduces real danger (direct FP or overclaim): "
            f"`{verifier['reduces_real_danger']}`",
            f"- Safety invariants hold: `{verifier['safety_invariants_hold']}`",
            "- Blocking gates: "
            + (
                ", ".join(f"`{gate}`" for gate in verifier["blocking_gates"])
                if verifier["blocking_gates"]
                else "none"
            ),
            "",
            "## How To Read This Loop",
            "",
            (
                "- The deterministic gate is the classifier of record and shows zero "
                "direct false positives across all four runs. There is no overclaim to "
                "retire."
            ),
            (
                "- The top guard would only move `indirect` review candidates toward a "
                "debatable synthetic `weak_proxy`/`no_clean_expression` label, which "
                "happens to match Gemini's advisory call."
            ),
            (
                "- That move contradicts the gov_001 hero golden (`indirect`) and "
                "downgrades correctly classified good twins, so the loop emits NO-GO and "
                "keeps the candidate review-only."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_proposal_markdown(model: dict[str, Any]) -> str:
    verifier = model["verifier"]
    plan = model["implementer"]["patch_plan"]
    top = next(
        candidate
        for candidate in model["explorer"]["ranked_candidates"]
        if candidate["family"] == model["top_candidate"]
    )
    guard = plan["deterministic_guard"]
    decision_word = "NO-GO" if verifier["verdict"] == VERDICT_NO_GO else (
        "GO" if verifier["verdict"] == VERDICT_GO else "CANDIDATE-ONLY"
    )
    lines = [
        f"# Top Candidate {decision_word}: `{model['top_candidate']}`",
        "",
        "## Decision",
        "",
        f"- Verdict: `{verifier['verdict']}`",
        f"- Ship decision: `{verifier['ship_decision']}` (`{verifier['human_label']}`)",
        f"- Reduces real danger: `{verifier['reduces_real_danger']}`",
        f"- Safety invariants hold: `{verifier['safety_invariants_hold']}`",
        "",
        verifier["rationale"],
        "",
        "## Why This Candidate Ranked First",
        "",
        f"- Review candidates: `{top['review_candidate_count']}`",
        f"- Direct false positives in family: `{top['direct_false_positives']}`",
        f"- Hero-cluster overlap: `{top['hero_cluster_overlap']}`",
        f"- Dangerousness / demo / stability / testability: "
        f"`{top['dangerousness']}` / `{top['demo_value']}` / "
        f"`{top['stability']:.2f}` / `{top['testability']:.2f}`",
        "",
        "## Drafted Patch Plan (NOT applied)",
        "",
        f"This plan is a proposal only. `applied = {plan['applied']}`. No prompt, "
        "policy, golden, or expected-output file is modified by this loop.",
        "",
        "### Prompt guardrail candidate",
        "",
        f"Target (human-approved patch only): `{plan['prompt_target']}`",
        "",
        plan["prompt_guardrail"],
        "",
        "### Deterministic guard candidate",
        "",
        f"- Name: `{guard['name']}`",
        f"- Target (human-approved patch only): `{guard['target']}`",
        f"- Proposed behavior: {guard['behavior']}",
    ]
    if plan["policy_direction"]:
        lines.extend(["", f"- Prior review direction: {plan['policy_direction']}"])
    lines.extend(
        [
            "",
            "### Predicted effect on committed rows",
            "",
            f"- Relabel: `{plan['predicted_relabel']['from_class']}` -> "
            f"`{plan['predicted_relabel']['to_class']}`",
            "- Affected cases: "
            + ", ".join(f"`{case}`" for case in plan["predicted_affected_case_ids"]),
            "",
            "## Gate Results",
            "",
            "| Gate | Status | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for gate in verifier["gates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{gate['gate']}`",
                    _gate_emoji(gate["status"]),
                    gate["detail"].replace("|", "\\|"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Remaining Risks / Follow-ups",
            "",
            "- The four event-stage review candidates remain candidate-only evidence "
            "in Phoenix; they are not promoted to strict goldens.",
            "- If a future run shows a deterministic *direct* false positive in this "
            "family, re-run this loop: the danger gate would then have something real "
            "to reduce.",
            "- Any guard must be twin-safe (preserve the good `indirect` twins) and "
            "must not regress the gov_001 hero golden before it can ship.",
            "- The deterministic gate stays the classifier of record; Gemini remains "
            "advisory and must never own the final class.",
            "",
        ]
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded, deterministic, offline repair-discovery loop over the "
            "committed Stress-40 runs and Governance-50 goldens. Emits a verdict that "
            "may be NO-GO. Runs no model calls and writes no prompts/policy/goldens."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verify the committed loop artifacts (JSON and both markdown files) "
            "match a fresh build; write nothing."
        ),
    )
    return parser.parse_args()


def _expected_artifacts(model: dict[str, Any]) -> dict[Path, str]:
    """The exact content each committed artifact should hold for this model.

    Single source of truth shared by the write path and ``--check`` so every
    artifact (JSON and both markdowns) is covered by the in-sync guarantee.
    """
    return {
        OUTPUT_JSON: json.dumps(model, indent=2, sort_keys=True) + "\n",
        OUTPUT_MARKDOWN: render_loop_markdown(model),
        PROPOSAL_MARKDOWN: render_proposal_markdown(model),
    }


def artifact_drift(model: dict[str, Any]) -> list[str]:
    """Return the committed artifacts that are missing or out of sync."""
    return sorted(
        str(path)
        for path, content in _expected_artifacts(model).items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    )


def _summary(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "schema_version": model["schema_version"],
        "top_candidate": model["top_candidate"],
        "verdict": model["verdict"],
        "ship_decision": model["ship_decision"],
        "blocking_gates": model["verifier"]["blocking_gates"],
        "reduces_real_danger": model["verifier"]["reduces_real_danger"],
        "writes_prompts": model["writes_prompts"],
        "writes_policy_code": model["writes_policy_code"],
        "writes_strict_expected_labels": model["writes_strict_expected_labels"],
        "json_path": str(OUTPUT_JSON),
        "markdown_path": str(OUTPUT_MARKDOWN),
        "proposal_path": str(PROPOSAL_MARKDOWN),
    }


def main() -> int:
    args = parse_args()
    model = build_loop_state()

    if args.check:
        drift = artifact_drift(model)
        print(
            json.dumps(
                {
                    "status": "ok" if not drift else "drift",
                    "drift_paths": drift,
                    "json_path": str(OUTPUT_JSON),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if not drift else 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, content in _expected_artifacts(model).items():
        path.write_text(content, encoding="utf-8")
    print(json.dumps(_summary(model), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
