from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.ledger import LedgerStore
from app.models import PhoenixInspection

MAX_TRACE_SUMMARY_CHARS = 1500


class PhoenixMCPInspector:
    """Best-effort Phoenix MCP bridge with a local fallback for repeatable demos."""

    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    async def inspect_failed_run(self, run_id: str) -> PhoenixInspection:
        run = self.store.get_run(run_id)
        eval_record = self.store.get_latest_eval_for_run(run_id)
        phoenix_trace_id = run.get("phoenix_trace_id") or "local-trace-unset"
        failure_summary = (
            eval_record.get("failure_summary") if eval_record else None
        ) or "No failed eval was recorded for this run."

        if settings.phoenix_mcp_enabled:
            mcp_summary = await self._try_phoenix_mcp_summary(phoenix_trace_id, failure_summary)
            if mcp_summary:
                return PhoenixInspection(
                    run_id=run_id,
                    phoenix_trace_id=phoenix_trace_id,
                    source="phoenix_mcp",
                    fallback_used=False,
                    summary=mcp_summary,
                    recommended_prompt_version="v2_trace_inspected",
                    mcp_configured=True,
                )

        return PhoenixInspection(
            run_id=run_id,
            phoenix_trace_id=phoenix_trace_id,
            source="local_eval_fallback",
            fallback_used=True,
            summary=(
                f"Trace-linked eval found an overclaim: {failure_summary} "
                "Revise the second run to treat adjacent leaderboard or hardware markets as weak "
                "proxies unless the market resolution directly expresses the thesis."
            ),
            recommended_prompt_version="v2_trace_inspected",
            mcp_configured=settings.phoenix_mcp_enabled,
        )

    async def _try_phoenix_mcp_summary(
        self, phoenix_trace_id: str, fallback_summary: str
    ) -> str | None:
        try:
            from mcp.client.stdio import stdio_client

            from mcp import ClientSession, StdioServerParameters
        except Exception:
            return None

        try:
            params = StdioServerParameters(
                command=settings.phoenix_mcp_command,
                args=list(settings.phoenix_mcp_args),
                env={
                    "PHOENIX_API_KEY": settings.phoenix_api_key or "",
                    "PHOENIX_BASE_URL": settings.phoenix_base_url or "",
                },
            )
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = {tool.name for tool in tools.tools}
                    if "get-trace" in tool_names:
                        result = await session.call_tool(
                            "get-trace",
                            {
                                "project_identifier": settings.phoenix_project_name,
                                "trace_id": phoenix_trace_id,
                                "include_annotations": True,
                            },
                        )
                        return _summarize_phoenix_mcp_result(
                            result, phoenix_trace_id, fallback_summary
                        )
                    if "get_trace" in tool_names:
                        result = await session.call_tool(
                            "get_trace", {"trace_id": phoenix_trace_id}
                        )
                        return _summarize_phoenix_mcp_result(
                            result, phoenix_trace_id, fallback_summary
                        )
                    if "get_trace_by_id" in tool_names:
                        result = await session.call_tool(
                            "get_trace_by_id", {"trace_id": phoenix_trace_id}
                        )
                        return _summarize_phoenix_mcp_result(
                            result, phoenix_trace_id, fallback_summary
                        )
        except Exception:
            return None
        return None


def _summarize_phoenix_mcp_result(
    result: Any, phoenix_trace_id: str, fallback_summary: str
) -> str:
    raw_text = _mcp_result_text(result)
    lower = raw_text.lower()
    signals = [
        name
        for name in [
            "fit_eval_run",
            "false_strong_recommendation",
            "weak_proxy_detected",
            "unsupported_implication",
            "schema_valid",
        ]
        if name in lower
    ]
    signal_text = ", ".join(signals) if signals else "trace data returned"
    excerpt = _compact(raw_text, max_chars=800)
    summary = (
        "Phoenix MCP inspected the failed trace. "
        f"trace_id={phoenix_trace_id}. "
        f"Signals found: {signal_text}. "
        f"Prior eval failure: {fallback_summary}. "
        f"Compact trace excerpt: {excerpt}"
    )
    return _compact(summary, max_chars=MAX_TRACE_SUMMARY_CHARS)


def _mcp_result_text(result: Any) -> str:
    content = getattr(result, "content", None)
    if content:
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            parts.append(text if text is not None else str(item))
        return "\n".join(parts)
    return str(result)


def _compact(text: str, *, max_chars: int) -> str:
    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars]}...[truncated]"
