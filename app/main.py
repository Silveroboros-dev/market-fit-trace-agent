from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import MarketFitTraceAgent, TraceInspectionUnavailableError
from app.candidate_review import (
    DEFAULT_CANDIDATES_DIR,
    build_review_decision,
    find_candidate_dir,
    load_candidate_review_detail,
    load_candidate_review_summary,
)
from app.candidate_triage import OUTPUT_NAME, triage_candidate_dir
from app.config import settings
from app.golden_replay import list_strict_golden_options, resolve_strict_golden_provider
from app.ledger import LedgerStore
from app.market_data import load_markets
from app.market_provider import PolyDataMarketProvider
from app.models import (
    CandidateReviewInput,
    CurrentRunCandidateInput,
    HumanVerdictInput,
    HumanVerdictResult,
    ImprovementResult,
    RunResult,
    SourceInput,
)
from app.run_candidates import export_current_run_candidate
from app.source_candidates import list_source_candidate_rows

store = LedgerStore()
agent = MarketFitTraceAgent(
    store=store,
    market_provider_resolver=resolve_strict_golden_provider,
)
app = FastAPI(title="Market Fit Trace Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "market-fit-trace-agent",
        "market_provider": settings.market_provider,
        "market_data_mode": (
            "polydata_live" if settings.market_provider == "polydata" else "fixture"
        ),
        "phoenix_mcp_enabled": settings.phoenix_mcp_enabled,
    }


@app.get("/api/markets")
def markets(
    mode: str = "fixture",
    top_k: int = Query(default=5, ge=1, le=50),
    min_volume_usd: float | None = Query(default=None, ge=0),
    l1: str | None = None,
) -> list[dict[str, object]]:
    if mode == "live":
        provider = PolyDataMarketProvider(
            settings_obj=replace(
                settings,
                market_provider="polydata",
                poly_data_top_k=top_k,
                poly_data_min_volume_usd=(
                    min_volume_usd
                    if min_volume_usd is not None
                    else settings.poly_data_min_volume_usd
                ),
                poly_data_l1_allowlist=tuple(
                    item.strip() for item in (l1 or "").split(",") if item.strip()
                )
                or settings.poly_data_l1_allowlist,
            )
        )
        return [market.model_dump() for market in provider.get_markets()]
    return [market.model_dump() for market in load_markets()]


@app.get("/api/strict-goldens")
def strict_goldens() -> dict[str, object]:
    goldens = list_strict_golden_options()
    return {
        "golden_count": len(goldens),
        "goldens": goldens,
    }


@app.get("/api/source-candidates")
def source_candidates() -> dict[str, object]:
    return list_source_candidate_rows()


@app.post("/api/runs", response_model=RunResult)
async def create_run(payload: SourceInput) -> RunResult:
    if payload.prompt_version != "v1_lenient":
        raise HTTPException(
            status_code=400,
            detail=(
                "Trace-inspected runs must be created through "
                "/api/runs/{run_id}/improve so Phoenix MCP supplies the prior trace context."
            ),
        )
    return await agent.run(
        thesis=payload.thesis,
        title=payload.title,
        prompt_version=payload.prompt_version,
    )


@app.post("/api/verdicts", response_model=HumanVerdictResult)
def record_verdict(payload: HumanVerdictInput) -> HumanVerdictResult:
    try:
        result = store.record_human_verdict(
            claim_id=payload.claim_id,
            verdict=payload.verdict,
            corrected_claim_text=payload.corrected_claim_text,
            corrected_fit_class=payload.corrected_fit_class,
            reviewer_note=payload.reviewer_note,
        )
        return HumanVerdictResult(
            verdict_id=result["verdict_id"],
            claim_status=result["claim_status"],
            ledger=store.query_claim_trace(payload.claim_id),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/ledger/{claim_id}")
def claim_trace(claim_id: str) -> dict[str, object]:
    try:
        return store.query_claim_trace(claim_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/retrieval-candidates")
def retrieval_candidates() -> dict[str, object]:
    return load_candidate_review_summary()


@app.get("/api/retrieval-candidates/{case_id}")
def retrieval_candidate(case_id: str) -> dict[str, object]:
    try:
        return load_candidate_review_detail(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown candidate: {case_id}") from exc


@app.post("/api/current-run-candidates")
def create_current_run_candidate(payload: CurrentRunCandidateInput) -> dict[str, object]:
    return export_current_run_candidate(
        source_text=payload.source_text,
        run=payload.run,
        case_id=payload.case_id,
        source_assisted=payload.source_assisted,
    )


@app.post("/api/retrieval-candidates/{case_id}/triage")
async def triage_retrieval_candidate(case_id: str) -> dict[str, object]:
    candidate_dir = find_candidate_dir(case_id, DEFAULT_CANDIDATES_DIR)
    if candidate_dir is None:
        raise HTTPException(status_code=404, detail=f"Unknown candidate: {case_id}")
    suggestion = await triage_candidate_dir(candidate_dir)
    (candidate_dir / OUTPUT_NAME).write_text(
        json.dumps(suggestion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return load_candidate_review_detail(case_id)


@app.post("/api/retrieval-candidates/{case_id}/review")
def review_retrieval_candidate(
    case_id: str, payload: CandidateReviewInput
) -> dict[str, object]:
    candidate_dir = find_candidate_dir(case_id, DEFAULT_CANDIDATES_DIR)
    if candidate_dir is None:
        raise HTTPException(status_code=404, detail=f"Unknown candidate: {case_id}")
    try:
        decision = build_review_decision(
            case_id=case_id,
            candidate_dir=candidate_dir,
            status=payload.status,
            note=payload.note,
            reviewer=payload.reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    (candidate_dir / "review_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return load_candidate_review_detail(case_id)


@app.post("/api/runs/{run_id}/improve", response_model=ImprovementResult)
async def improve_run(run_id: str) -> ImprovementResult:
    try:
        return await agent.improve_from_trace(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TraceInspectionUnavailableError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
