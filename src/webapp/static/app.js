const stateEl = document.getElementById("runState");
const titleEl = document.getElementById("resultTitle");
const verdictEl = document.getElementById("metricVerdict");
const rowsEl = document.getElementById("metricRows");
const issuesEl = document.getElementById("metricIssues");
const fileListEl = document.getElementById("fileList");
const reportEl = document.getElementById("reportPreview");
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

function setLoading(title) {
  titleEl.textContent = title;
  setRunState("running", "Running");
  setButtonsDisabled(true);
  cancelJobButton.disabled = true;
  retryJobButton.disabled = true;
}

function setError(message) {
  titleEl.textContent = "Run failed";
  setRunState("failed", "Failed");
  reportEl.textContent = message || "Pipeline failed.";
  setButtonsDisabled(false);
  cancelJobButton.disabled = true;
  retryJobButton.disabled = !activeJobId;
}

function verdictSummary(payload) {
  const verdict = payload.dataset_verdict || {};
  const meta = verdict.dataset_meta || {};
  const summary = verdict.summary || {};
  verdictEl.textContent = verdict.verdict || "-";
  rowsEl.textContent = Number.isFinite(meta.n) ? String(meta.n) : "-";
  issuesEl.textContent = Number.isFinite(summary.total_issues) ? String(summary.total_issues) : "-";
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
