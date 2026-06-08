from app.phoenix_mcp import MAX_TRACE_SUMMARY_CHARS, _summarize_phoenix_mcp_result


def test_phoenix_mcp_summary_is_bounded_and_signal_focused():
    raw = (
        "irrelevant payload " * 400
        + " fit_eval_run false_strong_recommendation weak_proxy_detected "
        "causal_mechanism_mismatch trace_repair_candidate"
    )

    summary = _summarize_phoenix_mcp_result(
        raw,
        phoenix_trace_id="trace_123",
        fallback_summary="Recommended market was too strong.",
    )

    assert len(summary) <= MAX_TRACE_SUMMARY_CHARS + len("...[truncated]")
    assert "trace_123" in summary
    assert "false_strong_recommendation" in summary
    assert "weak_proxy_detected" in summary
    assert "causal_mechanism_mismatch" in summary
    assert "Recommended market was too strong." in summary


def test_phoenix_mcp_summary_rejects_error_payload():
    summary = _summarize_phoenix_mcp_result(
        "Phoenix server version could not be determined.",
        phoenix_trace_id="trace_123",
        fallback_summary="false_strong_recommendation=true",
    )

    assert summary == ""


def test_phoenix_mcp_summary_rejects_payload_without_eval_signals():
    summary = _summarize_phoenix_mcp_result(
        "Trace payload returned only generic span content without eval annotations.",
        phoenix_trace_id="trace_123",
        fallback_summary="false_strong_recommendation=true",
    )

    assert summary == ""


def test_phoenix_mcp_summary_rejects_payload_without_repair_signals():
    summary = _summarize_phoenix_mcp_result(
        "fit_eval_run schema_valid trace_repair_candidate",
        phoenix_trace_id="trace_123",
        fallback_summary=(
            "false_strong_recommendation=true; causal_mechanism_mismatch=true"
        ),
    )

    assert summary == ""
