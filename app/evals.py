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
    trace_repair_gate_applied: bool = False,
    previous_trace_id: str | None = None,
    previous_failure_summary: str | None = None,
    inspection_source: str | None = None,
) -> EvalResult:
    market = _market_by_id(markets, fit.recommended_market_id)
    risks = set(market.known_fit_risks if market else [])
    weak_proxy_expected = any("weak_proxy" in risk for risk in risks)
    no_market_expected = fit.recommended_market_id is None
    strong_fit = fit.semantic_fit_class in STRONG_CLASSES
    false_strong = bool(weak_proxy_expected and strong_fit)
    causal_mismatch = _causal_mechanism_mismatch(
        claim, fit, market, weak_proxy_expected
    )
    resolution_target_mismatch = _resolution_target_mismatch(
        fit, market, weak_proxy_expected
    )
    horizon_mismatch = _horizon_mismatch(market)
    entity_mismatch = _entity_mismatch(market)
    unsupported = bool(
        false_strong
        or (
            strong_fit
            and (
                causal_mismatch
                or (_claim_mentions_cause(claim) and _fit_misses_cause(fit))
            )
        )
    )
    weak_proxy_detected = bool(fit.semantic_fit_class == FitClass.WEAK_PROXY)
    trace_repair_candidate = bool(
        strong_fit
        and (false_strong or unsupported)
        and (
            causal_mismatch
            or resolution_target_mismatch
            or horizon_mismatch
            or entity_mismatch
        )
    )

    metrics = EvalMetrics(
        schema_valid=bool(claim.claim_text and fit.fit_reason and fit.semantic_fit_class),
        false_strong_recommendation=false_strong,
        weak_proxy_detected=weak_proxy_detected,
        unsupported_implication=unsupported,
        human_verification_required=not human_verification_present,
        no_clean_expression_expected=no_market_expected,
        causal_mechanism_mismatch=causal_mismatch,
        resolution_target_mismatch=resolution_target_mismatch,
        horizon_mismatch=horizon_mismatch,
        entity_mismatch=entity_mismatch,
        trace_repair_candidate=trace_repair_candidate,
        trace_repair_gate_applied=trace_repair_gate_applied,
        previous_trace_id=previous_trace_id,
        previous_failure_summary=previous_failure_summary,
        inspection_source=inspection_source,
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
    mismatch_is_failure = bool(false_strong or unsupported)
    if mismatch_is_failure and strong_fit and causal_mismatch:
        failure_parts.append(
            "causal_mechanism_mismatch=true: the market can resolve for reasons "
            "unrelated to the thesis mechanism."
        )
    if mismatch_is_failure and strong_fit and resolution_target_mismatch:
        failure_parts.append(
            "resolution_target_mismatch=true: the market resolves on an adjacent "
            "target rather than the normalized thesis."
        )
    if mismatch_is_failure and strong_fit and horizon_mismatch:
        failure_parts.append(
            "horizon_mismatch=true: the market horizon differs from the normalized thesis."
        )
    if mismatch_is_failure and strong_fit and entity_mismatch:
        failure_parts.append(
            "entity_mismatch=true: the market entity differs from the normalized thesis."
        )
    if trace_repair_candidate:
        failure_parts.append(
            "trace_repair_candidate=true: Phoenix trace inspection can cap this "
            "strong fit to weak_proxy on rerun."
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
        and after.metrics.trace_repair_gate_applied
    )


def _market_by_id(markets: list[CandidateMarket], market_id: str | None) -> CandidateMarket | None:
    if market_id is None:
        return None
    for market in markets:
        if market.market_id == market_id:
            return market
    return None


def _claim_mentions_cause(claim: NormalizedClaim) -> bool:
    text = claim.claim_text.lower()
    tokens = ["mean", "because", "cause", "driven by", "due to"]
    return any(token in text for token in tokens)


def _fit_misses_cause(fit: MarketFit) -> bool:
    joined = " ".join([fit.fit_reason, *fit.misses]).lower()
    tokens = ["causal", "cause", "mechanism", "does not resolve", "not resolve"]
    return any(token in joined for token in tokens)


def _causal_mechanism_mismatch(
    claim: NormalizedClaim,
    fit: MarketFit,
    market: CandidateMarket | None,
    weak_proxy_expected: bool,
) -> bool:
    if market is None:
        return False
    risk_text = _risk_text(market)
    if "weak_proxy_for_causal" in risk_text:
        return True
    risk_signals = ("causal", "mechanism", "unrelated", "not_model_performance")
    if any(signal in risk_text for signal in risk_signals) and (
        weak_proxy_expected or _claim_mentions_cause(claim) or _fit_misses_cause(fit)
    ):
        return True
    return bool(_claim_mentions_cause(claim) and _fit_misses_cause(fit))


def _resolution_target_mismatch(
    fit: MarketFit, market: CandidateMarket | None, weak_proxy_expected: bool
) -> bool:
    if market is None:
        return False
    if not weak_proxy_expected and not fit.misses:
        return False
    risk_text = _risk_text(market)
    target_signals = (
        "wrong_market",
        "not_same_as",
        "does_not_measure",
        "does_not_express",
        "benchmark_market",
        "benchmark_not",
        "leaderboard_rank",
        "hardware_release_not_model_performance",
        "ipo_timing_not_valuation",
        "rate_threshold_not_same",
        "single_hyperscaler",
    )
    return any(signal in risk_text for signal in target_signals)


def _horizon_mismatch(market: CandidateMarket | None) -> bool:
    if market is None:
        return False
    risk_text = _risk_text(market)
    return any(signal in risk_text for signal in ("horizon", "wrong_date", "date_bucket"))


def _entity_mismatch(market: CandidateMarket | None) -> bool:
    if market is None:
        return False
    risk_text = _risk_text(market)
    return any(
        signal in risk_text
        for signal in ("wrong_entity", "wrong_platform", "entity_mismatch")
    )


def _risk_text(market: CandidateMarket) -> str:
    return " ".join(
        [
            market.title,
            market.description,
            market.resolution_rules,
            *market.known_fit_risks,
        ]
    ).lower()
