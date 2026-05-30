from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import MarketFitTraceAgent
from app.candidate_review import (
    load_candidate_review_detail,
    load_candidate_review_summary,
)
from app.config import settings
from app.golden_replay import list_strict_golden_options, resolve_strict_golden_provider
from app.ledger import LedgerStore
from app.market_data import load_markets
from app.market_provider import PolyDataMarketProvider
from app.models import (
    HumanVerdictInput,
    HumanVerdictResult,
    ImprovementResult,
    RunResult,
    SourceInput,
)

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
def health() -> dict[str, str]:
    return {"status": "ok", "service": "market-fit-trace-agent"}


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


@app.post("/api/runs", response_model=RunResult)
async def create_run(payload: SourceInput) -> RunResult:
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


@app.post("/api/runs/{run_id}/improve", response_model=ImprovementResult)
async def improve_run(run_id: str) -> ImprovementResult:
    try:
        return await agent.improve_from_trace(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
