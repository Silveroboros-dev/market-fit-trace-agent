from __future__ import annotations

from app.models import (
    CandidateMarket,
    EvalMetrics,
    EvalResult,
    FitClass,
    MarketFit,
    NormalizedClaim,
)

STRONG_CLASSES = {FitClass.DIRECT, FitClass.INDIRECT}


def evaluate_fit(
    *,
    claim: NormalizedClaim,
    fit: MarketFit,
    markets: list[CandidateMarket],
    phoenix_trace_id: str,
    human_verification_present: bool = False,
) -> EvalResult:
    market = _market_by_id(markets, fit.recommended_market_id)
    risks = set(market.known_fit_risks if market else [])
    weak_proxy_expected = any("weak_proxy" in risk for risk in risks)
    no_market_expected = fit.recommended_market_id is None
    strong_fit = fit.semantic_fit_class in STRONG_CLASSES
    false_strong = bool(weak_proxy_expected and strong_fit)
    unsupported = bool(
        false_strong
        or (strong_fit and _claim_mentions_cause(claim) and _fit_misses_cause(fit))
    )
    weak_proxy_detected = bool(
        weak_proxy_expected and fit.semantic_fit_class == FitClass.WEAK_PROXY
    )

    metrics = EvalMetrics(
        schema_valid=bool(claim.claim_text and fit.fit_reason and fit.semantic_fit_class),
        false_strong_recommendation=false_strong,
        weak_proxy_detected=weak_proxy_detected,
        unsupported_implication=unsupported,
        human_verification_required=not human_verification_present,
        no_clean_expression_expected=no_market_expected,
    )
    failure_parts: list[str] = []
    if false_strong:
        failure_parts.append(
            "Recommended market is only a weak proxy but the fit was classified too strongly."
        )
    if unsupported:
        failure_parts.append(
            "Explanation risks implying the market resolves the underlying causal thesis."
        )
    if not metrics.schema_valid:
        failure_parts.append("Agent output failed required schema fields.")
    failure_summary = " ".join(failure_parts) or None
    return EvalResult(
        phoenix_trace_id=phoenix_trace_id,
        metrics=metrics,
        failure_summary=failure_summary,
    )


def evaluate_improvement(before: EvalResult, after: EvalResult) -> bool:
    return bool(
        before.metrics.false_strong_recommendation
        and not after.metrics.false_strong_recommendation
        and after.metrics.weak_proxy_detected
    )


def _market_by_id(markets: list[CandidateMarket], market_id: str | None) -> CandidateMarket | None:
    if market_id is None:
        return None
    for market in markets:
        if market.market_id == market_id:
            return market
    return None


def _claim_mentions_cause(claim: NormalizedClaim) -> bool:
    text = f"{claim.claim_text} {claim.reasoning_summary}".lower()
    tokens = ["mean", "because", "cause", "driven by", "due to", "tpu"]
    return any(token in text for token in tokens)


def _fit_misses_cause(fit: MarketFit) -> bool:
    joined = " ".join([fit.fit_reason, *fit.misses]).lower()
    tokens = ["causal", "cause", "tpu", "mechanism", "does not resolve"]
    return any(token in joined for token in tokens)
