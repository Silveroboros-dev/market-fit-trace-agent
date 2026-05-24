from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any

from app.config import settings

REQUIRED_SPANS = ("fit_eval_run",)
REQUIRED_ANNOTATIONS = (
    "schema_valid",
    "false_strong_recommendation",
    "weak_proxy_detected",
    "unsupported_implication",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Phoenix Cloud trace, eval annotations, and eval note visibility."
    )
    parser.add_argument("--trace-id", help="Trace ID to inspect. Defaults to latest trace.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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

    configs = request("GET", "/v1/annotation_configs").get("data", [])
    project = urllib.parse.quote(settings.phoenix_project_name, safe="")
    traces = request("GET", f"/v1/projects/{project}/traces?limit=10&include_spans=true").get(
        "data", []
    )
    trace = _select_trace(traces, args.trace_id)
    if not trace:
        print(
            json.dumps(
                {
                    "status": "trace_not_found",
                    "requested_trace_id": args.trace_id,
                    "recent_trace_ids": [item.get("trace_id") for item in traces],
                },
                indent=2,
            )
        )
        return 1

    spans = trace.get("spans", [])
    span_names = [span.get("name") for span in spans]
    missing_spans = [name for name in REQUIRED_SPANS if name not in span_names]
    fit_span = next((span for span in spans if span.get("name") == "fit_eval_run"), None)
    if not fit_span:
        print(
            json.dumps(
                {
                    "status": "missing_fit_eval_span",
                    "trace_id": trace.get("trace_id"),
                    "trace_found": True,
                    "span_names": span_names,
                    "required_spans_found": [
                        name for name in REQUIRED_SPANS if name in span_names
                    ],
                    "required_spans_missing": missing_spans,
                },
                indent=2,
            )
        )
        return 1

    annotations = request(
        "GET",
        f"/v1/projects/{project}/span_annotations?span_ids={fit_span['span_id']}&limit=100",
    ).get("data", [])
    annotation_names = [item.get("name") for item in annotations]
    config_names = [item.get("name") for item in configs]
    missing_annotation_configs = [
        name for name in REQUIRED_ANNOTATIONS if name not in config_names
    ]
    missing_fit_eval_annotations = [
        name for name in REQUIRED_ANNOTATIONS if name not in annotation_names
    ]
    status = (
        "ok"
        if not missing_annotation_configs and not missing_fit_eval_annotations
        else "missing_required_annotations"
    )
    print(
        json.dumps(
            {
                "status": status,
                "project": settings.phoenix_project_name,
                "trace_id": trace.get("trace_id"),
                "phoenix_trace_url": (
                    f"{settings.phoenix_base_url.rstrip('/')}/traces/{trace.get('trace_id')}"
                ),
                "trace_found": True,
                "span_count": len(trace.get("spans", [])),
                "fit_eval_span_id": fit_span.get("span_id"),
                "required_spans_found": [
                    name for name in REQUIRED_SPANS if name in span_names
                ],
                "required_spans_missing": missing_spans,
                "required_annotations_found": [
                    name for name in REQUIRED_ANNOTATIONS if name in annotation_names
                ],
                "required_annotations_missing": missing_fit_eval_annotations,
                "required_annotation_configs_found": [
                    name for name in REQUIRED_ANNOTATIONS if name in config_names
                ],
                "required_annotation_configs_missing": missing_annotation_configs,
                "annotation_configs": config_names,
                "fit_eval_annotations": [
                    {"name": item.get("name"), "result": item.get("result")}
                    for item in annotations
                ],
            },
            indent=2,
        )
    )
    return 0 if status == "ok" else 1


def request(method: str, path: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{settings.phoenix_base_url.rstrip('/')}{path}",
        headers={
            "Authorization": f"Bearer {settings.phoenix_api_key}",
            "Accept": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _select_trace(traces: list[dict[str, Any]], trace_id: str | None) -> dict[str, Any] | None:
    if trace_id:
        return next((item for item in traces if item.get("trace_id") == trace_id), None)
    return next(
        (
            item
            for item in traces
            if any(span.get("name") == "fit_eval_run" for span in item.get("spans", []))
        ),
        traces[0] if traces else None,
    )


if __name__ == "__main__":
    sys.exit(main())
