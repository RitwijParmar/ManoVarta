const state = {
  sessionId: null,
  language: "en",
  exportPayload: null,
};

const chatLog = document.getElementById("chatLog");
const sessionMeta = document.getElementById("sessionMeta");
const messageInput = document.getElementById("messageInput");
const languageSelect = document.getElementById("languageSelect");
const startButton = document.getElementById("startButton");
const chatForm = document.getElementById("chatForm");
const downloadButton = document.getElementById("downloadButton");

const runtimeInfo = document.getElementById("runtimeInfo");
const summaryText = document.getElementById("summaryText");
const phqTotal = document.getElementById("phqTotal");
const gadTotal = document.getElementById("gadTotal");
const safetyLevel = document.getElementById("safetyLevel");
const snapshotMode = document.getElementById("snapshotMode");
const coverageText = document.getElementById("coverageText");
const unresolvedCount = document.getElementById("unresolvedCount");
const unresolvedList = document.getElementById("unresolvedList");
const itemTableBody = document.getElementById("itemTableBody");
const evidenceList = document.getElementById("evidenceList");

async function fetchRuntime() {
  const response = await fetch("/runtime/config");
  const payload = await response.json();
  runtimeInfo.textContent = `${payload.provider} | chat: ${payload.chat_model} | extract: ${payload.extraction_model}`;
}

async function startSession() {
  state.language = languageSelect.value;
  const response = await fetch("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: state.language }),
  });
  const payload = await response.json();
  state.sessionId = payload.session_id;
  state.exportPayload = null;
  chatLog.innerHTML = "";
  renderTurn(payload.assistant_turn);
  sessionMeta.classList.remove("empty");
  sessionMeta.textContent = `Session ${state.sessionId} | language: ${state.language}`;
  downloadButton.disabled = true;
  resetInsightPanel();
}

function renderTurn(turn) {
  const card = document.createElement("article");
  card.className = `message ${turn.speaker}`;
  card.innerHTML = `
    <span class="speaker">${turn.speaker}</span>
    <div class="bubble">${escapeHtml(turn.text)}</div>
  `;
  chatLog.appendChild(card);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderSnapshot(payload) {
  const { snapshot, summary, rows } = payload;
  phqTotal.textContent = snapshot.totals.PHQ9 ?? 0;
  gadTotal.textContent = snapshot.totals.GAD7 ?? 0;
  safetyLevel.textContent = snapshot.safety.level;
  safetyLevel.className = `metric-value small ${snapshot.safety.level}`;
  snapshotMode.textContent = snapshot.mode;
  summaryText.textContent = summary;
  coverageText.textContent = `Coverage ${snapshot.evidence_spans.length}/${Object.keys(snapshot.items).length}`;
  unresolvedCount.textContent = `${snapshot.unresolved_items.length} unresolved`;

  unresolvedList.innerHTML = "";
  if (!snapshot.unresolved_items.length) {
    unresolvedList.innerHTML = "<li>No unresolved items right now.</li>";
  } else {
    snapshot.unresolved_items.slice(0, 6).forEach((itemId) => {
      const row = rows.find((entry) => entry.item_id === itemId);
      const entry = document.createElement("li");
      entry.textContent = row ? `${row.label} · ${row.status}` : itemId;
      unresolvedList.appendChild(entry);
    });
  }

  itemTableBody.innerHTML = "";
  rows
    .filter((row) => row.value !== null || row.status !== "unresolved")
    .slice(0, 16)
    .forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.label)}</td>
        <td>${row.value === null ? "—" : row.value}</td>
        <td><span class="status-pill ${row.status}">${row.status}</span></td>
        <td>${row.source}</td>
      `;
      itemTableBody.appendChild(tr);
    });
  if (!itemTableBody.innerHTML) {
    itemTableBody.innerHTML = '<tr><td colspan="4" class="empty-cell">No item scores yet.</td></tr>';
  }

  evidenceList.innerHTML = "";
  if (!snapshot.evidence_spans.length) {
    evidenceList.innerHTML = '<li class="empty-cell">No evidence spans yet.</li>';
  } else {
    snapshot.evidence_spans.slice(-6).reverse().forEach((span) => {
      const itemRow = rows.find((row) => row.item_id === span.item_id);
      const li = document.createElement("li");
      li.className = "evidence-item";
      li.innerHTML = `
        <strong>${escapeHtml(itemRow ? itemRow.label : span.item_id)}</strong>
        <span>${escapeHtml(span.text_span)}</span>
      `;
      evidenceList.appendChild(li);
    });
  }
}

function resetInsightPanel() {
  phqTotal.textContent = "0";
  gadTotal.textContent = "0";
  safetyLevel.textContent = "none";
  snapshotMode.textContent = "heuristic";
  coverageText.textContent = "Coverage 0/16";
  unresolvedCount.textContent = "0 unresolved";
  summaryText.textContent = "Start a conversation to generate the first summary.";
  unresolvedList.innerHTML = "<li>No unresolved items yet.</li>";
  itemTableBody.innerHTML = '<tr><td colspan="4" class="empty-cell">No item scores yet.</td></tr>';
  evidenceList.innerHTML = '<li class="empty-cell">No evidence spans yet.</li>';
}

async function refreshExport() {
  if (!state.sessionId) {
    return;
  }
  const response = await fetch(`/chat/sessions/${state.sessionId}/export`);
  state.exportPayload = await response.json();
  downloadButton.disabled = false;
  renderSnapshot(state.exportPayload);
}

async function sendTurn(event) {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }
  if (!state.sessionId) {
    await startSession();
  }

  renderTurn({ speaker: "user", text });
  messageInput.value = "";

  const response = await fetch(`/chat/sessions/${state.sessionId}/turns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const payload = await response.json();
  renderTurn(payload.assistant_turn);
  await refreshExport();
}

function downloadExport() {
  if (!state.exportPayload) {
    return;
  }
  const blob = new Blob([JSON.stringify(state.exportPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${state.sessionId || "manovarta-session"}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

startButton.addEventListener("click", startSession);
chatForm.addEventListener("submit", sendTurn);
downloadButton.addEventListener("click", downloadExport);

fetchRuntime().catch(() => {
  runtimeInfo.textContent = "Runtime config unavailable.";
});
