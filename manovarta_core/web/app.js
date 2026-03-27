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
const micButton = document.getElementById("micButton");
const autoSendToggle = document.getElementById("autoSendToggle");
const speakToggle = document.getElementById("speakToggle");
const voiceStatus = document.getElementById("voiceStatus");

const runtimeInfo = document.getElementById("runtimeInfo");
const summaryText = document.getElementById("summaryText");
const phqTotal = document.getElementById("phqTotal");
const gadTotal = document.getElementById("gadTotal");
const safetyLevel = document.getElementById("safetyLevel");
const snapshotMode = document.getElementById("snapshotMode");
const coverageText = document.getElementById("coverageText");
const unresolvedCount = document.getElementById("unresolvedCount");
const unresolvedList = document.getElementById("unresolvedList");
const reviewCount = document.getElementById("reviewCount");
const reviewList = document.getElementById("reviewList");
const itemTableBody = document.getElementById("itemTableBody");
const evidenceList = document.getElementById("evidenceList");

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;
const speechSynthesisApi = window.speechSynthesis || null;

let recognition = null;
let listening = false;

async function fetchRuntime() {
  const response = await fetch("/runtime/config");
  const payload = await response.json();
  runtimeInfo.textContent = `${payload.provider} | chat: ${payload.chat_model} | extract: ${payload.extraction_model}`;
}

async function startSession() {
  state.language = languageSelect.value;
  stopListening();

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
  maybeSpeak(payload.assistant_turn);
  sessionMeta.classList.remove("empty");
  sessionMeta.textContent = `Session ${state.sessionId} | language: ${state.language}`;
  downloadButton.disabled = true;
  resetInsightPanel();
  updateVoiceStatus("Session ready for typed or spoken turns.");
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
  const coverage = snapshot.coverage || {
    total_items: Object.keys(snapshot.items).length,
    touched_items: snapshot.evidence_spans.length,
    resolved_items: [],
    next_items: snapshot.unresolved_items,
    review_items: [],
  };
  phqTotal.textContent = snapshot.totals.PHQ9 ?? 0;
  gadTotal.textContent = snapshot.totals.GAD7 ?? 0;
  safetyLevel.textContent = snapshot.safety.level;
  safetyLevel.className = `metric-value small ${snapshot.safety.level}`;
  snapshotMode.textContent = snapshot.mode;
  summaryText.textContent = summary;
  coverageText.textContent = `Coverage ${coverage.touched_items}/${coverage.total_items} · resolved ${coverage.resolved_items.length}`;
  unresolvedCount.textContent = `${coverage.next_items.length} queued`;
  reviewCount.textContent = `${coverage.review_items.length} flagged`;

  unresolvedList.innerHTML = "";
  if (!coverage.next_items.length) {
    unresolvedList.innerHTML = "<li>No follow-up queue right now.</li>";
  } else {
    coverage.next_items.slice(0, 6).forEach((itemId) => {
      const row = rows.find((entry) => entry.item_id === itemId);
      const entry = document.createElement("li");
      entry.textContent = row ? `${row.label} · ${row.status}` : itemId;
      unresolvedList.appendChild(entry);
    });
  }

  reviewList.innerHTML = "";
  if (!coverage.review_items.length) {
    reviewList.innerHTML = "<li>No review flags right now.</li>";
  } else {
    coverage.review_items.slice(0, 6).forEach((itemId) => {
      const row = rows.find((entry) => entry.item_id === itemId);
      const entry = document.createElement("li");
      entry.textContent = row ? `${row.label} · ${row.status}` : itemId;
      reviewList.appendChild(entry);
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
  unresolvedCount.textContent = "0 queued";
  reviewCount.textContent = "0 flagged";
  summaryText.textContent = "Start a conversation to generate the first summary.";
  unresolvedList.innerHTML = "<li>No follow-up queue yet.</li>";
  reviewList.innerHTML = "<li>No review flags right now.</li>";
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

  stopListening();
  if (speechSynthesisApi) {
    speechSynthesisApi.cancel();
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
  maybeSpeak(payload.assistant_turn);
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

function setupVoice() {
  if (!micButton || !voiceStatus) {
    return;
  }

  if (!SpeechRecognitionCtor) {
    micButton.disabled = true;
    updateVoiceStatus("Speech recognition is not available in this browser.", true);
    return;
  }

  recognition = new SpeechRecognitionCtor();
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;
  recognition.lang = mapVoiceLanguage(languageSelect.value);

  recognition.onstart = () => {
    listening = true;
    micButton.textContent = "Stop voice";
    updateVoiceStatus("Listening for a response...", false, true);
  };

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ")
      .trim();
    if (!transcript) {
      return;
    }

    messageInput.value = transcript;
    const finalResult = event.results[event.results.length - 1];
    if (finalResult?.isFinal) {
      updateVoiceStatus("Transcript captured.");
      if (autoSendToggle.checked) {
        chatForm.requestSubmit();
      }
    }
  };

  recognition.onerror = (event) => {
    listening = false;
    micButton.textContent = "Start voice";
    updateVoiceStatus(`Voice error: ${event.error}`, true);
  };

  recognition.onend = () => {
    listening = false;
    micButton.textContent = "Start voice";
    if (!voiceStatus.classList.contains("error")) {
      updateVoiceStatus("Voice idle.");
    }
  };

  micButton.addEventListener("click", toggleListening);
  languageSelect.addEventListener("change", () => {
    if (recognition) {
      recognition.lang = mapVoiceLanguage(languageSelect.value);
    }
    updateVoiceStatus(`Voice language set to ${languageSelect.value}.`);
  });

  updateVoiceStatus("Voice ready when microphone access is allowed.");
}

function toggleListening() {
  if (!recognition) {
    return;
  }
  if (listening) {
    stopListening();
    return;
  }

  recognition.lang = mapVoiceLanguage(languageSelect.value);
  updateVoiceStatus("Requesting microphone access...");
  recognition.start();
}

function stopListening() {
  if (recognition && listening) {
    recognition.stop();
  }
}

function maybeSpeak(turn) {
  if (!speechSynthesisApi || !speakToggle?.checked || turn.speaker !== "assistant") {
    return;
  }

  speechSynthesisApi.cancel();
  const utterance = new SpeechSynthesisUtterance(turn.text);
  utterance.lang = mapVoiceLanguage(state.language);
  const voice = pickVoice(utterance.lang);
  if (voice) {
    utterance.voice = voice;
  }
  speechSynthesisApi.speak(utterance);
}

function pickVoice(languageTag) {
  if (!speechSynthesisApi?.getVoices) {
    return null;
  }

  const voices = speechSynthesisApi.getVoices();
  if (!voices.length) {
    return null;
  }

  const exactMatch = voices.find((entry) => entry.lang === languageTag);
  if (exactMatch) {
    return exactMatch;
  }

  const baseTag = languageTag.split("-")[0];
  return voices.find((entry) => entry.lang.startsWith(baseTag)) || null;
}

function mapVoiceLanguage(languageCode) {
  if (languageCode === "hi") {
    return "hi-IN";
  }
  if (languageCode === "hinglish") {
    return "en-IN";
  }
  return "en-US";
}

function updateVoiceStatus(message, isError = false, isActive = false) {
  if (!voiceStatus) {
    return;
  }
  voiceStatus.textContent = message;
  voiceStatus.classList.toggle("error", isError);
  voiceStatus.classList.toggle("active", isActive);
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
setupVoice();

fetchRuntime().catch(() => {
  runtimeInfo.textContent = "Runtime config unavailable.";
});
