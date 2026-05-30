const state = {
  currentRun: null,
  marketsById: {},
  candidateSummary: null,
  selectedCandidateId: null,
  strictGoldens: [],
  selectedGolden: null,
  workflow: {
    detail: null,
    triageDecision: null,
    reviewDecision: null,
    screen: "packet",
  },
};

const FIT_CLASSES = [
  { value: "direct", label: "Direct" },
  { value: "indirect", label: "Indirect" },
  { value: "weak_proxy", label: "Weak proxy" },
  { value: "no_clean_expression", label: "No clean expression" },
];

const statusEl = document.querySelector("#service-status");
const resultEl = document.querySelector("#result");
const evalEl = document.querySelector("#eval-summary");
const ledgerEl = document.querySelector("#ledger-events");
const improveButton = document.querySelector("#improve-button");
const runButton = document.querySelector("#run-button");
const candidateStatsEl = document.querySelector("#candidate-stats");
const candidateSelectEl = document.querySelector("#candidate-select");
const candidateRefreshButton = document.querySelector("#candidate-refresh");
const workflowRailEl = document.querySelector("#workflow-rail");
const workflowScreenEl = document.querySelector("#workflow-screen");
const strictGoldenSelectEl = document.querySelector("#strict-golden-select");
const strictGoldenNoteEl = document.querySelector("#strict-golden-note");
const thesisEl = document.querySelector("#thesis");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}

async function checkHealth() {
  try {
    const health = await api("/api/health");
    statusEl.textContent = health.status === "ok" ? "Service online" : "Service unavailable";
  } catch {
    statusEl.textContent = "Service unavailable";
  }
}

async function loadMarkets() {
  try {
    const markets = await api("/api/markets");
    state.marketsById = Object.fromEntries(markets.map((market) => [market.market_id, market]));
  } catch {
    state.marketsById = {};
  }
}

async function loadStrictGoldens() {
  try {
    const summary = await api("/api/strict-goldens");
    state.strictGoldens = summary.goldens || [];
    renderStrictGoldenSelect();
    updateStrictGoldenNote();
  } catch {
    state.strictGoldens = [];
    strictGoldenSelectEl.innerHTML = `<option value="">Strict goldens unavailable</option>`;
    strictGoldenNoteEl.textContent = "Strict golden list is unavailable; manual source text still works.";
  }
}

function renderStrictGoldenSelect() {
  const groups = new Map();
  state.strictGoldens.forEach((golden) => {
    if (!groups.has(golden.pack)) {
      groups.set(golden.pack, []);
    }
    groups.get(golden.pack).push(golden);
  });
  strictGoldenSelectEl.innerHTML = `
    <option value="">Manual source text</option>
    ${Array.from(groups.entries())
      .map(
        ([pack, goldens]) => `
          <optgroup label="${escapeHtml(pack)}">
            ${goldens
              .map(
                (golden) => `
                  <option value="${escapeHtml(goldenKey(golden))}">
                    ${escapeHtml(golden.example_id)} - ${escapeHtml(statusLabel(golden.expected_fit_class))}
                  </option>
                `
              )
              .join("")}
          </optgroup>
        `
      )
      .join("")}
  `;
}

strictGoldenSelectEl.addEventListener("change", () => {
  const selected = state.strictGoldens.find(
    (golden) => goldenKey(golden) === strictGoldenSelectEl.value
  );
  state.selectedGolden = selected || null;
  if (!selected) {
    updateStrictGoldenNote();
    return;
  }

  thesisEl.value = selected.source_text;
  resetCurrentRunForLoadedGolden(selected);
  updateStrictGoldenNote();
});

thesisEl.addEventListener("input", () => {
  updateStrictGoldenNote();
});

document.querySelector("#run-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  runButton.disabled = true;
  runButton.textContent = "Running";
  improveButton.disabled = true;
  const thesis = thesisEl.value;
  const promptVersion = document.querySelector("#prompt-version").value;
  beginCurrentRun();
  try {
    const run = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({ thesis, prompt_version: promptVersion }),
    });
    state.currentRun = run;
    renderRun(run);
  } catch (error) {
    resultEl.innerHTML = `<p class="flag-bad">${escapeHtml(error.message)}</p>`;
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run agent";
  }
});

improveButton.addEventListener("click", async () => {
  if (!state.currentRun) return;
  improveButton.disabled = true;
  improveButton.textContent = "Inspecting";
  clearCandidateSelectionForRun();
  evalEl.innerHTML = `<p class="empty">Inspecting trace for current run.</p>`;
  try {
    const improved = await api(`/api/runs/${state.currentRun.run_id}/improve`, {
      method: "POST",
    });
    state.currentRun = improved.after;
    renderImprovement(improved);
  } catch (error) {
    evalEl.innerHTML = `<p class="flag-bad">${escapeHtml(error.message)}</p>`;
  } finally {
    improveButton.textContent = "Inspect trace and rerun";
    improveButton.disabled = false;
  }
});

candidateSelectEl.addEventListener("change", async () => {
  state.selectedCandidateId = candidateSelectEl.value;
  resetWorkflowChoices();
  if (state.selectedCandidateId) {
    await loadCandidateDetail(state.selectedCandidateId);
  } else {
    renderWorkflow();
  }
});

candidateRefreshButton.addEventListener("click", async () => {
  candidateRefreshButton.disabled = true;
  candidateRefreshButton.textContent = "Refreshing";
  try {
    await loadCandidates();
  } finally {
    candidateRefreshButton.disabled = false;
    candidateRefreshButton.textContent = "Refresh";
  }
});

function renderRun(run) {
  improveButton.disabled = false;
  indexRunMarkets(run);
  resultEl.innerHTML = `
    <span class="label">Normalized thesis</span>
    <p class="claim-text">${escapeHtml(run.claim.claim_text)}</p>
    ${fitClassScale(run.fit.semantic_fit_class)}
    ${runGovernancePrompt()}
    ${retrievedMarketContext(run)}
    ${recommendedMarket(run)}
    <div class="meta-grid">
      ${meta("Entities", run.claim.entities.join(", ") || "Unspecified")}
      ${meta("Horizon", run.claim.horizon)}
      ${meta("Stance", run.claim.stance)}
      ${meta("Confidence", run.claim.confidence)}
    </div>
    <div class="market">
      <span class="label">Fit reason</span>
      <p>${escapeHtml(run.fit.fit_reason)}</p>
      ${list("Captures", run.fit.captures)}
      ${list("Misses", run.fit.misses)}
      ${list("Rejected markets", run.fit.rejected_markets.map((item) => `${item.market_id}: ${item.reason}`))}
    </div>
    <div class="verdicts" data-claim-id="${run.claim_id}">
      <span class="label">Human review decision</span>
      <button type="button" data-verdict="verify">Verify</button>
      <button type="button" data-verdict="reject">Reject</button>
      <button type="button" data-verdict="needs_review">Needs review</button>
      <button type="button" data-verdict="corrected">Correct to weak proxy</button>
    </div>
  `;
  bindVerdicts();
  bindRunGovernance();
  renderEval(run);
  renderLedger(run.ledger);
  renderWorkflow();
}

function renderImprovement(improved) {
  const before = improved.before;
  const after = improved.after;
  indexRunMarkets(after);
  resultEl.innerHTML = `
    <div class="inspection">
      <span class="label">Phoenix MCP inspection</span>
      <p>${escapeHtml(improved.inspection.summary)}</p>
      <p class="trace">source=${escapeHtml(improved.inspection_source)} fallback=${escapeHtml(improved.fallback_used)} trace=${escapeHtml(improved.before_trace_id)}</p>
    </div>
    <div class="meta-grid">
      ${meta("Before", `${before.fit.semantic_fit_class} / false strong: ${before.eval.metrics.false_strong_recommendation}`)}
      ${meta("After", `${after.fit.semantic_fit_class} / false strong: ${after.eval.metrics.false_strong_recommendation}`)}
    </div>
    <span class="label">Revised normalized thesis</span>
    <p class="claim-text">${escapeHtml(after.claim.claim_text)}</p>
    ${fitClassScale(after.fit.semantic_fit_class)}
    ${recommendedMarket(after)}
    <div class="market">
      <span class="label">Revised fit reason</span>
      <p>${escapeHtml(after.fit.fit_reason)}</p>
      ${list("Misses", after.fit.misses)}
    </div>
  `;
  renderEval(after);
  renderLedger(after.ledger);
  renderWorkflow();
}

async function loadCandidates() {
  try {
    const summary = await api("/api/retrieval-candidates");
    state.candidateSummary = summary;
    const rows = summary.rows || [];
    renderCandidateStats(summary);
    renderCandidateSelect(rows);
    if (state.selectedCandidateId) {
      await loadCandidateDetail(state.selectedCandidateId);
    } else {
      resetWorkflowChoices();
      renderWorkflow();
    }
  } catch (error) {
    candidateStatsEl.innerHTML = "";
    workflowRailEl.innerHTML = "";
    workflowScreenEl.innerHTML = `<p class="flag-bad">${escapeHtml(error.message)}</p>`;
  }
}

function renderCandidateStats(summary) {
  const counts = summary.review_status_counts || {};
  candidateStatsEl.innerHTML = `
    <p class="candidate-scope-note">Phoenix candidate Dataset totals. These counters are independent of the active run; select a packet by case_id for row-level metadata.</p>
    ${candidateStat("Dataset version", datasetLink(summary))}
    ${candidateStat("Dataset rows", summary.candidate_count ?? 0)}
    ${candidateStat("Human promote", counts.promote || 0)}
    ${candidateStat("Needs rules", counts.needs_more_rules || 0)}
    ${candidateStat("Human reject", counts.reject || 0)}
    ${candidateStat("Strict labels", summary.strict_expected_labels_present ? "present" : "absent")}
  `;
}

function datasetLink(summary) {
  if (!summary.dataset_url) return "local export";
  const version = summary.dataset_version_id || summary.dataset_id || "open";
  return `<a href="${escapeHtml(summary.dataset_url)}" target="_blank" rel="noreferrer">${escapeHtml(version)}</a>`;
}

function candidateStat(label, value) {
  return `
    <div class="candidate-stat">
      <span class="label">${escapeHtml(label)}</span>
      <strong>${value}</strong>
    </div>
  `;
}

function renderCandidateSelect(rows) {
  candidateSelectEl.innerHTML = `
    <option value="">Select packet</option>
    ${rows
      .map(
        (row) => `
        <option value="${escapeHtml(row.case_id)}" ${row.case_id === state.selectedCandidateId ? "selected" : ""}>
          ${escapeHtml(row.case_id)}
        </option>
      `
      )
      .join("")}
  `;
}

async function loadCandidateDetail(caseId) {
  try {
    const detail = await api(`/api/retrieval-candidates/${encodeURIComponent(caseId)}`);
    state.workflow.detail = detail;
    renderWorkflow();
  } catch (error) {
    workflowScreenEl.innerHTML = `<p class="flag-bad">${escapeHtml(error.message)}</p>`;
  }
}

function resetWorkflowChoices() {
  state.workflow = {
    detail: null,
    triageDecision: null,
    reviewDecision: null,
    screen: "packet",
  };
}

function beginCurrentRun() {
  state.currentRun = null;
  clearCandidateSelectionForRun();
  resultEl.innerHTML = `<p class="empty">Running current thesis through bounded retrieval, deterministic policy, and Phoenix eval logging.</p>`;
  evalEl.innerHTML = `<p class="empty">Waiting for current run eval.</p>`;
  ledgerEl.innerHTML = "";
}

function resetCurrentRunForLoadedGolden(golden) {
  state.currentRun = null;
  improveButton.disabled = true;
  clearCandidateSelectionForRun();
  resultEl.innerHTML = `<p class="empty">Strict golden loaded. Click Run agent to replay the frozen fixture context.</p>`;
  evalEl.innerHTML = `<p class="empty">No eval recorded for loaded golden.</p>`;
  ledgerEl.innerHTML = "";
  const promptVersionEl = document.querySelector("#prompt-version");
  if (promptVersionEl) {
    promptVersionEl.value = "v1_lenient";
  }
}

function clearCandidateSelectionForRun() {
  state.selectedCandidateId = null;
  if (candidateSelectEl) {
    candidateSelectEl.value = "";
  }
  resetWorkflowChoices();
  renderWorkflow();
}

function updateStrictGoldenNote() {
  const currentText = normalizeSource(thesisEl.value);
  const selected = state.selectedGolden;
  if (selected && currentText === normalizeSource(selected.source_text)) {
    strictGoldenNoteEl.textContent = `Exact golden source loaded: ${selected.pack} / ${selected.example_id}. Run will use frozen fixture context.`;
    strictGoldenNoteEl.className = "golden-note is-active";
    return;
  }
  if (selected) {
    strictGoldenNoteEl.textContent = "Edited text may leave golden replay mode; exact strict golden text is required for frozen fixture context.";
    strictGoldenNoteEl.className = "golden-note is-edited";
    return;
  }

  const matched = state.strictGoldens.find(
    (golden) => currentText === normalizeSource(golden.source_text)
  );
  if (matched) {
    strictGoldenNoteEl.textContent = `Exact strict golden source detected: ${matched.pack} / ${matched.example_id}. Run will use frozen fixture context.`;
    strictGoldenNoteEl.className = "golden-note is-active";
    return;
  }

  strictGoldenNoteEl.textContent = "Manual source text. Unknown or edited theses use the normal retrieval path.";
  strictGoldenNoteEl.className = "golden-note";
}

function renderWorkflow() {
  const detail = state.workflow.detail;
  if (!detail) {
    workflowRailEl.innerHTML = "";
    workflowScreenEl.innerHTML = `
      <div class="candidate-detail-head">
        <div>
          <p class="eyebrow">Existing candidate queue</p>
          <h3>No candidate selected</h3>
        </div>
      </div>
      <p class="empty">Select a candidate packet to inspect its triage and review artifacts.</p>
    `;
    return;
  }
  workflowRailEl.innerHTML = renderWorkflowRail(detail);
  workflowScreenEl.innerHTML = renderWorkflowScreen(detail);
  bindWorkflowControls();
}

function renderWorkflowRail(detail) {
  const row = detail.dataset_export?.row || {};
  const review = detail.review_decision || {};
  const humanStatus = review.human_review_status || row.human_review_status || "pending";
  const promotionStatus = humanStatus === "promote" ? "eligible" : "held";
  const triageStatus =
    state.workflow.triageDecision === null
      ? "ask"
      : state.workflow.triageDecision === "yes"
        ? "opened"
        : "skipped";
  const reviewStatus =
    state.workflow.triageDecision === null
      ? "waiting"
      : state.workflow.reviewDecision === null
        ? "ask"
      : state.workflow.reviewDecision === "yes"
        ? "opened"
        : "skipped";

  return `
    ${workflowStep("packet", "Candidate packet", "loaded", [
      smallLabel("Case", detail.case_id),
      smallLabel("Retrieved", String((row.retrieved_market_ids || []).length || (detail.market_snapshots || []).length)),
      smallLabel("Rules", row.rules_status || "unknown"),
    ])}
    ${workflowQuestionStep({
      id: "triage",
      title: "LLM triage suggestion",
      status: triageStatus,
      decision: state.workflow.triageDecision,
      yesLabel: "Yes, inspect",
      noLabel: "No",
      decisionAttr: "data-triage-decision",
    })}
    ${workflowStep("suggestion", "llm_review_suggestion.json", state.workflow.triageDecision === "yes" ? "present" : "locked", [
      smallLabel("Source", state.workflow.triageDecision === "yes" ? row.llm_triage_source || "local" : "not opened"),
      smallLabel("Priority", state.workflow.triageDecision === "yes" ? row.llm_review_priority || "n/a" : "not opened"),
    ])}
    ${workflowStep("phoenix", "Phoenix Dataset metadata", state.workflow.triageDecision === "yes" ? "mirrored" : "locked", [
      smallLabel("Dataset", state.workflow.triageDecision === "yes" ? detail.dataset_export?.dataset_name || "n/a" : "not opened"),
      smallLabel("Version", state.workflow.triageDecision === "yes" ? detail.dataset_export?.dataset_version_id || "local" : "not opened"),
    ])}
    ${workflowQuestionStep({
      id: "review",
      title: "Human review decision",
      status: reviewStatus,
      decision: state.workflow.reviewDecision,
      yesLabel: "Yes, review",
      noLabel: "No",
      decisionAttr: "data-review-decision",
      disabled: state.workflow.triageDecision === null,
    })}
    ${workflowStep("promotion", "Promotion gate", state.workflow.reviewDecision === "yes" ? promotionStatus : "locked", [
      smallLabel("Human status", state.workflow.reviewDecision === "yes" ? humanStatus : "not opened"),
      smallLabel("Strict labels", state.workflow.reviewDecision === "yes" ? (detail.dataset_export?.strict_expected_labels_present ? "present" : "absent") : "not opened"),
    ])}
    ${workflowStep("strict", "Deterministic strict eval", strictEvalStatus(), [
      smallLabel("Current run", state.currentRun ? state.currentRun.fit.semantic_fit_class : "not run"),
      smallLabel("Gate", state.workflow.triageDecision === "no" && state.workflow.reviewDecision === "no" ? "open" : "fallback"),
    ])}
  `;
}

function workflowStep(screen, title, status, bodyItems) {
  const active = state.workflow.screen === screen ? "is-active" : "";
  return `
    <button type="button" class="workflow-step ${active}" data-workflow-screen="${escapeHtml(screen)}">
      <span class="workflow-step-top">
        <strong>${escapeHtml(title)}</strong>
        <span class="status-chip ${statusClass(status)}">${escapeHtml(statusLabel(status))}</span>
      </span>
      <span class="workflow-step-body">${bodyItems.join("")}</span>
    </button>
  `;
}

function workflowQuestionStep({
  id,
  title,
  status,
  decision,
  yesLabel,
  noLabel,
  decisionAttr,
  disabled = false,
}) {
  const active = state.workflow.screen === id ? "is-active" : "";
  const disabledAttr = disabled ? "disabled" : "";
  return `
    <div class="workflow-step workflow-question ${active}">
      <button type="button" class="workflow-step-face" data-workflow-screen="${escapeHtml(id)}" ${disabledAttr}>
        <span class="workflow-step-top">
          <strong>${escapeHtml(title)}</strong>
          <span class="status-chip ${statusClass(status)}">${escapeHtml(statusLabel(status))}</span>
        </span>
        <span class="workflow-step-body">
          ${smallLabel("Decision", decision || (disabled ? "waiting" : "unanswered"))}
        </span>
      </button>
      <span class="workflow-choice-row">
        <button type="button" ${decisionAttr}="yes" ${disabledAttr}>${escapeHtml(yesLabel)}</button>
        <button type="button" ${decisionAttr}="no" ${disabledAttr}>${escapeHtml(noLabel)}</button>
      </span>
    </div>
  `;
}

function strictEvalStatus() {
  if (state.workflow.triageDecision === "no" && state.workflow.reviewDecision === "no") {
    return "open";
  }
  return state.currentRun ? "ready" : "waiting";
}

function renderWorkflowScreen(detail) {
  if (state.workflow.screen === "triage") return renderTriageScreen(detail);
  if (state.workflow.screen === "suggestion") return renderTriageScreen(detail);
  if (state.workflow.screen === "phoenix") return renderTriageScreen(detail);
  if (state.workflow.screen === "review") return renderReviewScreen(detail);
  if (state.workflow.screen === "promotion") return renderReviewScreen(detail);
  if (state.workflow.screen === "strict") return renderStrictScreen();
  return renderPacketScreen(detail);
}

function renderPacketScreen(detail) {
  const row = detail.dataset_export?.row || {};
  const run = detail.run_result || {};
  const claim = run.claim || row.normalized_claim || {};
  const traceUrl = run.phoenix_trace_url || row.phoenix_trace_url;

  return `
    <div class="candidate-detail-head">
      <div>
        <p class="eyebrow">Live retrieval candidate packet</p>
        <h3>${escapeHtml(detail.case_id)}</h3>
      </div>
      <span class="status-chip status-present">packet</span>
    </div>
    <div class="detail-grid">
      ${meta("Run", run.run_id || row.run_id || "n/a")}
      ${meta("Retrieved markets", String((row.retrieved_market_ids || []).length || (detail.market_snapshots || []).length))}
      ${meta("Rules status", row.rules_status || "unknown")}
      ${meta("Proposed fit", row.proposed_fit_class || "n/a")}
      ${meta("Recommended market", row.recommended_market_id || "none")}
      ${meta("Candidate dir", detail.candidate_dir)}
    </div>
    <section class="candidate-copy">
      <span class="label">Source text</span>
      <p>${escapeHtml(detail.source?.source_text || row.source_text || "")}</p>
    </section>
    <section class="candidate-copy">
      <span class="label">Normalized claim</span>
      <p>${escapeHtml(claim.claim_text || "No normalized claim recorded.")}</p>
      <div class="detail-grid compact">
        ${meta("Entities", (claim.entities || []).join(", ") || "Unspecified")}
        ${meta("Horizon", claim.horizon || "unspecified")}
      </div>
    </section>
    <section class="candidate-copy">
      <span class="label">Phoenix trace</span>
      ${
        traceUrl
          ? `<p class="trace"><a href="${escapeHtml(traceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(traceUrl)}</a></p>`
          : `<p class="trace">${escapeHtml(run.phoenix_trace_id || row.phoenix_trace_id || "n/a")}</p>`
      }
    </section>
  `;
}

function renderTriageScreen(detail) {
  if (state.workflow.triageDecision !== "yes") {
    return `
      <div class="candidate-detail-head">
        <div>
          <p class="eyebrow">Optional step</p>
          <h3>LLM triage suggestion</h3>
        </div>
      </div>
      <div class="screen-prompt">
        <p>Open the LLM triage suggestion for this candidate?</p>
        <button type="button" data-triage-decision="yes">Yes, inspect</button>
        <button type="button" data-triage-decision="no">No</button>
      </div>
    `;
  }

  const row = detail.dataset_export?.row || {};
  const run = detail.run_result || {};
  const fit = run.fit || {};
  const suggestion = detail.llm_review_suggestion || null;
  const llmStatus = suggestion?.suggested_review_status || "no_suggestion";

  return `
    <div class="candidate-detail-head">
      <div>
        <p class="eyebrow">LLM triage suggestion</p>
        <h3>${escapeHtml(detail.case_id)}</h3>
      </div>
      <span class="status-chip ${statusClass(llmStatus)}">${escapeHtml(statusLabel(llmStatus))}</span>
    </div>
    <div class="authority-grid">
      <section>
        <span class="label">llm_review_suggestion.json</span>
        <div class="decision-line">
          <span class="status-chip ${statusClass(llmStatus)}">${escapeHtml(statusLabel(llmStatus))}</span>
          <span class="trace">${escapeHtml(suggestion?.triage_source || row.llm_triage_source || "none")}</span>
        </div>
        <p>${escapeHtml(suggestion?.judge_rationale || "No LLM suggestion recorded.")}</p>
        ${tagList(suggestion?.likely_issues || row.llm_likely_issues || [], "detail-tags")}
      </section>
      <section>
        <span class="label">Phoenix candidate Dataset metadata</span>
        <div class="detail-grid compact">
          ${meta("Dataset", detail.dataset_export?.dataset_name || "n/a")}
          ${meta("Version", detail.dataset_export?.dataset_version_id || "local")}
          ${meta("Mode", detail.dataset_export?.mode || "local")}
          ${meta("Strict labels", detail.dataset_export?.strict_expected_labels_present ? "present" : "absent")}
        </div>
        ${
          detail.dataset_export?.dataset_url
            ? `<p class="trace"><a href="${escapeHtml(detail.dataset_export.dataset_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.dataset_export.dataset_url)}</a></p>`
            : ""
        }
      </section>
    </div>
    <div class="detail-grid">
      ${meta("Rules status", row.rules_status || "unknown")}
      ${meta("Proposed fit", fit.semantic_fit_class || row.proposed_fit_class || "n/a")}
      ${meta("Recommended market", fit.recommended_market_id || row.recommended_market_id || "none")}
      ${meta("Markets to inspect", (suggestion?.markets_to_inspect || row.llm_markets_to_inspect || []).join(", ") || "none")}
      ${meta("Canonical truth", suggestion?.canonical_truth === false ? "false" : "n/a")}
    </div>
    ${candidateMarketList(detail, fit, suggestion)}
  `;
}

function renderReviewScreen(detail) {
  if (state.workflow.reviewDecision !== "yes") {
    return `
      <div class="candidate-detail-head">
        <div>
          <p class="eyebrow">Human gate</p>
          <h3>Human review decision</h3>
        </div>
      </div>
      <div class="screen-prompt">
        <p>Open the review console for this candidate?</p>
        <button type="button" data-review-decision="yes">Yes, review</button>
        <button type="button" data-review-decision="no">No</button>
      </div>
    `;
  }

  const row = detail.dataset_export?.row || {};
  const review = detail.review_decision || {};
  const humanStatus = review.human_review_status || row.human_review_status || "pending";
  const promoted = humanStatus === "promote";

  return `
    <div class="candidate-detail-head">
      <div>
        <p class="eyebrow">Review console</p>
        <h3>${escapeHtml(detail.case_id)}</h3>
      </div>
      <span class="status-chip ${statusClass(humanStatus)}">${escapeHtml(statusLabel(humanStatus))}</span>
    </div>
    <div class="authority-grid">
      <section>
        <span class="label">Human review authority</span>
        <div class="decision-line">
          <span class="status-chip ${statusClass(humanStatus)}">${escapeHtml(statusLabel(humanStatus))}</span>
          <span class="trace">${escapeHtml(review.reviewed_at_utc || row.reviewed_at_utc || "unreviewed")}</span>
        </div>
        <p>${escapeHtml(review.reviewer_note || row.reviewer_note || "No reviewer note recorded.")}</p>
      </section>
      <section>
        <span class="label">Promotion gate</span>
        <div class="decision-line">
          <span class="status-chip ${promoted ? "status-promote" : "status-held"}">${promoted ? "eligible" : "held"}</span>
          <span class="trace">${escapeHtml(row.reviewer || review.reviewer || "local_reviewer")}</span>
        </div>
        <p>${escapeHtml(promoted ? "Promoted frozen fixtures remain downstream of human promotion." : "Frozen fixture promotion is blocked unless human status is promote.")}</p>
      </section>
    </div>
    <div class="detail-grid">
      ${meta("Human status", humanStatus)}
      ${meta("Reviewed at", review.reviewed_at_utc || row.reviewed_at_utc || "unreviewed")}
      ${meta("Proposed fit", row.proposed_fit_class || "n/a")}
      ${meta("Recommended market", row.recommended_market_id || "none")}
      ${meta("Review decision path", detail.dataset_export?.row?.review_decision_path || "review_decision.json")}
      ${meta("Strict labels in candidate Dataset", detail.dataset_export?.strict_expected_labels_present ? "present" : "absent")}
    </div>
    <section class="candidate-copy">
      <span class="label">Candidate source</span>
      <p>${escapeHtml(detail.source?.source_text || row.source_text || "")}</p>
    </section>
  `;
}

function renderStrictScreen() {
  if (!(state.workflow.triageDecision === "no" && state.workflow.reviewDecision === "no")) {
    return `
      <div class="candidate-detail-head">
        <div>
          <p class="eyebrow">Fallback gate</p>
          <h3>Deterministic strict eval</h3>
        </div>
      </div>
      <p class="empty">Strict eval fallback opens after triage and review are both skipped.</p>
    `;
  }
  if (!state.currentRun) {
    return `
      <div class="candidate-detail-head">
        <div>
          <p class="eyebrow">Deterministic strict eval</p>
          <h3>No current run</h3>
        </div>
      </div>
      <p class="empty">Run the agent above to populate the deterministic eval block.</p>
    `;
  }
  const metrics = state.currentRun.eval.metrics;
  return `
    <div class="candidate-detail-head">
      <div>
        <p class="eyebrow">Deterministic strict eval</p>
        <h3>${escapeHtml(state.currentRun.claim.claim_text)}</h3>
      </div>
      <span class="status-chip ${state.currentRun.eval.failure_summary ? "status-reject" : "status-promote"}">${state.currentRun.eval.failure_summary ? "failed" : "passed"}</span>
    </div>
    <div class="metric-grid">
      ${metric("Schema", metrics.schema_valid)}
      ${metric("False strong", metrics.false_strong_recommendation, true)}
      ${metric("Weak proxy detected", metrics.weak_proxy_detected)}
      ${metric("Unsupported", metrics.unsupported_implication, true)}
      ${metric("Human review", metrics.human_verification_required)}
    </div>
    ${state.currentRun.eval.failure_summary ? `<p class="flag-bad">${escapeHtml(state.currentRun.eval.failure_summary)}</p>` : `<p class="flag-good">Eval passed for this seed case.</p>`}
  `;
}

function bindWorkflowControls() {
  workflowRailEl.querySelectorAll("[data-workflow-screen]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      state.workflow.screen = button.dataset.workflowScreen;
      renderWorkflow();
    });
  });
  workflowScreenEl.querySelectorAll("[data-triage-decision]").forEach((button) => {
    button.addEventListener("click", () => setTriageDecision(button.dataset.triageDecision));
  });
  workflowRailEl.querySelectorAll("[data-triage-decision]").forEach((button) => {
    button.addEventListener("click", () => setTriageDecision(button.dataset.triageDecision));
  });
  workflowScreenEl.querySelectorAll("[data-review-decision]").forEach((button) => {
    button.addEventListener("click", () => setReviewDecision(button.dataset.reviewDecision));
  });
  workflowRailEl.querySelectorAll("[data-review-decision]").forEach((button) => {
    button.addEventListener("click", () => setReviewDecision(button.dataset.reviewDecision));
  });
}

function setTriageDecision(value) {
  state.workflow.triageDecision = value;
  state.workflow.reviewDecision = null;
  state.workflow.screen = value === "yes" ? "triage" : "packet";
  renderWorkflow();
}

function setReviewDecision(value) {
  state.workflow.reviewDecision = value;
  if (value === "yes") {
    state.workflow.screen = "review";
  } else if (state.workflow.triageDecision === "no") {
    state.workflow.screen = "strict";
  } else {
    state.workflow.screen = "packet";
  }
  renderWorkflow();
}

function candidateMarketList(detail, fit, suggestion) {
  const markets = detail.market_snapshots || [];
  const rulesById = Object.fromEntries(
    (detail.review_rules || []).map((rule) => [rule.market_id, rule])
  );
  const inspectIds = new Set(suggestion?.markets_to_inspect || []);
  const recommendedId = fit.recommended_market_id;
  if (markets.length === 0) {
    return `<p class="empty">No retrieved markets recorded.</p>`;
  }
  return `
    <section class="candidate-markets">
      <span class="label">Retrieved markets</span>
      ${markets
        .map((market) => candidateMarketRow(market, rulesById, recommendedId, inspectIds))
        .join("")}
    </section>
  `;
}

function candidateMarketRow(market, rulesById, recommendedId, inspectIds) {
  const rules = rulesById[market.market_id] || {};
  const rulesStatus = rules.rules_status || (market.resolution_rules ? "present" : "unknown");
  const rulesText = rules.resolution_rules || market.resolution_rules || "";
  const markers = [
    market.market_id === recommendedId ? "recommended" : null,
    inspectIds.has(market.market_id) ? "inspect" : null,
  ].filter(Boolean);
  return `
    <article class="market-row">
      <div class="market-row-main">
        <div>
          <strong>${escapeHtml(market.title || market.market_id)}</strong>
          <p class="trace">${escapeHtml(market.market_id)}</p>
        </div>
        <div class="market-row-chips">
          ${markers.map((marker) => `<span>${escapeHtml(marker)}</span>`).join("")}
          <span>${escapeHtml(rulesStatus)}</span>
        </div>
      </div>
      <div class="detail-grid compact">
        ${meta("Close", market.close_date || "n/a")}
        ${meta("Probability", market.current_probability ?? "n/a")}
      </div>
      <details>
        <summary>Resolution rules</summary>
        <p>${escapeHtml(rulesText || "Rules unavailable from provider.")}</p>
      </details>
    </article>
  `;
}

function indexRunMarkets(run) {
  if (!Array.isArray(run.market_context)) return;
  run.market_context.forEach((market) => {
    state.marketsById[market.market_id] = market;
  });
}

function fitClassScale(current) {
  return `
    <div class="fit-scale">
      <span class="label">Market-fit class</span>
      <div class="fit-options">
        ${FIT_CLASSES.map(
          (item) => `
            <span class="fit-option ${item.value === current ? "is-active" : ""}">
              ${escapeHtml(item.label)}
            </span>
          `
        ).join("")}
      </div>
    </div>
  `;
}

function recommendedMarket(run) {
  const marketId = run.fit.recommended_market_id;
  if (!marketId) {
    return `
      <div class="recommended-market">
        <span class="label">Recommended market</span>
        <p class="market-title">None</p>
      </div>
    `;
  }

  const market = state.marketsById[marketId];
  const resolutionRules = market?.resolution_rules?.trim();
  return `
    <div class="recommended-market">
      <span class="label">Recommended market</span>
      <p class="market-title">${escapeHtml(market?.title || marketId)}</p>
      <p class="trace">${escapeHtml(marketId)}</p>
      ${
        market
          ? `
            <div class="market-details">
              ${meta("Venue", market.venue)}
              ${meta("Close", market.close_date)}
              ${meta("Outcomes", market.outcomes.join(" / "))}
              ${meta("Probability", market.current_probability === null || market.current_probability === undefined ? "n/a" : market.current_probability)}
            </div>
            <span class="label">Resolution rules</span>
            ${
              resolutionRules
                ? `<p>${escapeHtml(resolutionRules)}</p>`
                : `<p class="flag-warn">Rules unavailable from provider; treated as fit-risk.</p>`
            }
            ${riskTags(market.known_fit_risks)}
          `
          : ""
      }
    </div>
  `;
}

function retrievedMarketContext(run) {
  const markets = run.market_context || [];
  if (markets.length === 0) return "";
  const recommendedId = run.fit.recommended_market_id;
  const rejectedById = Object.fromEntries(
    (run.fit.rejected_markets || []).map((item) => [item.market_id, item.reason])
  );
  return `
    <section class="run-market-context">
      <span class="label">Found relevant markets (${markets.length})</span>
      ${markets
        .map((market) => runMarketRow(market, recommendedId, rejectedById))
        .join("")}
    </section>
  `;
}

function runMarketRow(market, recommendedId, rejectedById) {
  const markers = [
    market.market_id === recommendedId ? "recommended" : null,
    rejectedById[market.market_id] ? "rejected" : null,
    ...(market.known_fit_risks || []).slice(0, 2).map((risk) => risk.replaceAll("_", " ")),
  ].filter(Boolean);
  const rules = market.resolution_rules?.trim();
  return `
    <article class="run-market-row">
      <div class="market-row-main">
        <div>
          <strong>${escapeHtml(market.title || market.market_id)}</strong>
          <p class="trace">${escapeHtml(market.market_id)}</p>
        </div>
        <div class="market-row-chips">
          ${markers.map((marker) => `<span>${escapeHtml(marker)}</span>`).join("")}
        </div>
      </div>
      <div class="detail-grid compact">
        ${meta("Close", market.close_date || "n/a")}
        ${meta("Probability", market.current_probability === null || market.current_probability === undefined ? "n/a" : market.current_probability)}
      </div>
      ${
        rejectedById[market.market_id]
          ? `<p class="flag-warn">${escapeHtml(rejectedById[market.market_id])}</p>`
          : ""
      }
      <details>
        <summary>Resolution rules</summary>
        <p>${escapeHtml(rules || "Rules unavailable from provider; treated as fit-risk.")}</p>
      </details>
    </article>
  `;
}

function runGovernancePrompt() {
  return `
    <section class="run-governance">
      <span class="label">Workflow gates</span>
      <div class="run-question-grid">
        <div class="run-question-card">
          <strong>Candidate triage unavailable for this run</strong>
          <p>No candidate packet is bound to this run. LLM triage suggestions exist only after exporting a retrieval candidate packet.</p>
          <div class="run-gate-actions">
            <button type="button" data-scroll-candidate-queue>Browse existing candidate packets</button>
            <button type="button" data-run-gate-skip>Keep current run only</button>
          </div>
        </div>
        <div class="run-question-card">
          <strong>Open human review?</strong>
          <p>Human review remains the authority for promotion; the buttons below record a run-level verdict.</p>
          <div class="run-gate-actions">
            <button type="button" data-run-review-open>Yes, review</button>
            <button type="button" data-run-review-skip>No</button>
          </div>
        </div>
      </div>
      <p class="trace" id="run-gate-note">Existing candidate packets are independent from this run unless you explicitly select a case_id.</p>
    </section>
  `;
}

function bindRunGovernance() {
  document.querySelectorAll("[data-scroll-candidate-queue]").forEach((button) => {
    button.addEventListener("click", () => {
      const workbench = document.querySelector(".candidate-workbench");
      if (workbench) {
        workbench.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      const note = document.querySelector("#run-gate-note");
      if (note) {
        note.textContent = "Opened the existing candidate queue. Select a case_id explicitly before viewing triage or review artifacts.";
      }
    });
  });
  document.querySelectorAll("[data-run-gate-skip]").forEach((button) => {
    button.addEventListener("click", () => {
      const note = document.querySelector("#run-gate-note");
      if (note) {
        note.textContent = "Kept this screen bound to the current run. Candidate triage remains unavailable until a packet is exported.";
      }
    });
  });
  document.querySelectorAll("[data-run-review-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const verdicts = document.querySelector(".verdicts");
      if (verdicts) {
        verdicts.scrollIntoView({ behavior: "smooth", block: "center" });
        verdicts.classList.add("is-highlighted");
        setTimeout(() => verdicts.classList.remove("is-highlighted"), 1800);
      }
      const note = document.querySelector("#run-gate-note");
      if (note) {
        note.textContent = "Opened run-level human review controls. Promotion still requires candidate review status in the promotion workflow.";
      }
    });
  });
  document.querySelectorAll("[data-run-review-skip]").forEach((button) => {
    button.addEventListener("click", () => {
      const note = document.querySelector("#run-gate-note");
      if (note) {
        note.textContent = "Skipped human review for this run. No promoted fixture is created from this screen.";
      }
    });
  });
}

function bindVerdicts() {
  document.querySelectorAll("[data-verdict]").forEach((button) => {
    button.addEventListener("click", async () => {
      const claimId = button.parentElement.dataset.claimId;
      const verdict = button.dataset.verdict;
      const payload = {
        claim_id: claimId,
        verdict,
        corrected_fit_class: verdict === "corrected" ? "weak_proxy" : null,
        reviewer_note:
          verdict === "corrected"
            ? "Human reviewer downgraded the tempting market to a weak proxy."
            : "Human reviewer recorded a verdict from the demo UI.",
      };
      const response = await api("/api/verdicts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderLedger(response.ledger);
    });
  });
}

function renderEval(run) {
  const metrics = run.eval.metrics;
  evalEl.innerHTML = `
    <div class="run-eval-context">
      <span class="label">Current run Phoenix eval</span>
      ${meta("Run ID", run.run_id)}
      ${meta("Trace ID", run.phoenix_trace_id)}
      ${meta("Prompt", run.prompt_version)}
      ${meta("Fit", run.fit.semantic_fit_class)}
    </div>
    <div class="trace">
      ${
        run.phoenix_trace_url
          ? `<a href="${escapeHtml(run.phoenix_trace_url)}" target="_blank" rel="noreferrer">Open Phoenix trace</a>`
          : escapeHtml(run.phoenix_trace_id)
      }
    </div>
    <div class="metric-grid">
      ${metric("Schema", metrics.schema_valid)}
      ${metric("False strong", metrics.false_strong_recommendation, true)}
      ${metric("Weak proxy detected", metrics.weak_proxy_detected)}
      ${metric("Unsupported", metrics.unsupported_implication, true)}
      ${metric("Human review", metrics.human_verification_required)}
      ${metrics.second_run_improvement === null || metrics.second_run_improvement === undefined ? "" : metric("Second run", metrics.second_run_improvement)}
    </div>
    ${run.eval.failure_summary ? `<p class="flag-bad">${escapeHtml(run.eval.failure_summary)}</p>` : `<p class="flag-good">Eval passed for this seed case.</p>`}
  `;
}

function renderLedger(ledger) {
  ledgerEl.innerHTML = `
    <p class="eyebrow">Ledger events</p>
    ${ledger.events
      .map(
        (event) => `
          <div class="event">
            <strong>${escapeHtml(event.event_type)}</strong>
            <time>${escapeHtml(event.created_at)}</time>
            <p>${escapeHtml(event.summary)}</p>
          </div>`
      )
      .join("")}
  `;
}

function meta(label, value) {
  return `<div class="meta"><span class="label">${escapeHtml(label)}</span>${escapeHtml(value)}</div>`;
}

function metric(label, value, invert = false) {
  const ok = invert ? !value : Boolean(value);
  const klass = ok ? "flag-good" : "flag-bad";
  return `<div class="metric"><span class="label">${escapeHtml(label)}</span><strong class="${klass}">${escapeHtml(String(value))}</strong></div>`;
}

function list(label, values) {
  if (!values || values.length === 0) return "";
  return `<span class="label">${escapeHtml(label)}</span><ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`;
}

function riskTags(values) {
  if (!values || values.length === 0) return "";
  return `
    <span class="label">Fit risk signals</span>
    <div class="risk-tags">
      ${values.map((value) => `<span>${escapeHtml(value.replaceAll("_", " "))}</span>`).join("")}
    </div>
  `;
}

function tagList(values, className) {
  if (!values || values.length === 0) return "";
  return `
    <span class="${escapeHtml(className)}">
      ${values.map((value) => `<span>${escapeHtml(statusLabel(value))}</span>`).join("")}
    </span>
  `;
}

function smallLabel(label, value) {
  return `
    <span class="small-label">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(statusLabel(value))}</strong>
    </span>
  `;
}

function statusClass(value) {
  return `status-${String(value || "unknown")
    .toLowerCase()
    .replaceAll("_", "-")
    .replace(/[^a-z0-9-]/g, "-")}`;
}

function statusLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function goldenKey(golden) {
  return `${golden.pack}::${golden.example_id}`;
}

function normalizeSource(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

checkHealth();
loadMarkets();
loadStrictGoldens();
loadCandidates();
