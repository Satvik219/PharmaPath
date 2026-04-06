const API_BASE_URL = "http://localhost:5000/api";
const TOKEN_STORAGE_KEY = "pharmapath_live_token";

const statusEl = document.getElementById("status");
const formEl = document.getElementById("interaction-form");
const resultsPanel = document.getElementById("results-panel");
const graphPanel = document.getElementById("graph-panel");

let authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || "";

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

async function verifyExistingToken() {
  if (!authToken) {
    return false;
  }

  try {
    await apiFetch("/interactions/severity-levels", { method: "GET" });
    setStatus("Connected to Flask backend. Ready for interaction analysis.");
    return true;
  } catch (error) {
    authToken = "";
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    return false;
  }
}

async function bootstrapSession() {
  const existingSessionIsValid = await verifyExistingToken();
  if (existingSessionIsValid) {
    return;
  }

  const data = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      name: "Live Preview User",
      email: `live-${Date.now()}@pharmapath.local`,
      password: "demo1234",
      role: "pharmacist"
    })
  });
  authToken = data.jwt_token;
  localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
  setStatus("Connected to Flask backend. Ready for interaction analysis.");
}

function parseFormPayload() {
  return {
    medications: document
      .getElementById("medications")
      .value.split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    patient: {
      age: Number(document.getElementById("age").value) || undefined,
      weight_kg: Number(document.getElementById("weight").value) || undefined,
      liver_function: document.getElementById("liver-function").value || undefined,
      renal_function: document.getElementById("renal-function").value || undefined,
      conditions: document
        .getElementById("conditions")
        .value.split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    }
  };
}

function renderResults(result) {
  const summary = result.user_summary;
  const astarBlock = result.astar_summary.result
    ? `
      <div class="algorithm-card">
        <h3>What A* search did</h3>
        <p>${result.astar_summary.summary}</p>
        <p><strong>Current medicines:</strong> ${result.astar_summary.result.current_medications.join(", ")}</p>
        <p><strong>Suggested lower-risk option:</strong> ${result.astar_summary.result.suggested_medications.join(", ")}</p>
        <p><strong>Estimated risk score of suggestion:</strong> ${result.astar_summary.result.estimated_risk_score}</p>
        <p>${result.astar_summary.result.explanation}</p>
      </div>
    `
    : `
      <div class="algorithm-card">
        <h3>What A* search did</h3>
        <p>${result.astar_summary.summary}</p>
      </div>
    `;
  const resolvedCards = result.resolved_medications.length
    ? result.resolved_medications
        .map(
          (item) => `
            <div class="resolved-chip">
              <strong>${item.input}</strong> matched to ${item.name} (${item.drug_id})
            </div>
          `
        )
        .join("")
    : "<p>No medicines could be matched.</p>";

  const unmatchedBlock = result.unmatched_medications.length
    ? `<p><strong>Not recognized:</strong> ${result.unmatched_medications.join(", ")}. Please check the spelling or ask a pharmacist.</p>`
    : "";

  const riskCards = result.risk_pairs.length
    ? result.risk_pairs
        .map(
          (pair) => `
            <article class="pill-card">
              <strong>${pair.source_name} + ${pair.target_name}</strong>
              <span>${pair.type}</span>
              <span>Risk score: ${pair.adjusted_score ?? pair.score}</span>
              <p>${pair.description}</p>
            </article>
          `
        )
        .join("")
    : "<p>No direct interaction warning was found for the medicines that were recognized.</p>";

  const flagCards = result.bayesian_flags.length
    ? result.bayesian_flags
        .map(
          (flag) =>
            `<p>Your personal risk was increased by ${flag.delta} because of ${flag.reasons.join(", ")}.</p>`
        )
        .join("")
    : "<p>No patient-specific escalations were applied.</p>";

  const alternativeCards = result.safe_alternatives.length
    ? result.safe_alternatives
        .map(
          (option) => `
            <article class="alternative-card">
              <strong>${option.medication_names.join(", ")}</strong>
              <span>Estimated risk score: ${option.total_risk_score}</span>
              <p>${option.path_explanation}</p>
            </article>
          `
        )
        .join("")
    : "<p>No severe pair triggered an alternative search.</p>";

  resultsPanel.innerHTML = `
    <div class="panel-header">
      <p class="eyebrow">Final Result</p>
      <h2>${summary.title}</h2>
    </div>
    <div class="decision-card">
      <h3>What you should do now</h3>
      <p>${summary.action}</p>
      <h3>Why</h3>
      <p>${summary.why}</p>
      <p><strong>Overall risk:</strong> ${result.overall_risk}</p>
      ${unmatchedBlock}
    </div>
    ${astarBlock}
    <div class="panel-subsection">
      <h3>Medicines recognized by the system</h3>
      <div class="resolved-list">${resolvedCards}</div>
    </div>
    <div class="risk-pills">${riskCards}</div>
    <div class="panel-subsection">
      <h3>Personal factors that changed the result</h3>
      ${flagCards}
    </div>
    <div class="panel-subsection">
      <h3>Possible lower-risk options to ask about</h3>
      ${alternativeCards}
    </div>
  `;
}

function renderGraph(result) {
  const svg = buildComparisonGraphSvg(result.comparison_graph);

  graphPanel.innerHTML = `
    <div class="panel-header">
      <p class="eyebrow">Graph View</p>
      <h2>Medicine Relationship Map</h2>
    </div>
    <p>This map compares the medicines entered by the user with the lower-risk set suggested by A* search.</p>
    <div class="graph-legend">
      <span><span class="legend-dot" style="background:#c24d3f"></span>Current medicine</span>
      <span><span class="legend-dot" style="background:#2e9cbf"></span>Suggested medicine</span>
      <span><span class="legend-dot" style="background:#c8952d"></span>Interaction link</span>
    </div>
    <div class="graph-grid">
      ${svg}
    </div>
  `;
}

function buildComparisonGraphSvg(graph) {
  if (!graph.nodes.length) {
    return "<p>No graph data is available for this result.</p>";
  }

  const width = 900;
  const height = 380;
  const currentNodes = graph.nodes.filter((node) => node.group === "current");
  const suggestedNodes = graph.nodes.filter((node) => node.group === "suggested");
  const positions = {};

  currentNodes.forEach((node, index) => {
    const step = height / (currentNodes.length + 1);
    positions[node.id] = { x: 180, y: step * (index + 1) };
  });

  suggestedNodes.forEach((node, index) => {
    const step = height / (suggestedNodes.length + 1);
    positions[node.id] = { x: 720, y: step * (index + 1) };
  });

  const edgeSvg = graph.edges
    .map((edge) => {
      const source = positions[edge.source];
      const target = positions[edge.target];
      if (!source || !target) {
        return "";
      }

      const stroke =
        edge.kind === "replacement"
          ? "#2e9cbf"
          : edge.kind === "same-medicine"
            ? "#6c8a5c"
            : edge.severity === "contraindicated"
              ? "#c24d3f"
              : "#c8952d";
      const dash = edge.kind === "interaction" ? "0" : "8 6";
      const midX = (source.x + target.x) / 2;
      const midY = (source.y + target.y) / 2 - 8;

      return `
        <line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}"
          stroke="${stroke}" stroke-width="3" stroke-dasharray="${dash}" opacity="0.9" />
        <text x="${midX}" y="${midY}" text-anchor="middle" font-size="12" fill="#35506a">${edge.label}</text>
      `;
    })
    .join("");

  const nodeSvg = graph.nodes
    .map((node) => {
      const position = positions[node.id];
      const fill = node.group === "current" ? "#f4c5bf" : "#bfe4ef";
      const stroke = node.group === "current" ? "#c24d3f" : "#2e9cbf";
      if (!position) {
        return "";
      }

      return `
        <g>
          <circle cx="${position.x}" cy="${position.y}" r="34" fill="${fill}" stroke="${stroke}" stroke-width="3" />
          <text x="${position.x}" y="${position.y - 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#18324d">${node.label}</text>
          <text x="${position.x}" y="${position.y + 14}" text-anchor="middle" font-size="10" fill="#4f6478">${node.group === "current" ? "Current" : "Suggested"}</text>
        </g>
      `;
    })
    .join("");

  return `
    <svg class="graph-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Medicine comparison graph">
      <text x="180" y="30" text-anchor="middle" font-size="18" font-weight="700" fill="#18324d">Medicines Given</text>
      <text x="720" y="30" text-anchor="middle" font-size="18" font-weight="700" fill="#18324d">A* Suggested Medicines</text>
      ${edgeSvg}
      ${nodeSvg}
    </svg>
  `;
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Checking the medicines and preparing a final recommendation...");

  try {
    const result = await apiFetch("/interactions/check", {
      method: "POST",
      body: JSON.stringify(parseFormPayload())
    });
    renderResults(result);
    renderGraph(result);
    setStatus("Analysis complete.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

bootstrapSession().catch((error) => {
  setStatus(`Backend connection failed: ${error.message}`, true);
});
