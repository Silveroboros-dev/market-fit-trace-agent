import json
import re
import subprocess
import sys
from pathlib import Path

import scripts.run_repair_loop as run_repair_loop
from scripts.run_repair_loop import (
    OUTPUT_JSON,
    OUTPUT_MARKDOWN,
    PROPOSAL_MARKDOWN,
    VERDICT_CANDIDATE_ONLY,
    VERDICT_NO_GO,
    artifact_drift,
    build_loop_state,
    draft_patch_plan,
    gate_direct_false_positive_reduction,
    gate_gov_001_invariant,
    gate_no_auto_promotion,
    gate_no_gemini_owned_final_class,
    gate_overclaim,
    gate_tpu_hero_invariant,
    gate_twin_safety,
    rank_candidates,
    render_loop_markdown,
    render_proposal_markdown,
    run_verifier,
)

ROOT = Path(__file__).resolve().parents[1]


def _row(case_id, family, expected, deterministic, gemini="weak_proxy", trace="u"):
    return {
        "case_id": case_id,
        "mismatch_family": family,
        "expected_fit_class": expected,
        "deterministic_fit_class": deterministic,
        "gemini_fit_class": gemini,
        "phoenix_trace_url": trace,
    }


def _twin_rows():
    # 2 bad twins (det indirect, expected weaker) + 1 good twin (det == expected)
    return [
        _row("es_bad_a", "event_stage_mismatch", "weak_proxy", "indirect", "weak_proxy"),
        _row("es_bad_b", "event_stage_mismatch", "no_clean_expression", "indirect", "indirect"),
        _row("es_good_a", "event_stage_mismatch", "indirect", "indirect", "weak_proxy"),
        _row("mm_a", "metric_mismatch", "weak_proxy", "indirect", "weak_proxy"),
    ]


def _governance():
    return [
        {
            "governance_id": "gov_001_openai-filing",
            "case_id": "ui-openai-filing",
            "hero_cluster": "ai_startup_ipo_stage_mismatch",
            "fit_class": "indirect",
            "embedding_text": "openai confidential filing ipo",
        },
        {
            "governance_id": "gov_014_trace-repair-tpu",
            "case_id": "trace_repair_tpu_frontier_gap_001",
            "hero_cluster": None,
            "fit_class": "weak_proxy",
            "embedding_text": "google tpu frontier gap gemini",
        },
    ]


# --------------------------------------------------------------------------- #
# Stage 1 — explorer
# --------------------------------------------------------------------------- #
def test_rank_candidates_puts_hero_event_stage_first():
    rows = _twin_rows()
    invariant = {row["case_id"]: True for row in rows}
    ranked = rank_candidates(rows, invariant)

    assert ranked[0]["family"] == "event_stage_mismatch"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["hero_cluster_overlap"] is True
    # event_stage has more review candidates AND the hero demo bonus -> higher score
    assert ranked[0]["score"] > ranked[1]["score"]
    families = {candidate["family"] for candidate in ranked}
    assert "metric_mismatch" in families


def test_rank_candidates_ignores_families_without_review_candidates():
    rows = [
        _row("match_a", "metric_mismatch", "indirect", "indirect"),
        _row("under_a", "horizon_mismatch", "indirect", "weak_proxy"),
    ]
    invariant = {row["case_id"]: True for row in rows}
    assert rank_candidates(rows, invariant) == []


# --------------------------------------------------------------------------- #
# Stage 2 — implementer
# --------------------------------------------------------------------------- #
def test_draft_patch_plan_is_never_applied_and_targets_indirect_rows():
    rows = _twin_rows()
    invariant = {row["case_id"]: True for row in rows}
    top = rank_candidates(rows, invariant)[0]
    plan = draft_patch_plan(top, rows, {"event_stage_mismatch": "stage direction"})

    assert plan["applied"] is False
    assert plan["writes_prompts"] is False
    assert plan["writes_policy_code"] is False
    assert plan["writes_strict_expected_labels"] is False
    assert plan["predicted_relabel"] == {
        "family": "event_stage_mismatch",
        "from_class": "indirect",
        "to_class": "weak_proxy",
        "scope": plan["predicted_relabel"]["scope"],
    }
    # both bad twins and the good twin are caught (a text guard can't separate them)
    assert plan["predicted_affected_case_ids"] == ["es_bad_a", "es_bad_b", "es_good_a"]


# --------------------------------------------------------------------------- #
# Stage 3 — verifier gates
# --------------------------------------------------------------------------- #
def _plan_for(rows):
    invariant = {row["case_id"]: True for row in rows}
    top = rank_candidates(rows, invariant)[0]
    return draft_patch_plan(top, rows, {})


def test_direct_false_positive_gate_fails_when_no_fp_to_reduce():
    rows = _twin_rows()
    gate = gate_direct_false_positive_reduction(rows, _plan_for(rows))
    assert gate["before"] == 0
    assert gate["after"] == 0
    assert gate["reduction"] == 0
    assert gate["status"] == "fail"


def test_direct_false_positive_gate_passes_when_it_removes_a_real_fp():
    # det == direct while expected != direct is a real direct false positive
    rows = [
        _row("es_fp", "event_stage_mismatch", "weak_proxy", "direct", "weak_proxy"),
    ]
    # craft a plan that downgrades that direct false positive
    plan = {
        "candidate_family": "event_stage_mismatch",
        "predicted_relabel": {
            "family": "event_stage_mismatch",
            "from_class": "direct",
            "to_class": "weak_proxy",
            "scope": "x",
        },
        "predicted_affected_case_ids": ["es_fp"],
    }
    gate = gate_direct_false_positive_reduction(rows, plan)
    assert gate["before"] == 1
    assert gate["after"] == 0
    assert gate["reduction"] == 1
    assert gate["status"] == "pass"


def test_twin_safety_gate_flags_good_twin_collateral():
    rows = _twin_rows()
    gate = gate_twin_safety(rows, _plan_for(rows))
    assert gate["status"] == "fail"
    damaged = {item["case_id"] for item in gate["good_twins_damaged"]}
    assert "es_good_a" in damaged
    assert "es_bad_a" not in damaged


def test_gov_001_invariant_gate_fails_on_hero_downgrade():
    rows = _twin_rows()
    gate = gate_gov_001_invariant(_governance(), _plan_for(rows))
    assert gate["status"] == "fail"
    assert gate["gov_001_fit_class"] == "indirect"
    assert gate["conflicting_indirect_goldens"]


def test_gov_001_invariant_gate_passes_for_non_hero_family():
    rows = [
        _row("mm_a", "metric_mismatch", "weak_proxy", "indirect", "weak_proxy"),
        _row("mm_b", "metric_mismatch", "no_clean_expression", "indirect", "weak_proxy"),
    ]
    gate = gate_gov_001_invariant(_governance(), _plan_for(rows))
    assert gate["status"] == "pass"


def test_tpu_hero_invariant_passes_when_guard_avoids_tpu():
    rows = _twin_rows()
    gate = gate_tpu_hero_invariant(rows, _governance(), _plan_for(rows))
    assert gate["status"] == "pass"
    assert gate["touched_tpu_cases"] == []
    assert any("tpu" in anchor.lower() for anchor in gate["tpu_governance_anchors"])


def test_tpu_hero_invariant_fails_if_guard_touches_tpu():
    rows = [
        _row("es_tpu_case", "event_stage_mismatch", "weak_proxy", "indirect", "weak_proxy"),
    ]
    gate = gate_tpu_hero_invariant(rows, _governance(), _plan_for(rows))
    assert gate["status"] == "fail"
    assert gate["touched_tpu_cases"] == ["es_tpu_case"]


def test_no_auto_promotion_gate_detects_protected_writes():
    rows = _twin_rows()
    plan = _plan_for(rows)
    ok = gate_no_auto_promotion(plan, ["evals/repair_loop/loop_state.json"])
    assert ok["status"] == "pass"

    bad = gate_no_auto_promotion(plan, ["app/policy/fit.py"])
    assert bad["status"] == "fail"
    assert "app/policy/fit.py" in bad["wrote_protected_paths"]

    escaped = gate_no_auto_promotion(plan, ["evals/market_fit_v1/expected_outputs.jsonl"])
    assert escaped["status"] == "fail"


def test_no_auto_promotion_gate_normalizes_path_traversal():
    rows = _twin_rows()
    plan = _plan_for(rows)
    # a traversal string that resolves to a protected file must not slip through
    traversal = gate_no_auto_promotion(
        plan, ["evals/repair_loop/../../app/policy/fit.py"]
    )
    assert traversal["status"] == "fail"
    assert "evals/repair_loop/../../app/policy/fit.py" in traversal["wrote_protected_paths"]
    assert traversal["outputs_outside_repair_loop"]


def test_no_gemini_owned_final_class_gate_flags_adoption():
    rows = _twin_rows()
    gate = gate_no_gemini_owned_final_class(rows, _plan_for(rows))
    assert gate["status"] == "fail"
    adopted = {item["case_id"] for item in gate["gemini_adopted_cases"]}
    # es_bad_a: indirect -> weak_proxy adopts gemini weak_proxy
    assert "es_bad_a" in adopted


def test_overclaim_gate_introduces_none_but_offers_no_reduction():
    rows = _twin_rows()
    gate = gate_overclaim(rows, _plan_for(rows))
    assert gate["overclaims_introduced"] == 0
    assert gate["status"] == "pass"
    # downgrading never introduces overclaim; there is nothing to retire here
    assert gate["overclaims_reduced"] >= 0


# --------------------------------------------------------------------------- #
# Verifier verdict + NO-GO behavior
# --------------------------------------------------------------------------- #
def test_run_verifier_emits_no_go_on_synthetic_twins():
    rows = _twin_rows()
    verifier = run_verifier(
        rows, _governance(), _plan_for(rows), ["evals/repair_loop/loop_state.json"]
    )
    assert verifier["verdict"] == VERDICT_NO_GO
    assert verifier["ship_decision"] == "candidate_only"
    assert verifier["reduces_real_danger"] is False
    assert "gov_001_invariant" in verifier["blocking_gates"]
    assert "twin_safety" in verifier["blocking_gates"]
    assert "direct_false_positive_reduction" in verifier["blocking_gates"]


def test_run_verifier_can_emit_go_when_a_real_fp_is_safely_removed():
    # a guard that removes a real direct FP and breaks no safety invariant
    rows = [
        _row("mm_fp", "metric_mismatch", "weak_proxy", "direct", "no_clean_expression"),
    ]
    plan = {
        "candidate_family": "metric_mismatch",
        "applied": False,
        "writes_prompts": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
        "predicted_relabel": {
            "family": "metric_mismatch",
            "from_class": "direct",
            "to_class": "weak_proxy",
            "scope": "x",
        },
        "predicted_affected_case_ids": ["mm_fp"],
    }
    verifier = run_verifier(
        rows, _governance(), plan, ["evals/repair_loop/loop_state.json"]
    )
    assert verifier["reduces_real_danger"] is True
    assert verifier["safety_invariants_hold"] is True
    assert verifier["verdict"] == "go"


def test_run_verifier_emits_candidate_only_when_safe_but_no_danger_reduced():
    # all safety gates pass, but a no-op plan reduces no direct false positive
    rows = [_row("noop_a", "metric_mismatch", "indirect", "indirect", "indirect")]
    plan = {
        "candidate_family": "metric_mismatch",
        "applied": False,
        "writes_prompts": False,
        "writes_policy_code": False,
        "writes_strict_expected_labels": False,
        "predicted_relabel": {
            "family": "metric_mismatch",
            "from_class": "indirect",
            "to_class": "weak_proxy",
            "scope": "x",
        },
        "predicted_affected_case_ids": [],
    }
    verifier = run_verifier(
        rows, _governance(), plan, ["evals/repair_loop/loop_state.json"]
    )
    assert verifier["reduces_real_danger"] is False
    assert verifier["safety_invariants_hold"] is True
    assert verifier["verdict"] == VERDICT_CANDIDATE_ONLY
    assert verifier["ship_decision"] == "candidate_only"
    assert verifier["blocking_gates"] == ["direct_false_positive_reduction"]


# --------------------------------------------------------------------------- #
# End-to-end over committed artifacts
# --------------------------------------------------------------------------- #
def test_build_loop_state_over_committed_data_is_no_go():
    model = build_loop_state()
    assert model["top_candidate"] == "event_stage_mismatch"
    assert model["verdict"] == VERDICT_NO_GO
    assert model["ship_decision"] == "candidate_only"
    assert model["applies_changes"] is False
    assert model["runs_new_gemini_calls"] is False
    assert model["writes_prompts"] is False
    assert model["writes_policy_code"] is False
    assert model["writes_strict_expected_labels"] is False
    assert model["deterministic_run_invariant"] is True
    assert model["deterministic_direct_false_positives_total"] == 0
    # the four event-stage review candidates are the top family's members
    top = model["explorer"]["ranked_candidates"][0]
    assert top["review_candidate_count"] == 4
    assert "stress_es_openai_filing_vs_completion_001" in top["members"]
    # the loop renders without error
    assert "Repair-Discovery Loop State" in render_loop_markdown(model)
    assert "NO-GO" in render_proposal_markdown(model)


def test_committed_loop_state_json_is_in_sync():
    assert OUTPUT_JSON.exists(), "run `make repair-loop` to generate loop_state.json"
    on_disk = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    assert on_disk == build_loop_state()


def test_committed_markdown_artifacts_are_in_sync():
    model = build_loop_state()
    assert OUTPUT_MARKDOWN.exists() and PROPOSAL_MARKDOWN.exists()
    assert OUTPUT_MARKDOWN.read_text(encoding="utf-8") == render_loop_markdown(model)
    assert PROPOSAL_MARKDOWN.read_text(encoding="utf-8") == render_proposal_markdown(model)


def test_all_committed_artifacts_are_in_sync():
    # the in-sync guarantee must cover every committed artifact, not just the JSON
    assert artifact_drift(build_loop_state()) == []


def test_artifact_drift_detects_markdown_divergence(monkeypatch):
    model = build_loop_state()
    assert artifact_drift(model) == []
    monkeypatch.setattr(run_repair_loop, "render_loop_markdown", lambda _model: "DRIFT")
    drift = artifact_drift(model)
    assert any("LOOP_STATE.md" in path for path in drift)
    assert not any("loop_state.json" in path for path in drift)


def test_check_cli_exits_zero_and_reports_ok_when_in_sync():
    # exercises main(), the --check branch, and the 0 return contract end to end
    result = subprocess.run(
        [sys.executable, "scripts/run_repair_loop.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["drift_paths"] == []


# --------------------------------------------------------------------------- #
# Command contract (read-only, no promotion)
# --------------------------------------------------------------------------- #
def test_repair_loop_make_target_is_read_only():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = re.search(
        r"^repair-loop:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE
    )
    assert target is not None
    body = target.group("body")
    assert "scripts/run_repair_loop.py" in body
    assert "expected_outputs.jsonl" not in body
    assert "app/prompts.py" not in body
    assert "app/policy/fit.py" not in body
