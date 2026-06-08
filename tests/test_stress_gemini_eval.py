import json

from scripts.run_stress_gemini_eval import (
    _build_stress_gemini_failure_packet,
    _build_summary,
    _extract_fit_class,
    _parse_model_fit_proposal,
)


def test_extract_fit_class_from_model_proposal_shapes():
    assert _extract_fit_class({"semantic_fit_class": "indirect"}) == "indirect"
    assert (
        _extract_fit_class({"proposal": {"proposed_fit_class": "weak_proxy"}})
        == "weak_proxy"
    )
    raw = '{"recommended_market_id":"m1","semantic_fit_class":"direct"}'
    assert _extract_fit_class(raw) == "direct"
    assert _extract_fit_class({"unrelated": "direct"}) is None


def test_parse_model_fit_proposal_returns_json_when_possible():
    raw = json.dumps({"semantic_fit_class": "no_clean_expression"})
    parsed = _parse_model_fit_proposal(raw)
    assert parsed == {"semantic_fit_class": "no_clean_expression"}
    assert _parse_model_fit_proposal("truncated {") == "truncated {"


def test_stress_summary_uses_gemini_as_primary_and_policy_as_guardrail():
    rows = [
        _row(
            family="event_stage_mismatch",
            gemini_match=False,
            deterministic_match=True,
        ),
        _row(
            family="event_stage_mismatch",
            gemini_match=True,
            deterministic_match=True,
        ),
        _row(
            family="metric_mismatch",
            gemini_match=None,
            deterministic_match=True,
        ),
        _row(
            family="metric_mismatch",
            gemini_match=False,
            deterministic_match=False,
            exported=True,
        ),
    ]

    summary = _build_summary(
        rows,
        adk_configured=True,
        run_at_utc="2026-06-09T00:00:00+00:00",
    )

    assert summary["primary_evaluation_target"] == "gemini_advisory_proposal"
    assert summary["gemini_match"] == 1
    assert summary["gemini_mismatch"] == 2
    assert summary["missing_gemini_proposal"] == 1
    assert summary["deterministic_mismatch"] == 1
    assert summary["failure_candidates_exported"] == 1
    assert summary["by_family"]["event_stage_mismatch"]["gemini_mismatch"] == 1
    assert summary["by_family"]["metric_mismatch"]["missing_gemini_proposal"] == 1


def test_stress_gemini_failure_packet_is_candidate_only():
    case = {
        "case_id": "stress_es_openai_filing_vs_completion_001",
        "thesis": "OpenAI is preparing to file confidentially for an IPO.",
        "truth_scope": "synthetic_expected_label",
        "expected_label_source": "constructed_template",
        "expected_fit_class": "weak_proxy",
        "mismatch_family": "event_stage_mismatch",
        "trap_description": "Filing preparation is not IPO completion.",
        "market": {
            "market_id": "synth_openai_ipo_cap_300b",
            "title": "OpenAI IPO closing market cap above $300B in 2026?",
            "resolution_rules": "Resolves on completed IPO closing market cap.",
        },
    }
    row = {
        "run_id": "run_stress",
        "phoenix_trace_id": "trace_stress",
        "phoenix_trace_url": "https://phoenix.example/traces/trace_stress",
        "gemini_fit_class": "indirect",
        "gemini_proposal_json": '{"semantic_fit_class":"indirect"}',
        "deterministic_fit_class": "weak_proxy",
        "deterministic_match": True,
        "recommended_market_id": "synth_openai_ipo_cap_300b",
    }

    packet = _build_stress_gemini_failure_packet(case=case, row=row)
    proposed = packet["proposed_eval_case"]
    failure = packet["failure_signal"]

    assert failure["triggered_metrics"] == ["gemini_advisory_mismatch"]
    assert failure["candidate_only"] is True
    assert proposed["truth_scope"] == "synthetic_expected_label"
    assert proposed["canonical_truth"] is False
    assert proposed["writes_strict_expected_labels"] is False
    assert proposed["writes_policy_code"] is False
    assert "disregard" in proposed["human_review_options"]
    assert proposed["observed_gemini_fit_class"] == "indirect"
    assert proposed["deterministic_match"] is True


def _row(
    *,
    family: str,
    gemini_match: bool | None,
    deterministic_match: bool,
    exported: bool = False,
    error: str | None = None,
):
    return {
        "mismatch_family": family,
        "gemini_match": gemini_match,
        "deterministic_match": deterministic_match,
        "failure_candidate_exported": exported,
        "error": error,
    }
