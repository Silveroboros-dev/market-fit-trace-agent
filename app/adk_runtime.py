from __future__ import annotations

import uuid
from typing import Any

from app.config import settings
from app.json_utils import extract_json


class ADKJsonRuntime:
    """Google ADK runner for JSON proposal calls.

    The deployable ADK agent is defined as ``market_fit_adk.agent.root_agent``.
    The product layer still validates schemas and applies deterministic market-fit/eval
    policy after the model proposes structured output.
    """

    def __init__(self, *, model: str | None = None) -> None:
        self.model = model or settings.gemini_model
        self.runtime_name = f"google-adk:{self.model}"

    @property
    def available(self) -> bool:
        return settings.adk_configured and self._imports_available()

    async def generate_json(
        self,
        *,
        prompt: str,
        task_name: str,
        instruction: str,
    ) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            from google.adk.runners import InMemoryRunner
            from google.genai import types

            from market_fit_adk.agent import root_agent
        except Exception:
            return None

        try:
            app_name = "market_fit_trace_agent"
            user_id = "local_user"
            session_id = f"{_safe_agent_name(task_name)}_{uuid.uuid4().hex[:12]}"
            runner = InMemoryRunner(agent=root_agent, app_name=app_name)
            await runner.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
            task_prompt = f"""
Task name: {task_name}
Task instruction:
{instruction}

User/task payload:
{prompt}
"""
            final_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=task_prompt)],
                ),
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = "".join(
                        getattr(part, "text", "") or "" for part in event.content.parts
                    ).strip()
            return extract_json(final_text)
        except Exception:
            return None

    @staticmethod
    def _imports_available() -> bool:
        try:
            from market_fit_adk.agent import root_agent

            return bool(root_agent.name)
        except Exception:
            return False


def _safe_agent_name(task_name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char == "_" else "_" for char in task_name)
    return cleaned.strip("_")[:40] or "market_fit_json_agent"
