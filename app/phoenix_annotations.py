from __future__ import annotations

from app.config import settings
from app.models import EvalResult


def log_eval_annotations(*, span_id: str | None, eval_result: EvalResult) -> bool:
    if not span_id or not settings.phoenix_api_key:
        return False
    try:
        from phoenix.client import Client
        from phoenix.client.resources.spans import SpanAnnotationData
    except Exception:
        return False

    annotations = [
        _annotation(
            SpanAnnotationData,
            span_id=span_id,
            name="schema_valid",
            label="pass" if eval_result.metrics.schema_valid else "fail",
            score=1.0 if eval_result.metrics.schema_valid else 0.0,
            metadata={"category": "market_fit_eval"},
        ),
        _annotation(
            SpanAnnotationData,
            span_id=span_id,
            name="false_strong_recommendation",
            label="fail" if eval_result.metrics.false_strong_recommendation else "pass",
            score=0.0 if eval_result.metrics.false_strong_recommendation else 1.0,
            metadata={"category": "market_fit_eval"},
        ),
        _annotation(
            SpanAnnotationData,
            span_id=span_id,
            name="weak_proxy_detected",
            label=str(eval_result.metrics.weak_proxy_detected).lower(),
            score=1.0 if eval_result.metrics.weak_proxy_detected else 0.0,
            metadata={"category": "market_fit_eval"},
        ),
        _annotation(
            SpanAnnotationData,
            span_id=span_id,
            name="unsupported_implication",
            label="fail" if eval_result.metrics.unsupported_implication else "pass",
            score=0.0 if eval_result.metrics.unsupported_implication else 1.0,
            metadata={
                "category": "market_fit_eval",
                "failure_summary": eval_result.failure_summary or "",
            },
        ),
    ]
    client = Client(base_url=settings.phoenix_base_url, api_key=settings.phoenix_api_key)
    try:
        client.spans.log_span_annotations(span_annotations=annotations, sync=True)
        client.spans.add_span_note(
            span_id=span_id,
            note=(
                "Market-fit eval: "
                f"schema_valid={eval_result.metrics.schema_valid}; "
                "false_strong_recommendation="
                f"{eval_result.metrics.false_strong_recommendation}; "
                f"weak_proxy_detected={eval_result.metrics.weak_proxy_detected}; "
                "unsupported_implication="
                f"{eval_result.metrics.unsupported_implication}; "
                f"failure_summary={eval_result.failure_summary or 'none'}"
            ),
        )
    except Exception:
        return False
    return True


def _annotation(
    span_annotation_cls: type,
    *,
    span_id: str,
    name: str,
    label: str,
    score: float,
    metadata: dict[str, str],
):
    return span_annotation_cls(
        name=name,
        span_id=span_id,
        annotator_kind="CODE",
        result={"label": label, "score": score},
        metadata=metadata,
    )
