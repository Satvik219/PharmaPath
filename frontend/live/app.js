const API_BASE_URL = "http://localhost:5000/api";
const TOKEN_STORAGE_KEY = "pharmapath_live_token";

const statusEl = document.getElementById("status");
const formEl = document.getElementById("interaction-form");
const resultsPanel = document.getElementById("results-panel");
const graphPanel = document.getElementById("graph-panel");
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

let authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || "";
let currentResult = null;
let currentChatSessionId = "";
let loadingBubble = null;

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
    setStatus("Connected to backend. Ready for interaction analysis.");
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
  setStatus("Connected to backend. Ready for interaction analysis.");
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
  const summaryTitle =
    result.severity === "high"
      ? "High-risk regimen detected"
      : result.severity === "moderate"
        ? "Moderate interaction risk detected"
        : "No major interaction signal detected";

  const summaryAction =
    result.recommendations?.[0] ||
    "Review the explanation and discuss medication changes with a clinician before acting.";

  const summaryWhy =
    result.explanation ||
    "The analysis combines direct interaction severity, patient-specific risk factors, and multi-drug amplification.";

  const astarBlock = result.safe_alternatives?.[0]
    ? `
      <div class="algorithm-card">
        <h3>What A* search did</h3>
        <p>The search engine tested alternative regimens and ranked lower-risk substitutions.</p>
        <p><strong>Current medicines:</strong> ${result.drugs.join(", ")}</p>
        <p><strong>Suggested lower-risk option:</strong> ${result.safe_alternatives[0].medication_names.join(", ")}</p>
        <p><strong>Estimated risk score of suggestion:</strong> ${result.safe_alternatives[0].total_risk_score}</p>
        <p>${result.safe_alternatives[0].path_explanation}</p>
      </div>
    `
    : `
      <div class="algorithm-card">
        <h3>What A* search did</h3>
        <p>No lower-risk substitution was confidently identified from the current dataset.</p>
      </div>
    `;

  const resolvedCards = result.resolved_medications?.length
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

  const unmatchedBlock = result.unmatched_medications?.length
    ? `<p><strong>Not recognized:</strong> ${result.unmatched_medications.join(", ")}.</p>`
    : "";

  const riskCards = result.interactions?.length
    ? result.interactions
        .map(
          (pair) => `
            <article class="pill-card">
              <strong>${pair.source_name} + ${pair.target_name}</strong>
              <span>${pair.type}</span>
              <span>Risk score: ${pair.final_score ?? pair.base_score ?? pair.score}</span>
              <p>${pair.description}</p>
            </article>
          `
        )
        .join("")
    : "<p>No direct interaction warning was found for the medicines that were recognized.</p>";

  const flagCards = result.interactions_overview?.bayesian_flags?.length
    ? result.interactions_overview.bayesian_flags
        .map(
          (flag) =>
            `<p>Your personal risk was increased by ${flag.delta} because of ${flag.reasons.join(", ")}.</p>`
        )
        .join("")
    : "<p>No patient-specific escalations were applied.</p>";

  const chainCards = result.interactions_overview?.multi_hop_chains?.length
    ? result.interactions_overview.multi_hop_chains
        .map(
          (chain) => `
            <article class="alternative-card">
              <strong>${chain.path_names.join(" -> ")}</strong>
              <span>Chain score: ${chain.combined_score}</span>
              <p>${chain.mechanism}</p>
            </article>
          `
        )
        .join("")
    : "<p>No multi-hop interaction chains were detected in this regimen.</p>";

  const alternativeCards = result.safe_alternatives?.length
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

  const aiMeta = result.ai_meta || {};
  const aiMessage =
    aiMeta.source === "gemini"
      ? `Gemini response active via ${aiMeta.used_model}.`
      : `Using local fallback reasoning${aiMeta.error ? ` because Gemini failed: ${aiMeta.error}` : "."}`;

  resultsPanel.innerHTML = `
    <div class="panel-header">
      <p class="eyebrow">Final Result</p>
      <h2>${summaryTitle}</h2>
    </div>
    <div class="decision-card">
      <h3>What you should do now</h3>
      <p>${summaryAction}</p>
      <h3>Why</h3>
      <p>${summaryWhy}</p>
      <p><strong>Overall risk:</strong> ${result.severity} (${result.risk_score}/100)</p>
      <p><strong>AI status:</strong> ${aiMessage}</p>
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
      <h3>Multi-drug interaction chains</h3>
      ${chainCards}
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
  if (!graph?.nodes?.length) {
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
            : String(edge.severity || "").toLowerCase() === "contraindicated"
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

function appendChatBubble(role, message) {
  if (chatLog.querySelector(".chat-placeholder")) {
    chatLog.innerHTML = "";
  }

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = `<strong>${role === "user" ? "You" : "PharmaPath"}</strong><p>${message}</p>`;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showChatLoading() {
  if (loadingBubble) {
    return;
  }

  if (chatLog.querySelector(".chat-placeholder")) {
    chatLog.innerHTML = "";
  }

  loadingBubble = document.createElement("div");
  loadingBubble.className = "chat-bubble assistant loading";
  loadingBubble.innerHTML = `
    <strong>PharmaPath</strong>
    <div class="typing-indicator" aria-label="Loading response">
      <span></span><span></span><span></span>
    </div>
  `;
  chatLog.appendChild(loadingBubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function hideChatLoading() {
  if (!loadingBubble) {
    return;
  }

  loadingBubble.remove();
  loadingBubble = null;
}

function clearSuggestedQuestionRows() {
  chatLog.querySelectorAll(".graph-legend").forEach((node) => node.remove());
}

function renderSuggestedQuestions(questions = []) {
  clearSuggestedQuestionRows();
  if (!questions.length) {
    return;
  }

  const actions = document.createElement("div");
  actions.className = "graph-legend";
  actions.innerHTML = questions
    .map((question) => `<button type="button" data-question="${question.replace(/"/g, "&quot;")}">${question}</button>`)
    .join("");
  chatLog.appendChild(actions);

  actions.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      chatInput.value = button.dataset.question || "";
      chatForm.requestSubmit();
    });
  });
}

async function askQuestion(question) {
  if (!currentResult) {
    setStatus("Run an interaction check before asking follow-up questions.", true);
    return;
  }

  const submitButton = chatForm.querySelector("button");
  appendChatBubble("user", question);
  setStatus("PharmaPath is thinking...");
  showChatLoading();
  chatInput.disabled = true;
  if (submitButton) {
    submitButton.disabled = true;
  }

  const medications = document
    .getElementById("medications")
    .value.split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const lowerQuestion = question.toLowerCase();
  const removeMatch = lowerQuestion.match(/remove\s+([a-z0-9\- ]+)/i);
  const addMatch = lowerQuestion.match(/add\s+([a-z0-9\- ]+)/i);

  try {
    const result = await apiFetch("/interactions/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: currentChatSessionId || undefined,
        message: question,
        drugs: currentResult.drugs,
        current_drugs: medications,
        remove: removeMatch ? removeMatch[1].trim() : undefined,
        add: addMatch ? addMatch[1].trim() : undefined,
        patient: parseFormPayload().patient
      })
    });

    currentChatSessionId = result.session_id || currentChatSessionId;
    hideChatLoading();
    appendChatBubble("assistant", result.chat_response || "I could not generate a response.");
    renderSuggestedQuestions(result.suggested_questions || []);
    setStatus(
      result.ai_meta?.source === "gemini"
        ? `Gemini answered using ${result.ai_meta.used_model}.`
        : `Used local fallback reasoning${result.ai_meta?.error ? ` because Gemini failed: ${result.ai_meta.error}` : "."}`,
      result.ai_meta?.source !== "gemini"
    );
  } catch (error) {
    hideChatLoading();
    appendChatBubble("assistant", `I hit an error while answering: ${error.message}`);
    setStatus(error.message, true);
  } finally {
    chatInput.disabled = false;
    if (submitButton) {
      submitButton.disabled = false;
    }
    chatInput.focus();
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Checking the medicines and preparing a final recommendation...");

  try {
    const result = await apiFetch("/interactions/check", {
      method: "POST",
      body: JSON.stringify(parseFormPayload())
    });
    currentResult = result;
    currentChatSessionId = "";
    hideChatLoading();
    renderResults(result);
    renderGraph(result);
    chatLog.innerHTML = "";
    appendChatBubble("assistant", result.explanation || "Analysis complete.");
    renderSuggestedQuestions(result.suggested_questions || []);
    setStatus(
      result.ai_meta?.source === "gemini"
        ? `Analysis complete with Gemini using ${result.ai_meta.used_model}.`
        : `Analysis complete with local fallback reasoning${result.ai_meta?.error ? ` because Gemini failed: ${result.ai_meta.error}` : "."}`,
      result.ai_meta?.source !== "gemini"
    );
  } catch (error) {
    setStatus(error.message, true);
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatInput.value.trim();
  if (!question) {
    return;
  }
  chatInput.value = "";
  await askQuestion(question);
});

bootstrapSession().catch((error) => {
  setStatus(`Backend connection failed: ${error.message}`, true);
});
