const state = {
  status: null,
  endpoints: null,
};

const qs = (selector) => document.querySelector(selector);

function setBusy(button, busy) {
  button.disabled = busy;
  button.classList.toggle("is-busy", busy);
  button.setAttribute("aria-busy", String(busy));
  const label = button.querySelector(".button-label");
  if (label) {
    label.dataset.originalText ??= label.textContent;
    label.textContent = busy ? `${button.dataset.busyLabel || "Working"}...` : label.dataset.originalText;
    return;
  }
  button.dataset.originalText ??= button.textContent;
  button.textContent = busy ? `${button.dataset.busyLabel || "Working"}...` : button.dataset.originalText;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function pillClass(ok) {
  if (ok === true) return "status-pill ready";
  if (ok === false) return "status-pill error";
  return "status-pill attention";
}

function statusLabel(ok) {
  if (ok === true) return "Ready";
  if (ok === false) return "Needs attention";
  return "Unknown";
}

function itemByLabel(payload, label) {
  return payload.items.find((item) => item.label === label);
}

function connectedPhoneName(payload) {
  const phone = itemByLabel(payload, "Phone");
  const match = phone?.detail.match(/\(([^)]+)\)/);
  return match ? match[1] : null;
}

function serverIsRunning(payload) {
  return itemByLabel(payload, "USB tunnel")?.ok === true && itemByLabel(payload, "Ollama")?.ok === true;
}

function updateStartButton(payload) {
  const button = qs("#tunnelButton");
  const label = button.querySelector(".button-label");
  if (button.getAttribute("aria-busy") === "true") {
    return;
  }

  const running = serverIsRunning(payload);
  button.classList.toggle("is-running", running);
  button.setAttribute("aria-pressed", String(running));
  button.title = running ? "AI server is already reachable from this computer." : "Start the local AI server tunnel.";
  label.textContent = running ? "AI Server Running" : "Start AI Server";
  label.dataset.originalText = label.textContent;
}

function renderStatus(payload) {
  state.status = payload;
  const grid = qs("#statusGrid");
  grid.innerHTML = "";

  payload.items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "status-card";
    card.innerHTML = `
      <span class="${pillClass(item.ok)}">${statusLabel(item.ok)}</span>
      <h3>${item.label}</h3>
      <p>${item.detail}</p>
    `;
    grid.append(card);
  });

  const sidebarSignal = qs("#sidebarSignal");
  const sidebarStatus = qs("#sidebarStatus");
  sidebarSignal.className = `signal-dot ${payload.ok ? "ready" : "attention"}`;
  sidebarStatus.textContent = payload.ok ? "System ready" : "Attention needed";
  qs("#readinessTitle").textContent = payload.ok ? "Ready for local coding" : "Some pieces need attention";
  qs("#readinessDetail").textContent = payload.ok
    ? "Phone, tunnel, Ollama, and IDE checks are aligned."
    : "Use the cards below to see which part needs a nudge.";
  const hostPhone = connectedPhoneName(payload);
  const hostPhoneText = hostPhone ? `Hosting phone: ${hostPhone}` : "Hosting phone: not connected";
  qs("#hostPhonePill").textContent = hostPhoneText;
  qs("#topbarHostPhone").textContent = hostPhoneText;
  updateStartButton(payload);
}

function endpointRow(label, url) {
  return `<div class="endpoint-row"><span>${label}</span><code>${url}</code></div>`;
}

function renderModels(container, models) {
  if (!models || models.length === 0) {
    container.innerHTML = '<div class="model-chip"><span>Models</span><code>none detected</code></div>';
    return;
  }
  container.innerHTML = models.map((model) => `<div class="model-chip"><span>Model</span><code>${model}</code></div>`).join("");
}

function renderEndpoints(payload) {
  state.endpoints = payload;
  const ollama = payload.ollama;
  const pill = qs("#ollamaEndpointPill");
  pill.className = pillClass(ollama.ok);
  pill.textContent = statusLabel(ollama.ok);
  qs("#ollamaEndpointList").innerHTML = [
    endpointRow("Models", ollama.modelsUrl),
    endpointRow("Generate", ollama.generateUrl),
  ].join("");
  renderModels(qs("#ollamaModels"), ollama.models);

  const nativeList = qs("#nativeEndpointList");
  const nativeModels = qs("#nativeModels");
  if (!payload.native) {
    nativeList.innerHTML = '<div class="endpoint-row"><span>Status</span><code>not configured</code></div>';
    nativeModels.innerHTML = "";
    return;
  }

  const native = payload.native;
  nativeList.innerHTML = [
    endpointRow("Health", native.healthUrl),
    endpointRow("Models", native.modelsUrl),
    endpointRow("Completion", native.completionUrl),
    endpointRow("State", native.loading ? "loading" : statusLabel(native.ok).toLowerCase()),
  ].join("");
  renderModels(nativeModels, native.models);
}

async function refreshStatus() {
  try {
    const status = await requestJson("/api/status");
    renderStatus(status);
    await refreshEndpoints();
  } catch (error) {
    qs("#activityLog").textContent = error.message;
  }
}

async function refreshEndpoints() {
  const ollamaBase = encodeURIComponent(qs("#ollamaBase").value.trim() || "http://127.0.0.1:11434");
  const nativeEnabled = qs("#nativeEnabled").checked;
  const nativeBase = encodeURIComponent(qs("#nativeBase").value.trim());
  const suffix = nativeEnabled && nativeBase ? `&nativeApiBase=${nativeBase}` : "";
  const payload = await requestJson(`/api/endpoints?ollamaApiBase=${ollamaBase}${suffix}`);
  renderEndpoints(payload);
}

async function startTunnel() {
  const button = qs("#tunnelButton");
  if (state.status && serverIsRunning(state.status)) {
    await refreshStatus();
    return;
  }
  setBusy(button, true);
  try {
    const result = await requestJson("/api/actions/tunnel", {
      method: "POST",
      body: JSON.stringify({}),
    });
    qs("#activityLog").textContent = [result.message, result.output].filter(Boolean).join("\n");
    await refreshStatus();
  } finally {
    setBusy(button, false);
    if (state.status) {
      updateStartButton(state.status);
    }
  }
}

async function generateScripts() {
  const button = qs("#generateScriptsButton");
  setBusy(button, true);
  try {
    const result = await requestJson("/api/actions/generate-scripts", {
      method: "POST",
      body: JSON.stringify({
        mode: qs("#scriptMode").value,
        profile: qs("#scriptProfile").value,
        outputDir: qs("#outputDir").value.trim() || ".",
      }),
    });
    qs("#activityLog").textContent = [result.message, result.output].filter(Boolean).join("\n");
  } finally {
    setBusy(button, false);
  }
}

async function runDiagnostics() {
  const button = qs("#diagnosticsButton");
  setBusy(button, true);
  try {
    const payload = await requestJson("/api/diagnostics");
    qs("#diagnosticsOutput").textContent = payload.text;
  } finally {
    setBusy(button, false);
  }
}

function wireEvents() {
  qs("#probeEndpointsButton").addEventListener("click", refreshEndpoints);
  qs("#tunnelButton").addEventListener("click", startTunnel);
  qs("#generateScriptsButton").addEventListener("click", generateScripts);
  qs("#diagnosticsButton").addEventListener("click", runDiagnostics);
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showView(link.dataset.viewLink);
    });
  });
  qs("#nativeEnabled").addEventListener("change", (event) => {
    qs("#nativeBase").disabled = !event.target.checked;
    refreshEndpoints();
  });
}

function showView(view) {
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    link.classList.toggle("active", link.dataset.viewLink === view);
  });
  document.querySelectorAll("[data-view-section]").forEach((section) => {
    section.hidden = section.dataset.viewSection !== view;
  });
  if (view === "diagnostics" && qs("#diagnosticsOutput").textContent === "No report yet.") {
    runDiagnostics();
  }
  if (view === "endpoints") {
    refreshEndpoints();
  }
}

wireEvents();
refreshStatus();
