from fastapi.testclient import TestClient

from app.main import app


def test_api_rejects_direct_trace_inspected_run():
    client = TestClient(app)

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
    client = TestClient(app)

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
