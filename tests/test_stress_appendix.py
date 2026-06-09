import json

from scripts.build_stress_appendix import (
    OUTPUT_JSON,
    build_appendix,
    classify_deterministic,
    deterministic_decomposition,
    deterministic_stability,
    gemini_advisory_stats,
    render_markdown,
)


def test_classify_deterministic_buckets():
    # exact agreement
    assert classify_deterministic("direct", "direct") == "match"
    assert classify_deterministic("weak_proxy", "weak_proxy") == "match"
    # dangerous direction: deterministic asserts direct when expected is not direct
    assert classify_deterministic("indirect", "direct") == "direct_false_positive"
    assert classify_deterministic("no_clean_expression", "direct") == "direct_false_positive"
    # stronger than a synthetic weak/no label -> review candidate, NOT a false positive
    assert classify_deterministic("weak_proxy", "indirect") == "strong_over_weak_no"
    assert classify_deterministic("no_clean_expression", "indirect") == "strong_over_weak_no"
    assert classify_deterministic("no_clean_expression", "weak_proxy") == "strong_over_weak_no"
    # safe, conservative direction
    assert classify_deterministic("indirect", "weak_proxy") == "under_call"
    assert classify_deterministic("indirect", "no_clean_expression") == "under_call"


def test_gemini_advisory_stats_counts_missing_and_rate():
    rows = [
        {"gemini_proposal_present": True, "gemini_match": True},
        {"gemini_proposal_present": True, "gemini_match": False},
        {"gemini_proposal_present": False, "gemini_match": False},
    ]
    stats = gemini_advisory_stats(rows)
    assert stats["total"] == 3
    assert stats["proposals_present"] == 2
    assert stats["missing_proposals"] == 1
    assert stats["advisory_mismatches"] == 1
    assert stats["advisory_mismatch_rate"] == 0.5


def test_deterministic_decomposition_separates_false_positive_from_review_candidate():
    rows = [
        {
            "case_id": "a",
            "mismatch_family": "event_stage_mismatch",
            "expected_fit_class": "weak_proxy",
            "deterministic_fit_class": "indirect",
            "phoenix_trace_url": "u",
        },
        {
            "case_id": "b",
            "mismatch_family": "event_stage_mismatch",
            "expected_fit_class": "indirect",
            "deterministic_fit_class": "direct",
            "phoenix_trace_url": "u",
        },
        {
            "case_id": "c",
            "mismatch_family": "event_stage_mismatch",
            "expected_fit_class": "indirect",
            "deterministic_fit_class": "indirect",
            "phoenix_trace_url": "u",
        },
    ]
    decomposition = deterministic_decomposition(rows)
    assert decomposition["counts"]["strong_over_weak_no"] == 1
    assert decomposition["counts"]["direct_false_positive"] == 1
    assert decomposition["counts"]["match"] == 1
    assert [c["case_id"] for c in decomposition["strong_over_weak_no_candidates"]] == ["a"]
    assert [c["case_id"] for c in decomposition["direct_false_positive_cases"]] == ["b"]


def test_deterministic_stability_flags_disagreement():
    runs = [
        ("run_1", [{"case_id": "x", "deterministic_fit_class": "indirect"}]),
        ("run_2", [{"case_id": "x", "deterministic_fit_class": "weak_proxy"}]),
    ]
    stability = deterministic_stability(runs)
    assert stability["distinct_cases"] == 1
    assert stability["present_in_all_runs"] == 1
    assert len(stability["unstable_cases"]) == 1


def test_appendix_over_committed_runs_matches_known_signal():
    model = build_appendix()
    assert model["runs_summarized"] == 4
    assert model["cases_per_run"] == [40, 40, 40, 40]
    # Gemini advisory is the proposer and varies run to run
    assert model["gemini_advisory_mismatches_per_run"] == [17, 17, 16, 21]
    # the deterministic gate is the classifier of record and is run-invariant
    stability = model["deterministic_stability"]
    assert stability["distinct_cases"] == 40
    assert stability["present_in_all_runs"] == 40
    assert stability["unstable_cases"] == []
    # dangerous direction is zero; strong-over cases are review candidates, not FPs
    assert model["deterministic_direct_false_positives_total"] == 0
    assert model["deterministic_strong_over_weak_no_per_run"] == [11, 11, 11, 11]
    assert len(model["review_candidates"]) == 11
    assert model["direct_false_positive_cases"] == []
    assert model["runs_new_gemini_calls"] is False
    assert "Stress-40 Appendix" in render_markdown(model)


def test_committed_appendix_json_is_in_sync():
    # the committed artifact must equal a fresh recompute (no silent drift)
    on_disk = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    assert on_disk == build_appendix()
