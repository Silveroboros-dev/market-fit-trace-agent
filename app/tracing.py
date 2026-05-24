from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import settings

try:
    from opentelemetry import trace as trace_api
    from opentelemetry.trace import Span
except Exception:  # pragma: no cover - optional tracing dependency
    trace_api = None
    Span = object  # type: ignore[assignment]


_TRACING_READY = False
_TRACER_PROVIDER: Any | None = None


def _safe_attr(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, str | int | float | bool):
        return value
    return json.dumps(value, sort_keys=True)


def setup_tracing() -> None:
    global _TRACER_PROVIDER, _TRACING_READY
    if _TRACING_READY:
        return
    if settings.phoenix_api_key and settings.phoenix_collector_endpoint:
        if os.environ.get("PHOENIX_ADK_TRACING_READY", "").lower() == "true":
            _TRACING_READY = True
            return
    if not (settings.phoenix_collector_endpoint or settings.phoenix_api_key):
        _TRACING_READY = True
        return
    try:
        from phoenix.otel import register

        kwargs: dict[str, Any] = {
            "project_name": settings.phoenix_project_name,
            "auto_instrument": True,
            "batch": False,
        }
        if settings.phoenix_isolated_tracer_provider:
            kwargs["set_global_tracer_provider"] = False
        if settings.phoenix_api_key:
            kwargs["api_key"] = settings.phoenix_api_key
        _TRACER_PROVIDER = register(**kwargs)
        os.environ["PHOENIX_APP_TRACING_READY"] = "true"
    except Exception:
        # Local development should still run without Phoenix credentials or collector access.
        pass
    _TRACING_READY = True


class TraceContext:
    def __init__(self) -> None:
        setup_tracing()
        self._tracer = _get_tracer()
        self.local_trace_id = f"local-{uuid.uuid4().hex}"
        self.root_trace_id: str | None = None
        self.span_ids: dict[str, str] = {}

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
        if not self._tracer:
            yield
            return
        with self._tracer.start_as_current_span(name) as span:
            self._set_attributes(span, attributes or {})
            context = span.get_span_context()
            if context and context.is_valid:
                trace_id = format(context.trace_id, "032x")
                self.root_trace_id = self.root_trace_id or trace_id
                self.span_ids[name] = format(context.span_id, "016x")
            yield

    def trace_id(self) -> str:
        return self.root_trace_id or self.local_trace_id

    def span_id(self, name: str) -> str | None:
        return self.span_ids.get(name)

    def set_current_span_attributes(self, attributes: dict[str, Any]) -> None:
        if not trace_api:
            return
        span = trace_api.get_current_span()
        if not span:
            return
        self._set_attributes(span, attributes)

    @staticmethod
    def _set_attributes(span: Span, attributes: dict[str, Any]) -> None:
        for key, value in attributes.items():
            try:
                span.set_attribute(key, _safe_attr(value))
            except Exception:
                span.set_attribute(key, str(value))


def _get_tracer() -> Any | None:
    if _TRACER_PROVIDER:
        return _TRACER_PROVIDER.get_tracer(__name__)
    return trace_api.get_tracer(__name__) if trace_api else None
