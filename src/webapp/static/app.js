const stateEl = document.getElementById("runState");
const titleEl = document.getElementById("resultTitle");
const verdictEl = document.getElementById("metricVerdict");
const rowsEl = document.getElementById("metricRows");
const issuesEl = document.getElementById("metricIssues");
const missingEl = document.getElementById("metricMissing");
const duplicatesEl = document.getElementById("metricDuplicates");
const guardrailEl = document.getElementById("metricGuardrail");
const fileListEl = document.getElementById("fileList");
const reportEl = document.getElementById("reportPreview");
const resultStackEl = document.getElementById("resultStack");
const serviceStatusEl = document.getElementById("serviceStatus");
const sampleListEl = document.getElementById("sampleList");
const singleForm = document.getElementById("singleForm");
const multiForm = document.getElementById("multiForm");
const cancelJobButton = document.getElementById("cancelJob");
const retryJobButton = document.getElementById("retryJob");
let activeJobId = null;
let pollToken = 0;

function isTerminalStatus(status) {
  return ["completed", "failed", "cancelled"].includes(status);
}

function setRunState(kind, label) {
  stateEl.className = `run-state ${kind}`;
  stateEl.textContent = label;
}

function setButtonsDisabled(disabled) {
  document.querySelectorAll(".primary-action, .sample-run").forEach((button) => {
    button.disabled = disabled;
  });
}

function formatInteger(value) {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("en-US").format(number) : "-";
}

function formatDecimal(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "-";
}

function clearStructuredResults(message = "Pipeline is running.") {
  resultStackEl.replaceChildren();
  const panel = document.createElement("section");
  panel.className = "insight-panel empty-state";
  panel.appendChild(textEl("h3", "", "Run summary"));
  panel.appendChild(textEl("p", "", message));
  resultStackEl.appendChild(panel);
}

function setLoading(title) {
  titleEl.textContent = title;
  setRunState("running", "Running");
  setButtonsDisabled(true);
  cancelJobButton.disabled = true;
  retryJobButton.disabled = true;
  verdictEl.textContent = "-";
  rowsEl.textContent = "-";
  issuesEl.textContent = "-";
  missingEl.textContent = "-";
  duplicatesEl.textContent = "-";
  guardrailEl.textContent = "-";
  clearStructuredResults("The job is queued. Results will appear here as soon as the pipeline finishes.");
}

function setError(message) {
  titleEl.textContent = "Run failed";
  setRunState("failed", "Failed");
  reportEl.textContent = message || "Pipeline failed.";
  clearStructuredResults(message || "Pipeline failed.");
  setButtonsDisabled(false);
  cancelJobButton.disabled = true;
  retryJobButton.disabled = !activeJobId;
}

function verdictSummary(payload) {
  const verdict = payload.dataset_verdict || {};
  const meta = verdict.dataset_meta || {};
  const summary = verdict.summary || {};
  const guardrail = payload.guardrail_report || {};
  verdictEl.textContent = verdict.verdict || "-";
  rowsEl.textContent = formatInteger(meta.n);
  issuesEl.textContent = formatInteger(summary.total_issues);
  missingEl.textContent = formatPercent(meta.p_cells_missing);
  duplicatesEl.textContent = Number.isFinite(Number(meta.n_duplicates))
    ? `${formatInteger(meta.n_duplicates)} (${formatPercent(meta.p_duplicates)})`
    : "-";
  guardrailEl.textContent = guardrail.status || "-";
}

function renderFiles(payload) {
  const links = payload.links || {};
  const names = Object.keys(links);
  fileListEl.innerHTML = "";
  fileListEl.classList.toggle("empty", names.length === 0);
  if (names.length === 0) {
    fileListEl.textContent = "No output files";
    return;
  }
  names.forEach((name) => {
    const link = document.createElement("a");
    link.href = links[name];
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = name;
    fileListEl.appendChild(link);
  });
}

function updateJobActions(payload) {
  const status = payload.status || "idle";
  activeJobId = payload.job_id || activeJobId;
  cancelJobButton.disabled = !activeJobId || isTerminalStatus(status);
  retryJobButton.disabled = !activeJobId || !isTerminalStatus(status);
}

function renderJobProgress(payload) {
  titleEl.textContent = `Job ${payload.job_id}`;
  const status = payload.status || "running";
  const progress = Math.round(Number(payload.progress || 0) * 100);
  setRunState(status === "queued" ? "queued" : "running", `${status} ${progress}%`);
  verdictSummary(payload);
  renderFiles(payload);
  clearStructuredResults(payload.message || "Pipeline is running.");
  reportEl.textContent = payload.report || payload.message || "Pipeline is running.";
  updateJobActions(payload);
}

function renderResult(payload) {
  titleEl.textContent = `Job ${payload.job_id}`;
  if (payload.status === "cancelled") {
    setRunState("failed", "Cancelled");
  } else {
    setRunState(payload.status === "failed" ? "failed" : "done", payload.status === "failed" ? "Failed" : "Done");
  }
  verdictSummary(payload);
  renderFiles(payload);
  const error = payload.error || {};
  reportEl.textContent = payload.report || error.detail || payload.message || "No report generated.";
  renderStructuredResults(payload);
  setButtonsDisabled(false);
  updateJobActions(payload);
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function pollJob(jobId, token) {
  while (token === pollToken) {
    await sleep(750);
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.detail || `HTTP ${response.status}`);
      return;
    }
    if (isTerminalStatus(payload.status)) {
      renderResult(payload);
      return;
    }
    renderJobProgress(payload);
  }
}

function handleJobPayload(payload) {
  activeJobId = payload.job_id;
  updateJobActions(payload);
  if (isTerminalStatus(payload.status)) {
    renderResult(payload);
    return;
  }
  renderJobProgress(payload);
  pollToken += 1;
  pollJob(payload.job_id, pollToken);
}

async function submitForm(form, endpoint, title) {
  setLoading(title);
  const formData = new FormData(form);
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok || payload.status === "failed") {
      setError(payload.detail || `HTTP ${response.status}`);
      return;
    }
    handleJobPayload(payload);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
}

function textEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) {
    el.className = className;
  }
  el.textContent = text;
  return el;
}

function createPanel(title, subtitle) {
  const panel = document.createElement("section");
  panel.className = "insight-panel";
  const header = document.createElement("div");
  header.className = "insight-heading";
  header.appendChild(textEl("h3", "", title));
  if (subtitle) {
    header.appendChild(textEl("p", "", subtitle));
  }
  panel.appendChild(header);
  return panel;
}

function severityBadge(value) {
  const badge = document.createElement("span");
  const safe = String(value || "INFO").toLowerCase();
  badge.className = `severity-badge severity-${safe}`;
  badge.textContent = value || "INFO";
  return badge;
}

function makeTable(columns, rows, emptyText) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrap";
  if (!rows.length) {
    wrapper.classList.add("empty-table");
    wrapper.textContent = emptyText;
    return wrapper;
  }
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((column) => {
    headRow.appendChild(textEl("th", "", column.label));
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      const value = column.render ? column.render(row) : row[column.key];
      if (value instanceof Node) {
        td.appendChild(value);
      } else {
        td.textContent = value === undefined || value === null || value === "" ? "-" : String(value);
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

function issueScope(issue) {
  return issue.affected_column || issue.affected_table || "dataset";
}

function getDataQualityIssues(dataQuality) {
  if (!dataQuality) {
    return [];
  }
  if (dataQuality.schema_version === "multi_table_data_quality_v1") {
    return dataQuality.combined_findings?.anomalies || [];
  }
  return dataQuality.anomalies || [];
}

function renderVerdictPanel(payload) {
  const verdict = payload.dataset_verdict || {};
  const meta = verdict.dataset_meta || {};
  const summary = verdict.summary || {};
  const panel = createPanel("Verdict", "Decision summary from deterministic findings.");

  const verdictLine = document.createElement("div");
  verdictLine.className = "verdict-line";
  verdictLine.appendChild(severityBadge(verdict.verdict || "UNKNOWN"));
  verdictLine.appendChild(textEl("p", "", verdict.verdict_rationale || payload.message || "No verdict rationale emitted."));
  panel.appendChild(verdictLine);

  const facts = document.createElement("div");
  facts.className = "fact-grid";
  [
    ["Rows", formatInteger(meta.n)],
    ["Columns", formatInteger(meta.n_var)],
    ["Total issues", formatInteger(summary.total_issues)],
    ["Critical", formatInteger(summary.critical)],
    ["High", formatInteger(summary.high)],
    ["Warn", formatInteger(summary.warn)],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.appendChild(textEl("span", "", label));
    item.appendChild(textEl("strong", "", value));
    facts.appendChild(item);
  });
  panel.appendChild(facts);

  if (meta.is_sampled) {
    const note = textEl(
      "p",
      "sample-note",
      `Profiled ${formatInteger(meta.sample_n)} sampled rows from ${formatInteger(meta.original_n)} original rows (${meta.sample_method || "sampling"}, seed ${meta.sample_seed ?? "-"}).`
    );
    panel.appendChild(note);
  }
  return panel;
}

function renderTopIssuesPanel(payload) {
  const verdict = payload.dataset_verdict || {};
  const panel = createPanel("Top Issues", "The issues that drive the current verdict.");
  panel.appendChild(makeTable(
    [
      { label: "Severity", render: (issue) => severityBadge(issue.effective_severity || issue.severity) },
      { label: "Type", key: "issue_type" },
      { label: "Scope", render: issueScope },
      { label: "Affected", render: (issue) => formatInteger(issue.affected_count) },
      { label: "Reason", key: "rationale" },
    ],
    (verdict.top_issues || []).slice(0, 10),
    "No top issues emitted."
  ));
  return panel;
}

function renderDataQualityPanel(payload) {
  const issues = getDataQualityIssues(payload.data_quality_findings).slice(0, 12);
  const panel = createPanel("Data Quality Findings", "Column and row-level findings from L1-L2.5.");
  panel.appendChild(makeTable(
    [
      { label: "Severity", render: (issue) => severityBadge(issue.compound_severity || issue.severity) },
      { label: "Type", key: "issue_type" },
      { label: "Scope", render: issueScope },
      { label: "Affected", render: (issue) => `${formatInteger(issue.affected_count)} (${formatPercent(issue.affected_percent)})` },
      { label: "Export", render: (issue) => issue.full_anomalies_export_path ? "available" : "-" },
    ],
    issues,
    "No data quality issues emitted."
  ));
  return panel;
}

function renderSchemaPanel(payload) {
  const schema = payload.schema_evaluation_findings || {};
  const relationships = schema.relationships || [];
  const errors = schema.integrity_errors || [];
  const panel = createPanel("Schema & Relationships", "Inferred or explicit table relationships and schema issues.");
  panel.appendChild(makeTable(
    [
      { label: "Status", key: "status" },
      { label: "Decision", render: (rel) => rel.decision || "-" },
      { label: "Bucket", render: (rel) => rel.confidence_bucket || "-" },
      {
        label: "Relationship",
        render: (rel) => `${rel.child_table}.${rel.child_column} -> ${rel.parent_table}.${rel.parent_column}`,
      },
      { label: "Evidence", render: (rel) => (rel.evidence || []).join("; ") },
    ],
    relationships.slice(0, 10),
    "No relationships emitted."
  ));

  if (errors.length) {
    const subheading = textEl("h4", "", "Schema issues");
    panel.appendChild(subheading);
    panel.appendChild(makeTable(
      [
        { label: "Severity", render: (issue) => severityBadge(issue.compound_severity || issue.severity) },
        { label: "Type", key: "error_type" },
        { label: "Scope", render: issueScope },
        { label: "Affected", render: (issue) => formatInteger(issue.affected_count) },
        { label: "Description", key: "description" },
      ],
      errors.slice(0, 10),
      "No schema issues emitted."
    ));
  }
  return panel;
}

function basename(path) {
  return String(path || "").split(/[\\/]/).pop();
}

function renderCrossTablePanel(payload) {
  const analysis = payload.cross_table_analysis;
  if (!analysis) {
    return null;
  }
  const panel = createPanel("Cross-table Analysis", "Safe joined dataset and numeric cross-table correlations.");

  const facts = document.createElement("div");
  facts.className = "fact-grid";
  [
    ["Status", analysis.status || "-"],
    ["Fact table", analysis.fact_table || "-"],
    ["Rows", formatInteger(analysis.denormalized_rows)],
    ["Columns", formatInteger(analysis.denormalized_columns)],
    ["Analysis rows", formatInteger(analysis.analysis_rows)],
    ["Deduped rows", formatInteger(analysis.exact_duplicate_rows_removed)],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.appendChild(textEl("span", "", label));
    item.appendChild(textEl("strong", "", value));
    facts.appendChild(item);
  });
  panel.appendChild(facts);

  const previewName = basename(analysis.preview_csv_path);
  if (previewName && payload.links?.[previewName]) {
    const preview = document.createElement("p");
    preview.className = "sample-note";
    preview.append("Preview CSV: ");
    const link = document.createElement("a");
    link.href = payload.links[previewName];
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = previewName;
    preview.appendChild(link);
    panel.appendChild(preview);
  }

  const joinHeading = textEl("h4", "", "Safe join steps");
  panel.appendChild(joinHeading);
  panel.appendChild(makeTable(
    [
      { label: "Status", key: "status" },
      {
        label: "Relationship",
        render: (step) => `${step.child_table}.${step.child_column} -> ${step.parent_table}.${step.parent_column}`,
      },
      { label: "Rows", render: (step) => `${formatInteger(step.before_rows)} -> ${formatInteger(step.after_rows)}` },
      { label: "Match", render: (step) => formatPercent(step.match_rate) },
      { label: "Added cols", render: (step) => formatInteger((step.added_columns || []).length) },
      { label: "Warnings", render: (step) => (step.warnings || []).join("; ") || "-" },
    ],
    analysis.join_steps || [],
    "No safe join steps emitted."
  ));

  const corrHeading = textEl("h4", "", "Top numeric correlations");
  panel.appendChild(corrHeading);
  panel.appendChild(makeTable(
    [
      { label: "Coefficient", render: (corr) => formatDecimal(corr.coefficient, 4) },
      { label: "Left", key: "left_feature" },
      { label: "Right", key: "right_feature" },
      { label: "N", render: (corr) => formatInteger(corr.n) },
      { label: "Method", key: "method" },
    ],
    analysis.correlations || [],
    "No cross-table numeric correlations passed the MVP filters."
  ));

  if ((analysis.warnings || []).length) {
    const warningList = document.createElement("ul");
    warningList.className = "warning-list";
    analysis.warnings.slice(0, 8).forEach((warning) => {
      warningList.appendChild(textEl("li", "", warning));
    });
    panel.appendChild(warningList);
  }
  return panel;
}

function renderChartsPanel(payload) {
  const links = payload.links || {};
  const chartNames = Object.keys(links).filter((name) => name.toLowerCase().endsWith(".png"));
  if (!chartNames.length) {
    return null;
  }
  const panel = createPanel("Diagnostic Charts", "Generated chart artifacts shown directly from L3.5.");
  const grid = document.createElement("div");
  grid.className = "chart-grid";
  chartNames.forEach((name) => {
    const link = document.createElement("a");
    link.href = links[name];
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "chart-card";
    const img = document.createElement("img");
    img.src = links[name];
    img.alt = name;
    img.loading = "lazy";
    link.appendChild(img);
    link.appendChild(textEl("span", "", name));
    grid.appendChild(link);
  });
  panel.appendChild(grid);
  return panel;
}

function renderArtifactPanel(payload) {
  const manifest = payload.artifact_manifest || {};
  const artifacts = manifest.artifacts || [];
  const links = payload.links || {};
  const panel = createPanel("Artifacts", "Machine-readable outputs and exported rows.");
  panel.appendChild(makeTable(
    [
      { label: "Kind", key: "kind" },
      { label: "Layer", key: "source_layer" },
      {
        label: "File",
        render: (artifact) => {
          const link = document.createElement("a");
          link.href = links[artifact.path] || "#";
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = artifact.path;
          if (!links[artifact.path]) {
            link.removeAttribute("href");
          }
          return link;
        },
      },
    ],
    artifacts,
    "No artifact manifest emitted."
  ));
  return panel;
}

function renderStructuredResults(payload) {
  resultStackEl.replaceChildren();
  if (payload.status === "failed") {
    clearStructuredResults(payload.error?.detail || payload.message || "Pipeline failed.");
    return;
  }
  const panels = [
    renderVerdictPanel(payload),
    renderTopIssuesPanel(payload),
    renderDataQualityPanel(payload),
    renderSchemaPanel(payload),
    renderCrossTablePanel(payload),
    renderChartsPanel(payload),
    renderArtifactPanel(payload),
  ].filter(Boolean);
  panels.forEach((panel) => resultStackEl.appendChild(panel));
}

function renderExamples(examples) {
  sampleListEl.classList.remove("loading", "empty");
  sampleListEl.replaceChildren();
  if (!Array.isArray(examples) || examples.length === 0) {
    sampleListEl.classList.add("empty");
    sampleListEl.textContent = "No samples found";
    return;
  }

  examples.forEach((example) => {
    const item = document.createElement("article");
    item.className = "sample-item";

    const meta = document.createElement("div");
    meta.className = "sample-meta";
    meta.appendChild(textEl("strong", "", example.title || example.id));

    const detail = textEl(
      "span",
      "",
      `${example.mode || "single"} · ${(example.formats || []).join(", ")}`
    );
    meta.appendChild(detail);

    const issues = document.createElement("div");
    issues.className = "issue-tags";
    (example.error_profile || []).slice(0, 4).forEach((issue) => {
      issues.appendChild(textEl("span", "", issue));
    });
    meta.appendChild(issues);

    const button = document.createElement("button");
    button.className = "sample-run";
    button.type = "button";
    button.dataset.exampleId = example.id;
    button.dataset.exampleMode = example.mode || "single";
    button.textContent = "Run";
    button.addEventListener("click", () => {
      runExample(example);
    });

    item.appendChild(meta);
    item.appendChild(button);
    sampleListEl.appendChild(item);
  });
}

async function loadExamples() {
  try {
    const response = await fetch("/api/examples");
    const payload = await response.json();
    if (!response.ok) {
      sampleListEl.classList.add("empty");
      sampleListEl.textContent = payload.detail || "Cannot load samples";
      return;
    }
    renderExamples(payload.examples);
  } catch (error) {
    sampleListEl.classList.add("empty");
    sampleListEl.textContent = error instanceof Error ? error.message : String(error);
  }
}

async function runExample(example) {
  setLoading(example.title || "Sample dataset");
  const quick = example.mode === "single" && singleForm.elements.profiling_minimal.checked;
  const endpoint = `/api/examples/${encodeURIComponent(example.id)}/run?profiling_minimal=${quick}`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok || payload.status === "failed") {
      setError(payload.detail || `HTTP ${response.status}`);
      return;
    }
    handleJobPayload(payload);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
}

cancelJobButton.addEventListener("click", async () => {
  if (!activeJobId) {
    return;
  }
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(activeJobId)}/cancel`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.detail || `HTTP ${response.status}`);
      return;
    }
    if (isTerminalStatus(payload.status)) {
      renderResult(payload);
    } else {
      renderJobProgress(payload);
    }
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
});

retryJobButton.addEventListener("click", async () => {
  if (!activeJobId) {
    return;
  }
  setLoading("Retrying pipeline");
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(activeJobId)}/retry`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.detail || `HTTP ${response.status}`);
      return;
    }
    handleJobPayload(payload);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const mode = tab.dataset.mode;
    document.querySelectorAll(".tab").forEach((other) => {
      const isActive = other === tab;
      other.classList.toggle("active", isActive);
      other.setAttribute("aria-selected", String(isActive));
    });
    singleForm.classList.toggle("hidden", mode !== "single");
    multiForm.classList.toggle("hidden", mode !== "multi");
  });
});

singleForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(singleForm, "/api/jobs", "Single-table pipeline");
});

multiForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(multiForm, "/api/jobs/multi", "Multi-table pipeline");
});

fetch("/health")
  .then((response) => response.json())
  .then((payload) => {
    serviceStatusEl.textContent = payload.status === "ok" ? "Online" : "Degraded";
  })
  .catch(() => {
    serviceStatusEl.textContent = "Offline";
  });

loadExamples();
