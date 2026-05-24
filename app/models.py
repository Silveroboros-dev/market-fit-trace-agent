from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FitClass(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    WEAK_PROXY = "weak_proxy"
    NO_CLEAN_EXPRESSION = "no_clean_expression"


class HumanVerdict(StrEnum):
    VERIFY = "verify"
    REJECT = "reject"
    NEEDS_REVIEW = "needs_review"
    CORRECTED = "corrected"


class SourceInput(BaseModel):
    thesis: str = Field(min_length=8)
    title: str | None = None
    prompt_version: str = "v1_lenient"


class NormalizedClaim(BaseModel):
    claim_text: str
    entities: list[str] = Field(default_factory=list)
    horizon: str = "unspecified"
    stance: str = "unspecified"
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    reasoning_summary: str = ""


class CandidateMarket(BaseModel):
    market_id: str
    title: str
    venue: str
    description: str
    resolution_rules: str
    close_date: str
    outcomes: list[str]
    current_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    known_fit_risks: list[str] = Field(default_factory=list)
    entity_tags: list[str] = Field(default_factory=list)


class RejectedMarket(BaseModel):
    market_id: str
    reason: str


class MarketFit(BaseModel):
    recommended_market_id: str | None
    semantic_fit_class: FitClass
    fit_reason: str
    captures: list[str] = Field(default_factory=list)
    misses: list[str] = Field(default_factory=list)
    rejected_markets: list[RejectedMarket] = Field(default_factory=list)


class EvalMetrics(BaseModel):
    schema_valid: bool
    false_strong_recommendation: bool
    weak_proxy_detected: bool
    unsupported_implication: bool
    human_verification_required: bool
    no_clean_expression_expected: bool = False
    second_run_improvement: bool | None = None


class EvalResult(BaseModel):
    eval_record_id: str | None = None
    phoenix_trace_id: str
    metrics: EvalMetrics
    failure_summary: str | None = None


class LedgerEvent(BaseModel):
    event_type: str
    created_at: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ClaimTrace(BaseModel):
    claim_id: str
    status: str
    events: list[LedgerEvent]


class RunResult(BaseModel):
    run_id: str
    source_id: str
    claim_id: str
    phoenix_trace_id: str
    phoenix_trace_url: str | None = None
    model: str
    prompt_version: str
    claim: NormalizedClaim
    fit: MarketFit
    eval: EvalResult
    ledger: ClaimTrace


class HumanVerdictInput(BaseModel):
    claim_id: str
    verdict: HumanVerdict
    corrected_claim_text: str | None = None
    corrected_fit_class: FitClass | None = None
    reviewer_note: str = ""


class HumanVerdictResult(BaseModel):
    verdict_id: str
    claim_status: str
    ledger: ClaimTrace


class ImprovementRequest(BaseModel):
    run_id: str


class PhoenixInspection(BaseModel):
    run_id: str
    phoenix_trace_id: str
    source: str
    fallback_used: bool
    summary: str
    recommended_prompt_version: str
    mcp_configured: bool


class ImprovementResult(BaseModel):
    before_run_id: str
    after_run_id: str
    before_trace_id: str
    after_trace_id: str
    inspection_source: str
    fallback_used: bool
    before_fit: FitClass
    after_fit: FitClass
    false_strong_recommendation_before: bool
    false_strong_recommendation_after: bool
    inspection: PhoenixInspection
    before: RunResult
    after: RunResult


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
