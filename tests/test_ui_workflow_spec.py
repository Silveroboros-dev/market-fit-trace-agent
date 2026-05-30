from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "ui-workflow-spec.md"
APP_JS = ROOT / "app" / "static" / "app.js"
INDEX_HTML = ROOT / "app" / "static" / "index.html"


def test_ui_workflow_spec_defines_state_binding_acceptance_criteria():
    spec = SPEC.read_text(encoding="utf-8")

    for criterion in (
        "AC-1",
        "AC-2",
        "AC-3",
        "AC-4",
        "AC-5",
        "AC-6",
        "AC-7",
        "AC-8",
        "AC-9",
        "AC-10",
    ):
        assert criterion in spec
    assert "current run is identified by `run_id`" in spec
    assert "candidate packet is identified by `case_id`" in spec
    assert "must not silently map a current run to the first available candidate" in spec
    assert "candidate triage is unavailable for this run" in spec
    assert "Run-Scoped Eval Metrics" in spec
    assert "Dataset-wide and independent from the active run" in spec
    assert "Exact Golden Replay Uses Frozen Fixture Context" in spec
    assert "Strict Golden Loader Is Manual" in spec


def test_current_run_ui_does_not_open_existing_candidate_triage():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "Candidate triage unavailable for this run" in app_js
    assert "Browse existing candidate packets" in app_js
    assert "data-scroll-candidate-queue" in app_js
    assert "Yes, show triage" not in app_js
    assert "data-scroll-candidate-workflow" not in app_js

    bind_run_governance = app_js.split("function bindRunGovernance()", 1)[1].split(
        "function bindVerdicts()", 1
    )[0]
    assert 'state.workflow.screen = "triage"' not in bind_run_governance
    assert "setTriageDecision" not in bind_run_governance


def test_candidate_queue_requires_explicit_case_selection():
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert "Existing candidate packets" in index_html
    assert "Select a candidate packet to inspect its triage and review artifacts." in app_js
    assert '<option value="">Select packet</option>' in app_js
    assert "state.selectedCandidateId = rows[0].case_id" not in app_js
    assert "await loadCandidateDetail(state.selectedCandidateId)" in app_js


def test_strict_golden_loader_fills_source_without_auto_run():
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert "Load strict golden" in index_html
    assert "strict-golden-select" in index_html
    assert "strict-golden-note" in index_html
    assert 'api("/api/strict-goldens")' in app_js
    assert "Exact golden source loaded" in app_js
    assert "Edited text may leave golden replay mode" in app_js

    strict_golden_handler = app_js.split(
        'strictGoldenSelectEl.addEventListener("change"', 1
    )[1].split('thesisEl.addEventListener("input"', 1)[0]
    assert "/api/runs" not in strict_golden_handler
    assert "setTriageDecision" not in strict_golden_handler
    assert "setReviewDecision" not in strict_golden_handler


def test_current_run_clears_stale_candidate_selection_and_scopes_eval_metrics():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "function beginCurrentRun()" in app_js
    assert "function clearCandidateSelectionForRun()" in app_js
    assert "state.selectedCandidateId = null" in app_js
    assert 'candidateSelectEl.value = ""' in app_js

    submit_handler = app_js.split(
        'document.querySelector("#run-form").addEventListener("submit"', 1
    )[1].split('improveButton.addEventListener("click"', 1)[0]
    assert "beginCurrentRun();" in submit_handler

    improve_handler = app_js.split('improveButton.addEventListener("click"', 1)[1].split(
        'candidateSelectEl.addEventListener("change"', 1
    )[0]
    assert "clearCandidateSelectionForRun();" in improve_handler

    render_eval = app_js.split("function renderEval(run)", 1)[1].split(
        "function renderLedger", 1
    )[0]
    assert "Current run Phoenix eval" in render_eval
    assert 'meta("Run ID", run.run_id)' in render_eval
    assert 'meta("Trace ID", run.phoenix_trace_id)' in render_eval
    assert 'meta("Prompt", run.prompt_version)' in render_eval
    assert 'meta("Fit", run.fit.semantic_fit_class)' in render_eval


def test_candidate_dataset_totals_are_labeled_global():
    app_js = APP_JS.read_text(encoding="utf-8")

    render_candidate_stats = app_js.split("function renderCandidateStats(summary)", 1)[
        1
    ].split("function datasetLink", 1)[0]
    assert "Phoenix candidate Dataset totals" in render_candidate_stats
    assert "independent of the active run" in render_candidate_stats
    assert 'candidateStat("Dataset version"' in render_candidate_stats
    assert 'candidateStat("Dataset rows"' in render_candidate_stats
    assert 'candidateStat("Human promote"' in render_candidate_stats
    assert 'candidateStat("Human reject"' in render_candidate_stats


def test_current_run_market_rows_are_rendered_before_recommended_market_details():
    app_js = APP_JS.read_text(encoding="utf-8")
    render_run = app_js.split("function renderRun(run)", 1)[1].split(
        "function renderImprovement", 1
    )[0]

    assert "${retrievedMarketContext(run)}" in render_run
    assert "${recommendedMarket(run)}" in render_run
    assert render_run.index("${retrievedMarketContext(run)}") < render_run.index(
        "${recommendedMarket(run)}"
    )
    assert "Found relevant markets" in app_js
