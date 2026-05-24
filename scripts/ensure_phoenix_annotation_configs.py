from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

CONFIGS: list[dict[str, Any]] = [
    {
        "name": "schema_valid",
        "type": "CATEGORICAL",
        "optimization_direction": "MAXIMIZE",
        "values": [{"label": "pass", "score": 1}, {"label": "fail", "score": 0}],
        "description": "Required claim and market-fit schema fields were present.",
    },
    {
        "name": "false_strong_recommendation",
        "type": "CATEGORICAL",
        "optimization_direction": "MAXIMIZE",
        "values": [{"label": "pass", "score": 1}, {"label": "fail", "score": 0}],
        "description": "Fails when a weak proxy is recommended as a strong market fit.",
    },
    {
        "name": "weak_proxy_detected",
        "type": "CATEGORICAL",
        "optimization_direction": "MAXIMIZE",
        "values": [{"label": "true", "score": 1}, {"label": "false", "score": 0}],
        "description": "The agent flagged a tempting but weak prediction-market proxy.",
    },
    {
        "name": "unsupported_implication",
        "type": "CATEGORICAL",
        "optimization_direction": "MAXIMIZE",
        "values": [{"label": "pass", "score": 1}, {"label": "fail", "score": 0}],
        "description": "Fails when the explanation implies unsupported causal resolution.",
    },
]


def main() -> int:
    if not settings.phoenix_base_url or not settings.phoenix_api_key:
        print(
            json.dumps(
                {
                    "status": "missing_config",
                    "required": ["PHOENIX_BASE_URL", "PHOENIX_API_KEY"],
                },
                indent=2,
            )
        )
        return 2

    existing_payload = request("GET", "/v1/annotation_configs")
    existing = {item.get("name") for item in existing_payload.get("data", [])}
    created: list[str] = []
    skipped: list[str] = []

    for config in CONFIGS:
        if config["name"] in existing:
            skipped.append(config["name"])
            continue
        request("POST", "/v1/annotation_configs", config)
        created.append(config["name"])

    print(
        json.dumps(
            {
                "status": "ok",
                "created": created,
                "skipped_existing": skipped,
                "configured": sorted(existing | {item["name"] for item in CONFIGS}),
            },
            indent=2,
        )
    )
    return 0


def request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{settings.phoenix_base_url.rstrip('/')}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {settings.phoenix_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Phoenix API {method} {path} failed: {exc.code} {detail}") from exc


if __name__ == "__main__":
    sys.exit(main())
