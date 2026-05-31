from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "ui-workflow-spec.md"
APP_JS = ROOT / "app" / "static" / "app.js"
INDEX_HTML = ROOT / "app" / "static" / "index.html"


def test_ui_workflow_spec_defines_state_binding_acceptance_criteria():
    spec = SPEC.read_text(encoding="utf-8")
    spec_inline = " ".join(spec.split())

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
        "AC-11",
        "AC-12",
        "AC-13",
        "AC-14",
        "AC-15",
        "AC-16",
        "AC-17",
        "AC-18",
        "AC-19",
        "AC-20",
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
    assert "Trace-Inspected Runs Require Phoenix Inspection" in spec
    assert "Current Run Can Create Advisory Candidate Triage" in spec
    assert "LLM Triage Includes Market Ranking Scores" in spec
    assert "Human Promotion Review Target Is Explicit" in spec
    assert "Source-Assisted Candidate Loader Preserves Truth Boundary" in spec
    assert "Missing Phoenix MCP Is a Visible Failed Dependency" in spec
    assert "Candidate Review Console Requires Explicit Review Yes" in spec
    assert "Current-Run Reviewer Notes Are Read-Only Drafts" in spec
    assert "Inverse Direct Markets Show Supporting Outcome" in spec
    assert "must not silently use `local_eval_fallback`" in spec_inline
    assert "must not call `/api/verdicts`" in spec
    assert "source_case_key" in spec


def test_current_run_ui_does_not_open_existing_candidate_triage():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "Run LLM triage suggestion?" in app_js
    assert "data-create-run-triage" in app_js
    assert "llm_review_suggestion.json with market ranking scores" in app_js
    assert "Yes, show triage" not in app_js
    assert "data-scroll-candidate-workflow" not in app_js

    bind_run_governance = app_js.split("function bindRunGovernance()", 1)[1].split(
        "async function createCandidateFromCurrentRun", 1
    )[0]
    assert 'state.workflow.screen = "triage"' not in bind_run_governance
    assert "setTriageDecision" not in bind_run_governance
    assert "/api/current-run-candidates" in app_js


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


def test_source_assisted_loader_fills_source_without_auto_run_or_truth_claim():
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert "Load source-assisted candidate" in index_html
    assert "source-candidate-select" in index_html
    assert "source-candidate-note" in index_html
    assert 'api("/api/source-candidates")' in app_js
    assert "Source-assisted row loaded" in app_js
    assert "source_text_and_provenance_only" in app_js
    assert "proposed fit labels are advisory" in index_html
    assert "source_assisted: currentSourceAssistedRef()" in app_js

    source_candidate_handler = app_js.split(
        'sourceCandidateSelectEl.addEventListener("change"', 1
    )[1].split('thesisEl.addEventListener("input"', 1)[0]
    assert "/api/runs" not in source_candidate_handler
    assert "setTriageDecision" not in source_candidate_handler
    assert "setReviewDecision" not in source_candidate_handler


def test_trace_inspected_mode_is_not_directly_selectable():
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'value="v1_lenient"' in index_html
    assert "Trace-inspected reruns use Phoenix MCP" in index_html
    assert '<option value="v2_trace_inspected">' not in index_html
    assert 'document.querySelector("#prompt-version").value' in app_js
    assert "parsed.detail" in app_js


def test_current_run_clears_stale_candidate_selection_and_scopes_eval_metrics():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "function beginCurrentRun()" in app_js
    assert "function clearCandidateSelectionForRun()" in app_js
    assert "state.selectedCandidateId = null" in app_js
    assert "state.activeRunCandidateId = null" in app_js
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
    assert 'meta("Previous trace", metrics.previous_trace_id)' in render_eval
    assert 'metric("Causal mismatch", metrics.causal_mechanism_mismatch, true)' in render_eval
    assert (
        'metric("Repair gate", metrics.trace_repair_gate_applied)' in render_eval
    )


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
    assert "Retrieved candidate markets" in app_js
    assert 'meta("Supporting outcome", run.fit.supporting_outcome)' in app_js
    assert 'meta("Polarity", statusLabel(run.fit.polarity))' in app_js


def test_candidate_packet_views_show_eval_trace_and_review_target():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "Initial source text" in app_js
    assert "Normalized thesis" in app_js
    assert "Eval trace" in app_js
    assert "False strong" in app_js
    assert "Promote means eligible for later frozen strict-golden promotion" in app_js
    assert "No strict expected labels are written here" in app_js


def test_candidate_triage_market_scores_are_rendered_as_advisory_rankings():
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "market_scores" in app_js
    assert "review_score" in app_js
    assert "score ${score}" in app_js
    assert "currentRunScoreById" in app_js
    assert "Retrieved candidate markets with advisory scores" in app_js
    assert "orderedMarkets" in app_js
    assert "scoreById[right.market.market_id]" in app_js


def test_current_run_triage_does_not_auto_open_candidate_review_console():
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert "activeRunCandidateDetail" in app_js
    assert "promotion review is still unopened" in app_js
    assert "data-scroll-run-markets" in app_js
    assert "20260531-inverse-direct" in index_html

    create_candidate = app_js.split(
        "async function createCandidateFromCurrentRun", 1
    )[1].split("function currentSourceAssistedRef", 1)[0]
    assert 'openScreen === "review"' in create_candidate
    assert "state.selectedCandidateId = null" in create_candidate
    assert 'candidateSelectEl.value = ""' in create_candidate
    assert "resetWorkflowChoices();" in create_candidate
    assert "renderRun(state.currentRun)" in create_candidate


def test_current_run_reviewer_recommendation_is_read_only_draft():
    app_js = APP_JS.read_text(encoding="utf-8")

    render_run = app_js.split("function renderRun(run)", 1)[1].split(
        "function renderImprovement", 1
    )[0]
    assert "${reviewerRecommendationDraft(run)}" in render_run
    assert "bindReviewerRecommendations(run)" in render_run
    assert "Reviewer recommendation (read-only draft)" in app_js
    assert "Draft only for run" in app_js
    assert "No ledger event, candidate review file, Phoenix Dataset metadata" in app_js
    assert "Inverse market note" in app_js
    assert "supporting_outcome=No" in app_js
    assert "/api/verdicts" not in app_js
    assert "data-verdict" not in app_js
    assert "human_verdict_recorded" not in app_js
