from fastapi.testclient import TestClient

import app.main as main_module
from app.agent import MarketFitTraceAgent
from app.ledger import LedgerStore
from app.models import PhoenixInspection


class OfflineADKRuntime:
    runtime_name = "offline-test-runtime"

    async def generate_json(self, **_kwargs):
        return None


class FallbackInspector:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    async def inspect_failed_run(self, run_id: str) -> PhoenixInspection:
        run = self.store.get_run(run_id)
        return PhoenixInspection(
            run_id=run_id,
            phoenix_trace_id=run["phoenix_trace_id"],
            source="local_eval_fallback",
            fallback_used=True,
            summary="local fallback should not drive the normal UI repair path",
            recommended_prompt_version="v2_trace_inspected",
            mcp_configured=False,
        )


def test_api_rejects_direct_trace_inspected_run():
    client = TestClient(main_module.app)

    response = client.post(
        "/api/runs",
        json={
            "thesis": "Google TPU progress means Gemini closes the frontier-model gap in 2026.",
            "prompt_version": "v2_trace_inspected",
        },
    )

    assert response.status_code == 400
    assert "Phoenix MCP" in response.json()["detail"]


def test_source_candidates_endpoint_exposes_source_assisted_rows_without_truth_labels():
    client = TestClient(main_module.app)

    response = client.get("/api/source-candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_candidate_count"] == 30
    assert payload["canonical_truth"] is False
    row = payload["rows"][0]
    assert row["source_case_key"]
    assert row["source_text"]
    assert row["source_provenance"]
    assert row["source_truth_scope"] == "source_text_and_provenance_only"
    assert row["strict_expected_labels_present"] is False


def test_api_rejects_trace_improve_when_phoenix_mcp_falls_back(
    monkeypatch, tmp_path
):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(
        store=store,
        adk_runtime=OfflineADKRuntime(),
        phoenix_inspector_factory=FallbackInspector,
    )
    monkeypatch.setattr(main_module, "agent", agent)
    client = TestClient(main_module.app)

    first = client.post(
        "/api/runs",
        json={
            "thesis": "Google TPU progress means Gemini closes the frontier-model gap in 2026.",
            "prompt_version": "v1_lenient",
        },
    )
    assert first.status_code == 200

    response = client.post(f"/api/runs/{first.json()['run_id']}/improve")

    assert response.status_code == 424
    assert "Phoenix MCP inspection is unavailable" in response.json()["detail"]
