from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.ledger import LedgerStore

mcp = FastMCP("market-fit-ledger")
store = LedgerStore()


@mcp.tool()
def propose_claim(
    run_id: str,
    source_id: str,
    claim_text: str,
    entities: list[str],
    horizon: str,
    stance: str,
    confidence: float,
    reasoning_summary: str,
) -> dict[str, str]:
    return store.propose_claim(
        run_id=run_id,
        source_id=source_id,
        claim_text=claim_text,
        entities=entities,
        horizon=horizon,
        stance=stance,
        confidence=confidence,
        reasoning_summary=reasoning_summary,
    )


@mcp.tool()
def attach_market_fit(
    claim_id: str,
    recommended_market_id: str | None,
    semantic_fit_class: str,
    fit_reason: str,
    captures: list[str],
    misses: list[str],
    rejected_markets: list[dict[str, Any]],
) -> dict[str, str]:
    return store.attach_market_fit(
        claim_id=claim_id,
        recommended_market_id=recommended_market_id,
        semantic_fit_class=semantic_fit_class,
        fit_reason=fit_reason,
        captures=captures,
        misses=misses,
        rejected_markets=rejected_markets,
    )


@mcp.tool()
def record_eval_result(
    run_id: str,
    claim_id: str | None,
    phoenix_trace_id: str,
    metrics: dict[str, Any],
    failure_summary: str | None,
) -> dict[str, str]:
    return store.record_eval_result(
        run_id=run_id,
        claim_id=claim_id,
        phoenix_trace_id=phoenix_trace_id,
        metrics=metrics,
        failure_summary=failure_summary,
    )


@mcp.tool()
def record_human_verdict(
    claim_id: str,
    verdict: str,
    corrected_claim_text: str | None = None,
    corrected_fit_class: str | None = None,
    reviewer_note: str = "",
) -> dict[str, str]:
    return store.record_human_verdict(
        claim_id=claim_id,
        verdict=verdict,
        corrected_claim_text=corrected_claim_text,
        corrected_fit_class=corrected_fit_class,
        reviewer_note=reviewer_note,
    )


@mcp.tool()
def query_claim_trace(claim_id: str) -> dict[str, Any]:
    return store.query_claim_trace(claim_id).model_dump()


if __name__ == "__main__":
    mcp.run()

