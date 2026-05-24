from __future__ import annotations

from app.config import settings
from app.ledger import LedgerStore
from app.models import PhoenixInspection


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
                        return (
                            "Phoenix MCP returned trace data. "
                            f"Eval failure: {fallback_summary} Details: {result}"
                        )
                    if "get_trace" in tool_names:
                        result = await session.call_tool(
                            "get_trace", {"trace_id": phoenix_trace_id}
                        )
                        return (
                            "Phoenix MCP returned trace data. "
                            f"Eval failure: {fallback_summary} Details: {result}"
                        )
                    if "get_trace_by_id" in tool_names:
                        result = await session.call_tool(
                            "get_trace_by_id", {"trace_id": phoenix_trace_id}
                        )
                        return (
                            "Phoenix MCP returned trace data. "
                            f"Eval failure: {fallback_summary} Details: {result}"
                        )
        except Exception:
            return None
        return None
