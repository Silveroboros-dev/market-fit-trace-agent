const state = {
  currentRun: null,
  activeRunCandidateId: null,
  activeRunCandidateDetail: null,
  marketsById: {},
  candidateSummary: null,
  selectedCandidateId: null,
  strictGoldens: [],
  selectedGolden: null,
  sourceCandidates: [],
  selectedSourceCandidate: null,
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
const sourceCandidateSelectEl = document.querySelector("#source-candidate-select");
const sourceCandidateNoteEl = document.querySelector("#source-candidate-note");
const thesisEl = document.querySelector("#thesis");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `HTTP ${response.status}`;
    try {
      const parsed = JSON.parse(text);
      message = parsed.detail || message;
    } catch {
      // Keep the raw body when the response is not JSON.
    }
    throw new Error(message);
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

async function loadSourceCandidates() {
  try {
    const summary = await api("/api/source-candidates");
    state.sourceCandidates = summary.rows || [];
    renderSourceCandidateSelect();
    updateSourceCandidateNote();
  } catch {
    state.sourceCandidates = [];
    sourceCandidateSelectEl.innerHTML = `<option value="">Source candidates unavailable</option>`;
    sourceCandidateNoteEl.textContent = "Source-assisted candidate list is unavailable; manual source text still works.";
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

function renderSourceCandidateSelect() {
  const groups = new Map();
  state.sourceCandidates.forEach((row) => {
    if (!groups.has(row.pack)) {
      groups.set(row.pack, []);
    }
    groups.get(row.pack).push(row);
  });
  sourceCandidateSelectEl.innerHTML = `
    <option value="">Manual source text</option>
    ${Array.from(groups.entries())
      .map(
        ([pack, rows]) => `
          <optgroup label="${escapeHtml(pack)}">
            ${rows
              .map(
                (row) => `
                  <option value="${escapeHtml(sourceCandidateKey(row))}">
                    ${escapeHtml(row.example_id)} - ${escapeHtml(row.labels?.topic || "source candidate")} / ${escapeHtml(statusLabel(row.proposed_fit_class || "unlabeled"))}
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
  if (selected) {
    state.selectedSourceCandidate = null;
    sourceCandidateSelectEl.value = "";
  }
  if (!selected) {
    updateStrictGoldenNote();
    updateSourceCandidateNote();
    return;
  }

  thesisEl.value = selected.source_text;
  resetCurrentRunForLoadedGolden(selected);
  updateStrictGoldenNote();
  updateSourceCandidateNote();
});

sourceCandidateSelectEl.addEventListener("change", () => {
  const selected = state.sourceCandidates.find(
    (row) => sourceCandidateKey(row) === sourceCandidateSelectEl.value
  );
  state.selectedSourceCandidate = selected || null;
  if (selected) {
    state.selectedGolden = null;
    strictGoldenSelectEl.value = "";
  }
  if (!selected) {
    updateSourceCandidateNote();
    updateStrictGoldenNote();
    return;
  }

  thesisEl.value = selected.source_text;
  resetCurrentRunForLoadedSourceCandidate(selected);
  updateSourceCandidateNote();
  updateStrictGoldenNote();
});

thesisEl.addEventListener("input", () => {
  updateStrictGoldenNote();
  updateSourceCandidateNote();
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
  if (state.selectedCandidateId !== state.activeRunCandidateId) {
    state.activeRunCandidateId = null;
  }
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
    ${reviewerRecommendationDraft(run)}
  `;
  bindReviewerRecommendations(run);
  bindRunGovernance();
  renderEval(run);
  renderLedger(run.ledger);
  renderWorkflow();
}

function reviewerRecommendationDraft(run) {
  return `
    <div class="verdicts reviewer-draft" data-reviewer-draft-run-id="${escapeHtml(run.run_id)}">
      <span class="label">Reviewer recommendation (read-only draft)</span>
      <textarea id="reviewer-recommendation-note" rows="4" placeholder="Write a local recommendation for this run. Example: market 1439555 is inverse-directional because No supports the normalized thesis, but horizon and resolution target still need review."></textarea>
      <div class="run-gate-actions">
        <button type="button" data-reviewer-template="inverse_market">Inverse market note</button>
        <button type="button" data-reviewer-template="needs_rules">Needs rules</button>
        <button type="button" data-reviewer-template="weak_proxy">Weak proxy</button>
      </div>
      <p class="trace" data-reviewer-draft-status>
        Draft only for run ${escapeHtml(run.run_id)}. No ledger event, candidate review file, Phoenix Dataset metadata, or expected_outputs.jsonl mutation is written from this note.
      </p>
    </div>
  `;
}

function renderImprovement(improved) {
  const before = improved.before;
  const after = improved.after;
  indexRunMarkets(after);
  const inspectionLabel =
    improved.inspection_source === "phoenix_mcp"
      ? "Phoenix MCP inspection"
      : "Trace inspection fallback";
  resultEl.innerHTML = `
    <div class="inspection">
      <span class="label">${escapeHtml(inspectionLabel)}</span>
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
    ${retrievedMarketContext(after)}
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
  state.activeRunCandidateId = null;
  state.activeRunCandidateDetail = null;
  clearCandidateSelectionForRun();
  resultEl.innerHTML = `<p class="empty">Running current thesis through bounded retrieval, deterministic policy, and Phoenix eval logging.</p>`;
  evalEl.innerHTML = `<p class="empty">Waiting for current run eval.</p>`;
  ledgerEl.innerHTML = "";
}

function resetCurrentRunForLoadedGolden(golden) {
  state.currentRun = null;
  state.activeRunCandidateId = null;
  state.activeRunCandidateDetail = null;
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

function resetCurrentRunForLoadedSourceCandidate(row) {
  state.currentRun = null;
  state.activeRunCandidateId = null;
  state.activeRunCandidateDetail = null;
  improveButton.disabled = true;
  clearCandidateSelectionForRun();
  resultEl.innerHTML = `<p class="empty">Source-assisted candidate loaded from ${escapeHtml(row.pack)} / ${escapeHtml(row.example_id)}. Click Run agent to create a fresh run, trace, and deterministic eval.</p>`;
  evalEl.innerHTML = `<p class="empty">No eval recorded for the loaded source-assisted row.</p>`;
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

function updateSourceCandidateNote() {
  const currentText = normalizeSource(thesisEl.value);
  const selected = state.selectedSourceCandidate;
  if (selected && currentText === normalizeSource(selected.source_text)) {
    sourceCandidateNoteEl.innerHTML = sourceCandidateNote(selected, "is-active");
    sourceCandidateNoteEl.className = "golden-note is-active";
    return;
  }
  if (selected) {
    sourceCandidateNoteEl.textContent = "Edited text no longer exactly matches the source-assisted row; provenance will not be attached to a candidate packet unless the saved source text is restored.";
    sourceCandidateNoteEl.className = "golden-note is-edited";
    return;
  }

  const matched = state.sourceCandidates.find(
    (row) => currentText === normalizeSource(row.source_text)
  );
  if (matched) {
    sourceCandidateNoteEl.innerHTML = sourceCandidateNote(matched, "is-active");
    sourceCandidateNoteEl.className = "golden-note is-active";
    return;
  }

  sourceCandidateNoteEl.textContent = "Manual source text. No source-assisted provenance is attached.";
  sourceCandidateNoteEl.className = "golden-note";
}

function sourceCandidateNote(row) {
  const provenance = row.source_provenance || {};
  const sourceName = provenance.source_name || row.source_name || "unknown source";
  const status = provenance.fetch_status || row.fetch_status || "candidate";
  return `Source-assisted row loaded: ${escapeHtml(row.pack)} / ${escapeHtml(row.example_id)} from ${escapeHtml(sourceName)} (${escapeHtml(status)}). Source/provenance are evidence; proposed fit ${escapeHtml(statusLabel(row.proposed_fit_class || "unlabeled"))} is advisory, not canonical truth.`;
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
      <span class="label">Initial source text</span>
      <p>${escapeHtml(detail.source?.source_text || row.source_text || "")}</p>
    </section>
    ${sourceAssistedPacketBlock(detail.source?.source_assisted)}
    <section class="candidate-copy">
      <span class="label">Normalized thesis</span>
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
    ${candidateEvalTrace(detail)}
  `;
}

function candidateEvalTrace(detail) {
  const row = detail.dataset_export?.row || {};
  const run = detail.run_result || {};
  const metrics = run.eval?.metrics || {};
  const traceId = run.phoenix_trace_id || row.phoenix_trace_id || row.trace_id || "n/a";
  return `
    <section class="candidate-copy">
      <span class="label">Eval trace</span>
      <div class="detail-grid compact">
        ${meta("Run ID", run.run_id || row.run_id || "n/a")}
        ${meta("Trace ID", traceId)}
        ${meta("Fit", run.fit?.semantic_fit_class || row.proposed_fit_class || "n/a")}
        ${meta("False strong", valueOrDefault(metrics.false_strong_recommendation ?? row.false_strong_recommendation, "n/a"))}
        ${meta("Weak proxy", valueOrDefault(metrics.weak_proxy_detected ?? row.weak_proxy_detected, "n/a"))}
        ${meta("Unsupported", valueOrDefault(metrics.unsupported_implication ?? row.unsupported_implication, "n/a"))}
      </div>
      ${
        run.eval?.failure_summary
          ? `<p class="flag-bad">${escapeHtml(run.eval.failure_summary)}</p>`
          : `<p class="flag-good">No eval failure summary recorded for this packet.</p>`
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
        <p>${escapeHtml(promoted ? "Eligible for a later explicit frozen strict-golden promotion. This screen does not write expected_outputs.jsonl." : "Frozen fixture promotion is blocked unless human status is promote. Review status is candidate metadata, not strict truth.")}</p>
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
    ${sourceAssistedPacketBlock(detail.source?.source_assisted)}
    <section class="candidate-copy">
      <span class="label">Record candidate review</span>
      <textarea id="candidate-review-note" rows="4">${escapeHtml(review.reviewer_note || row.reviewer_note || "")}</textarea>
      <div class="run-gate-actions">
        <button type="button" data-candidate-review-status="promote">Promote candidate</button>
        <button type="button" data-candidate-review-status="candidate_only">Candidate only</button>
        <button type="button" data-candidate-review-status="needs_more_rules">Needs rules</button>
        <button type="button" data-candidate-review-status="reject">Reject</button>
      </div>
      <p class="trace">Promote means eligible for later frozen strict-golden promotion. No strict expected labels are written here.</p>
    </section>
  `;
}

function sourceAssistedPacketBlock(sourceAssisted) {
  if (!sourceAssisted) return "";
  const provenance = sourceAssisted.source_provenance || {};
  return `
    <section class="candidate-copy">
      <span class="label">Source-assisted evidence anchor</span>
      <div class="detail-grid compact">
        ${meta("Source row", `${sourceAssisted.pack || "unknown"} / ${sourceAssisted.example_id || "unknown"}`)}
        ${meta("Truth scope", sourceAssisted.source_truth_scope || "source_text_and_provenance_only")}
        ${meta("Source", provenance.source_name || "unknown")}
        ${meta("Fetch status", provenance.fetch_status || "unknown")}
        ${meta("Proposed fit", sourceAssisted.proposed_fit_class || "advisory only")}
        ${meta("Canonical truth", "false")}
      </div>
      ${
        provenance.source_url
          ? `<p class="trace"><a href="${escapeHtml(provenance.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(provenance.source_url)}</a></p>`
          : ""
      }
      <p class="trace">Source-assisted rows anchor source text and provenance only. Proposed fit labels do not write strict expected labels.</p>
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
  workflowScreenEl.querySelectorAll("[data-candidate-review-status]").forEach((button) => {
    button.addEventListener("click", () =>
      recordCandidateReview(button.dataset.candidateReviewStatus)
    );
  });
}

async function recordCandidateReview(status) {
  const detail = state.workflow.detail;
  if (!detail) return;
  const note = document.querySelector("#candidate-review-note")?.value || "";
  const updated = await api(`/api/retrieval-candidates/${encodeURIComponent(detail.case_id)}/review`, {
    method: "POST",
    body: JSON.stringify({
      status,
      note: note || `Human review marked candidate as ${status}.`,
      reviewer: "local_reviewer",
    }),
  });
  bindCandidateDetail(updated, {
    triageDecision: state.workflow.triageDecision ?? "yes",
    reviewDecision: "yes",
    screen: "review",
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
  const scoreById = Object.fromEntries(
    (suggestion?.market_scores || detail.dataset_export?.row?.llm_market_scores || []).map(
      (row) => [row.market_id, row.review_score]
    )
  );
  const recommendedId = fit.recommended_market_id;
  if (markets.length === 0) {
    return `<p class="empty">No retrieved markets recorded.</p>`;
  }
  return `
    <section class="candidate-markets">
      <span class="label">Retrieved markets</span>
      ${markets
        .map((market) =>
          candidateMarketRow(market, rulesById, recommendedId, inspectIds, scoreById)
        )
        .join("")}
    </section>
  `;
}

function candidateMarketRow(market, rulesById, recommendedId, inspectIds, scoreById) {
  const rules = rulesById[market.market_id] || {};
  const rulesStatus = rules.rules_status || (market.resolution_rules ? "present" : "unknown");
  const rulesText = rules.resolution_rules || market.resolution_rules || "";
  const score = scoreById[market.market_id];
  const markers = [
    score === undefined ? null : `score ${score}`,
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
              ${run.fit.supporting_outcome ? meta("Supporting outcome", run.fit.supporting_outcome) : ""}
              ${run.fit.polarity ? meta("Polarity", statusLabel(run.fit.polarity)) : ""}
            </div>
            ${
              resolutionRules
                ? `
                  <details class="rules-details">
                    <summary>Resolution rules</summary>
                    <p>${escapeHtml(resolutionRules)}</p>
                  </details>
                `
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
  const scoreById = currentRunScoreById();
  const hasScores = Object.keys(scoreById).length > 0;
  const orderedMarkets = hasScores
    ? markets
        .map((market, index) => ({ market, index }))
        .sort(
          (left, right) =>
            (scoreById[right.market.market_id] ?? -1) -
              (scoreById[left.market.market_id] ?? -1) || left.index - right.index
        )
        .map((item) => item.market)
    : markets;
  return `
    <section class="run-market-context">
      <span class="label">${hasScores ? "Retrieved candidate markets with advisory scores" : "Retrieved candidate markets"} (${markets.length})</span>
      ${orderedMarkets
        .map((market) => runMarketRow(market, recommendedId, rejectedById, scoreById))
        .join("")}
    </section>
  `;
}

function runMarketRow(market, recommendedId, rejectedById, scoreById = {}) {
  const score = scoreById[market.market_id];
  const markers = [
    score === undefined ? null : `score ${score}`,
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

function currentRunScoreById() {
  const detail = state.activeRunCandidateDetail;
  if (!detail || detail.case_id !== state.activeRunCandidateId) return {};
  const scores = detail.llm_review_suggestion?.market_scores || [];
  return Object.fromEntries(scores.map((row) => [row.market_id, row.review_score]));
}

function runGovernancePrompt() {
  const hasCandidate = Boolean(state.activeRunCandidateId);
  return `
    <section class="run-governance">
      <span class="label">Workflow gates</span>
      <div class="run-question-grid">
        <div class="run-question-card">
          <strong>${hasCandidate ? "LLM triage scores are bound" : "Run LLM triage suggestion?"}</strong>
          <p>${hasCandidate ? `Advisory scores from candidate packet ${escapeHtml(state.activeRunCandidateId)} are shown on the retrieved market rows below.` : "Create a candidate packet from this run and write advisory llm_review_suggestion.json with market ranking scores."}</p>
          <div class="run-gate-actions">
            ${
              hasCandidate
                ? `<button type="button" data-scroll-run-markets>Show scored markets</button>`
                : `<button type="button" data-create-run-triage>Yes, score markets</button>`
            }
            <button type="button" data-run-gate-skip>No</button>
          </div>
        </div>
        <div class="run-question-card">
          <strong>Review candidate for promotion?</strong>
          <p>Review writes review_decision.json for a candidate packet. Promote means eligible for later frozen strict-golden promotion; this UI does not mutate expected_outputs.jsonl.</p>
          <div class="run-gate-actions">
            ${
              hasCandidate
                ? `<button type="button" data-open-active-candidate="review">Yes, review packet</button>`
                : `<button type="button" data-create-run-review>Yes, create packet</button>`
            }
            <button type="button" data-run-review-skip>No</button>
          </div>
        </div>
      </div>
      <p class="trace" id="run-gate-note">${hasCandidate ? "Current run has an explicit candidate packet. LLM triage remains advisory; human review controls candidate promotion status." : "New theses start as current runs. Create a candidate packet only if you want advisory triage or promotion review."}</p>
    </section>
  `;
}

function bindRunGovernance() {
  document.querySelectorAll("[data-create-run-triage]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.currentRun) return;
      await createCandidateFromCurrentRun({ runTriage: true, openScreen: "triage" });
    });
  });
  document.querySelectorAll("[data-create-run-review]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.currentRun) return;
      await createCandidateFromCurrentRun({ runTriage: false, openScreen: "review" });
    });
  });
  document.querySelectorAll("[data-open-active-candidate]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.activeRunCandidateId) return;
      const detail = await api(`/api/retrieval-candidates/${encodeURIComponent(state.activeRunCandidateId)}`);
      bindCandidateDetail(detail, {
        triageDecision: "yes",
        reviewDecision: button.dataset.openActiveCandidate === "review" ? "yes" : null,
        screen: button.dataset.openActiveCandidate,
      });
    });
  });
  document.querySelectorAll("[data-scroll-run-markets]").forEach((button) => {
    button.addEventListener("click", () => {
      const markets = document.querySelector(".run-market-context");
      if (markets) {
        markets.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
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
        note.textContent = "Skipped advisory triage. The deterministic run and Phoenix eval remain visible above.";
      }
    });
  });
  document.querySelectorAll("[data-run-review-skip]").forEach((button) => {
    button.addEventListener("click", () => {
      const note = document.querySelector("#run-gate-note");
      if (note) {
        note.textContent = "Skipped promotion review. No candidate review status or strict fixture is created from this choice.";
      }
    });
  });
}

async function createCandidateFromCurrentRun({ runTriage, openScreen }) {
  const note = document.querySelector("#run-gate-note");
  if (note) {
    note.textContent = runTriage
      ? "Creating a candidate packet and writing advisory llm_review_suggestion.json."
      : "Creating a candidate packet for human promotion review.";
  }
  let detail = await api("/api/current-run-candidates", {
    method: "POST",
    body: JSON.stringify({
      source_text: thesisEl.value,
      run: state.currentRun,
      source_assisted: currentSourceAssistedRef(),
    }),
  });
  if (runTriage) {
    detail = await api(`/api/retrieval-candidates/${encodeURIComponent(detail.case_id)}/triage`, {
      method: "POST",
    });
  }
  state.activeRunCandidateId = detail.case_id;
  state.activeRunCandidateDetail = detail;
  if (openScreen === "review") {
    ensureCandidateOption(detail.case_id);
    bindCandidateDetail(detail, {
      triageDecision: runTriage ? "yes" : "no",
      reviewDecision: "yes",
      screen: "review",
    });
  } else if (state.currentRun) {
    state.selectedCandidateId = null;
    if (candidateSelectEl) {
      candidateSelectEl.value = "";
    }
    resetWorkflowChoices();
    renderRun(state.currentRun);
    const updatedNote = document.querySelector("#run-gate-note");
    if (updatedNote) {
      updatedNote.textContent = `Bound current run to candidate packet ${detail.case_id}. Advisory scores are shown on the retrieved market rows; promotion review is still unopened.`;
    }
  }
}

function currentSourceAssistedRef() {
  const selected = state.selectedSourceCandidate;
  if (!selected) return null;
  if (normalizeSource(thesisEl.value) !== normalizeSource(selected.source_text)) {
    return null;
  }
  return {
    source_case_key: selected.source_case_key,
    pack: selected.pack,
    example_id: selected.example_id,
    source_type: selected.source_type,
    as_of_ts: selected.as_of_ts,
    source_provenance: selected.source_provenance || {},
    labels: selected.labels || {},
    market_snapshot_ref: selected.market_snapshot_ref || {},
    market_rules_snapshot_ref: selected.market_rules_snapshot_ref || {},
    proposed_fit_class: selected.proposed_fit_class || null,
    proposed_best_market_id: selected.proposed_best_market_id || null,
    canonical_truth: false,
    source_truth_scope: "source_text_and_provenance_only",
  };
}

function bindCandidateDetail(detail, { triageDecision, reviewDecision, screen }) {
  state.selectedCandidateId = detail.case_id;
  ensureCandidateOption(detail.case_id);
  candidateSelectEl.value = detail.case_id;
  state.workflow = {
    detail,
    triageDecision,
    reviewDecision,
    screen,
  };
  renderWorkflow();
  document.querySelector(".candidate-workbench")?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function ensureCandidateOption(caseId) {
  if ([...candidateSelectEl.options].some((option) => option.value === caseId)) return;
  const option = document.createElement("option");
  option.value = caseId;
  option.textContent = caseId;
  candidateSelectEl.appendChild(option);
}

function bindReviewerRecommendations(run) {
  const draft = document.querySelector("[data-reviewer-draft-run-id]");
  if (!draft) return;
  const note = draft.querySelector("#reviewer-recommendation-note");
  const status = draft.querySelector("[data-reviewer-draft-status]");
  const normalizedThesis = run.claim?.claim_text || "the normalized thesis";
  const templates = {
    inverse_market: `Recommendation draft: inspect whether one retrieved market is an inverse expression of "${normalizedThesis}". If the market's No outcome supports the thesis and the inverted market directly matches the normalized thesis, record semantic_fit_class=direct, polarity=inverse, and supporting_outcome=No.`,
    needs_rules: `Recommendation draft: keep this as needs_more_rules until the market resolution text proves the same entity, event, horizon, and polarity as "${normalizedThesis}".`,
    weak_proxy: `Recommendation draft: classify the recommended market as weak_proxy if it is adjacent evidence but can resolve for reasons unrelated to "${normalizedThesis}".`,
  };
  draft.querySelectorAll("[data-reviewer-template]").forEach((button) => {
    button.addEventListener("click", () => {
      note.value = templates[button.dataset.reviewerTemplate] || "";
      if (status) {
        status.textContent = "Draft updated locally only. Use candidate promotion review to persist a human decision.";
      }
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
      ${metrics.previous_trace_id ? meta("Previous trace", metrics.previous_trace_id) : ""}
      ${metrics.inspection_source ? meta("Inspection", metrics.inspection_source) : ""}
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
      ${metric("Causal mismatch", metrics.causal_mechanism_mismatch, true)}
      ${metric("Target mismatch", metrics.resolution_target_mismatch, true)}
      ${metric("Repair candidate", metrics.trace_repair_candidate, true)}
      ${metric("Repair gate", metrics.trace_repair_gate_applied)}
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

function valueOrDefault(value, fallback) {
  return value === null || value === undefined ? fallback : value;
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

function sourceCandidateKey(row) {
  return row.source_case_key || `${row.pack}::${row.example_id}`;
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
loadSourceCandidates();
loadCandidates();
