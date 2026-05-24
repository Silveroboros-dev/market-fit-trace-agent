from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Market Fit Trace Agent"
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    google_adk_enabled: bool = os.getenv("GOOGLE_ADK_ENABLED", "true").lower() == "true"
    google_genai_use_vertexai: bool = (
        os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    )
    google_cloud_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str | None = os.getenv("GOOGLE_CLOUD_LOCATION")
    phoenix_project_name: str = os.getenv("PHOENIX_PROJECT_NAME", "market_fit_trace_agent")
    phoenix_collector_endpoint: str | None = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    phoenix_base_url: str | None = os.getenv("PHOENIX_BASE_URL")
    phoenix_api_key: str | None = os.getenv("PHOENIX_API_KEY")
    phoenix_isolated_tracer_provider: bool = (
        os.getenv("PHOENIX_ISOLATED_TRACER_PROVIDER", "").lower() == "true"
    )
    phoenix_mcp_enabled: bool = os.getenv("PHOENIX_MCP_ENABLED", "").lower() == "true"
    phoenix_mcp_command: str = os.getenv("PHOENIX_MCP_COMMAND", "npx")
    phoenix_mcp_args: tuple[str, ...] = tuple(
        part
        for part in os.getenv("PHOENIX_MCP_ARGS", "-y,@arizeai/phoenix-mcp@latest").split(
            ","
        )
        if part
    )
    ledger_store_path: Path = Path(os.getenv("LEDGER_STORE_PATH", ".local/ledger_store.json"))
    market_data_path: Path = Path(os.getenv("MARKET_DATA_PATH", "app/data/seed_markets.json"))

    @property
    def vertex_configured(self) -> bool:
        return bool(
            self.google_genai_use_vertexai
            and self.google_cloud_project
            and self.google_cloud_location
        )

    @property
    def adk_configured(self) -> bool:
        return bool(self.google_adk_enabled and (self.google_api_key or self.vertex_configured))


settings = Settings()
