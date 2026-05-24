const state = {
  currentRun: null,
};

const statusEl = document.querySelector("#service-status");
const resultEl = document.querySelector("#result");
const evalEl = document.querySelector("#eval-summary");
const ledgerEl = document.querySelector("#ledger-events");
const improveButton = document.querySelector("#improve-button");
const runButton = document.querySelector("#run-button");

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

document.querySelector("#run-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  runButton.disabled = true;
  runButton.textContent = "Running";
  improveButton.disabled = true;
  const thesis = document.querySelector("#thesis").value;
  const promptVersion = document.querySelector("#prompt-version").value;
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

function renderRun(run) {
  improveButton.disabled = false;
  resultEl.innerHTML = `
    <p class="claim-text">${escapeHtml(run.claim.claim_text)}</p>
    <span class="fit-class">${escapeHtml(run.fit.semantic_fit_class)}</span>
    <div class="meta-grid">
      ${meta("Entities", run.claim.entities.join(", ") || "Unspecified")}
      ${meta("Horizon", run.claim.horizon)}
      ${meta("Stance", run.claim.stance)}
      ${meta("Recommended market", run.fit.recommended_market_id || "None")}
    </div>
    <div class="market">
      <span class="label">Fit reason</span>
      <p>${escapeHtml(run.fit.fit_reason)}</p>
      ${list("Captures", run.fit.captures)}
      ${list("Misses", run.fit.misses)}
      ${list("Rejected markets", run.fit.rejected_markets.map((item) => `${item.market_id}: ${item.reason}`))}
    </div>
    <div class="verdicts" data-claim-id="${run.claim_id}">
      <button type="button" data-verdict="verify">Verify</button>
      <button type="button" data-verdict="reject">Reject</button>
      <button type="button" data-verdict="needs_review">Needs review</button>
      <button type="button" data-verdict="corrected">Correct to weak proxy</button>
    </div>
  `;
  bindVerdicts();
  renderEval(run);
  renderLedger(run.ledger);
}

function renderImprovement(improved) {
  const before = improved.before;
  const after = improved.after;
  resultEl.innerHTML = `
    <div class="inspection">
      <span class="label">Phoenix MCP inspection</span>
      <p>${escapeHtml(improved.inspection.summary)}</p>
      <p class="trace">source=${escapeHtml(improved.inspection.source)} trace=${escapeHtml(improved.inspection.phoenix_trace_id)}</p>
    </div>
    <div class="meta-grid">
      ${meta("Before", `${before.fit.semantic_fit_class} / false strong: ${before.eval.metrics.false_strong_recommendation}`)}
      ${meta("After", `${after.fit.semantic_fit_class} / false strong: ${after.eval.metrics.false_strong_recommendation}`)}
    </div>
    <p class="claim-text">${escapeHtml(after.claim.claim_text)}</p>
    <span class="fit-class">${escapeHtml(after.fit.semantic_fit_class)}</span>
    <div class="market">
      <span class="label">Revised fit reason</span>
      <p>${escapeHtml(after.fit.fit_reason)}</p>
      ${list("Misses", after.fit.misses)}
    </div>
  `;
  renderEval(after);
  renderLedger(after.ledger);
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
      ${metric("Weak proxy", metrics.weak_proxy_detected)}
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

checkHealth();
