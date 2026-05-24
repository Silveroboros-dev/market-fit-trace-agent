from app.phoenix_mcp import MAX_TRACE_SUMMARY_CHARS, _summarize_phoenix_mcp_result


def test_phoenix_mcp_summary_is_bounded_and_signal_focused():
    raw = (
        "irrelevant payload " * 400
        + " fit_eval_run false_strong_recommendation weak_proxy_detected"
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
    assert "Recommended market was too strong." in summary
