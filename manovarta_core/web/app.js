const state = {
  sessionId: null,
  language: "en",
  exportPayload: null,
  profiles: [],
  isBusy: false,
};

const chatLog = document.getElementById("chatLog");
const sessionMeta = document.getElementById("sessionMeta");
const sessionBadge = document.getElementById("sessionBadge");
const messageInput = document.getElementById("messageInput");
const languageSelect = document.getElementById("languageSelect");
const startButton = document.getElementById("startButton");
const chatForm = document.getElementById("chatForm");
const downloadButton = document.getElementById("downloadButton");
const summaryLink = document.getElementById("summaryLink");
const exportLink = document.getElementById("exportLink");
const micButton = document.getElementById("micButton");
const autoSendToggle = document.getElementById("autoSendToggle");
const speakToggle = document.getElementById("speakToggle");
const voiceStatus = document.getElementById("voiceStatus");
const statusBanner = document.getElementById("statusBanner");

const runtimeInfo = document.getElementById("runtimeInfo");
const serviceHealth = document.getElementById("serviceHealth");
const profileList = document.getElementById("profileList");
const apiLinkList = document.getElementById("apiLinkList");
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

function setBusy(isBusy) {
  state.isBusy = isBusy;
  startButton.disabled = isBusy;
  chatForm.querySelector('button[type="submit"]').disabled = isBusy;
}

function setStatusBanner(message, tone = "info") {
  if (!statusBanner) {
    return;
  }
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${tone}`;
}

function updateSessionBadge() {
  if (!sessionBadge) {
    return;
  }
  if (!state.sessionId) {
    sessionBadge.textContent = "No session";
    sessionBadge.className = "chip soft";
    return;
  }
  sessionBadge.textContent = `${state.language.toUpperCase()} • ${state.sessionId.slice(0, 8)}`;
  sessionBadge.className = "chip";
}

function setLink(anchor, href) {
  if (!anchor) {
    return;
  }
  if (!href) {
    anchor.href = "#";
    anchor.classList.add("disabled-link");
    return;
  }
  anchor.href = href;
  anchor.classList.remove("disabled-link");
}

function runtimeToText(payload) {
  return `${payload.provider} | chat: ${payload.chat_model} | extract: ${payload.extraction_model}`;
}

function renderApiLinks(links) {
  if (!apiLinkList) {
    return;
  }
  const resolvedLinks = links?.length
    ? links
    : [
        { label: "Health", href: "/health", description: "Service heartbeat and active sessions" },
        { label: "Runtime config", href: "/runtime/config", description: "Current provider and model setup" },
        { label: "Profiles", href: "/profiles", description: "Seed demo profiles" },
        { label: "Questionnaires", href: "/questionnaires", description: "PHQ-9 and GAD-7 item schema" },
        { label: "OpenAPI docs", href: "/docs", description: "Interactive API explorer" },
      ];

  apiLinkList.innerHTML = "";
  resolvedLinks.forEach((link) => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${escapeHtml(link.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(link.label)}</a>
      <span class="link-hint">${escapeHtml(link.description || "")}</span>`;
    apiLinkList.appendChild(li);
  });
}

function renderProfiles(profiles) {
  if (!profileList) {
    return;
  }
  if (!profiles.length) {
    profileList.innerHTML = '<p class="muted">No profiles available right now.</p>';
    return;
  }

  profileList.innerHTML = "";
  profiles.slice(0, 6).forEach((profile) => {
    const card = document.createElement("article");
    card.className = "profile-card";
    const tags = (profile.nuance_tags || []).slice(0, 3).join(" • ");
    card.innerHTML = `
      <p class="profile-title">${escapeHtml(profile.patient_id)} · ${escapeHtml((profile.language || "en").toUpperCase())}</p>
      <p class="profile-meta">${escapeHtml(profile.occupation || "participant")} · age ${escapeHtml(String(profile.age || "n/a"))}</p>
      <p class="profile-context">${escapeHtml(profile.context || profile.notes || "No context available.")}</p>
      <p class="profile-tags">${escapeHtml(tags || "general screening demo")}</p>
      <button type="button" class="button secondary profile-launch" data-profile-id="${escapeHtml(profile.patient_id)}">Launch Scenario</button>
    `;
    profileList.appendChild(card);
  });

  document.querySelectorAll(".profile-launch").forEach((button) => {
    button.addEventListener("click", async () => {
      const profileId = button.getAttribute("data-profile-id");
      const profile = state.profiles.find((entry) => entry.patient_id === profileId);
      if (!profile) {
        return;
      }
      await launchProfile(profile);
    });
  });
}

function mapProfileToSeedText(profile) {
  const depression = profile.depression_level || "unknown";
  const anxiety = profile.anxiety_level || "unknown";
  const context = profile.context || "day-to-day stress has been hard to manage";
  const note = profile.notes || "I am trying to explain what has changed lately.";
  return `I am ${profile.age || "an adult"} and ${context}. My depression feels ${depression} and anxiety feels ${anxiety}. ${note}`;
}

async function launchProfile(profile) {
  languageSelect.value = profile.language || "en";
  state.language = languageSelect.value;
  setStatusBanner(`Launching ${profile.patient_id} in ${state.language.toUpperCase()}...`, "info");
  await startSession();
  await sendMessageText(mapProfileToSeedText(profile));
}

async function fetchBootstrap() {
  try {
    const response = await fetch("/demo/bootstrap");
    if (!response.ok) {
      throw new Error(`Bootstrap failed: ${response.status}`);
    }
    const payload = await response.json();
    runtimeInfo.textContent = runtimeToText(payload.runtime);
    serviceHealth.textContent = `Backend ${payload.health.status} · active sessions ${payload.health.active_sessions}`;
    serviceHealth.className = `service-health ${payload.health.status === "ok" ? "good" : "warn"}`;
    state.profiles = payload.profiles || [];
    renderProfiles(state.profiles);
    renderApiLinks(payload.links || []);
    return;
  } catch (error) {
    console.error(error);
  }

  const [runtimeResponse, healthResponse, profilesResponse] = await Promise.all([
    fetch("/runtime/config"),
    fetch("/health"),
    fetch("/profiles"),
  ]);
  const runtimePayload = await runtimeResponse.json();
  const healthPayload = await healthResponse.json();
  const profilesPayload = await profilesResponse.json();
  runtimeInfo.textContent = runtimeToText(runtimePayload);
  serviceHealth.textContent = `Backend ${healthPayload.status} · active sessions ${healthPayload.active_sessions}`;
  serviceHealth.className = `service-health ${healthPayload.status === "ok" ? "good" : "warn"}`;
  state.profiles = (profilesPayload || []).map((profile) => {
    const background = profile.background_profile || {};
    const symptoms = profile.symptom_profile || {};
    return {
      patient_id: profile.patient_id,
      language: profile.language,
      age: profile.age,
      occupation: profile.occupation,
      context: background.context || "",
      depression_level: symptoms.depression_level || "unknown",
      anxiety_level: symptoms.anxiety_level || "unknown",
      notes: profile.notes || "",
      nuance_tags: profile.nuance_tags || [],
    };
  });
  renderProfiles(state.profiles);
  renderApiLinks([]);
}

async function startSession() {
  setBusy(true);
  try {
    state.language = languageSelect.value;
    stopListening();

    const response = await fetch("/chat/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: state.language }),
    });
    if (!response.ok) {
      throw new Error(`Could not start session (${response.status})`);
    }
    const payload = await response.json();
    state.sessionId = payload.session_id;
    state.exportPayload = null;
    chatLog.innerHTML = "";
    renderTurn(payload.assistant_turn);
    maybeSpeak(payload.assistant_turn);
    sessionMeta.classList.remove("empty");
    sessionMeta.textContent = `Session ${state.sessionId} · language ${state.language.toUpperCase()} · runtime ready`;
    updateSessionBadge();
    downloadButton.disabled = true;
    setLink(summaryLink, null);
    setLink(exportLink, null);
    resetInsightPanel();
    updateVoiceStatus("Session ready for typed or spoken turns.");
    setStatusBanner(`Session started in ${state.language.toUpperCase()}.`, "success");
  } catch (error) {
    console.error(error);
    renderSystemMessage("Session start failed. Check backend health and try again.");
    setStatusBanner("Could not start session. Please retry.", "error");
  } finally {
    setBusy(false);
  }
}

function renderSystemMessage(text) {
  renderTurn({ speaker: "assistant", text: `[System] ${text}` });
}

function renderTurn(turn) {
  const card = document.createElement("article");
  card.className = `message ${turn.speaker}`;
  card.innerHTML = `
    <span class="speaker">${turn.speaker}</span>
    <div class="bubble">${escapeHtml(String(turn.text || ""))}</div>
  `;
  chatLog.appendChild(card);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderSnapshot(payload) {
  const { snapshot, summary, rows } = payload;
  const safeRows = rows || [];
  const safeItems = snapshot.items || {};
  const coverage = snapshot.coverage || {
    total_items: Object.keys(safeItems).length,
    touched_items: snapshot.evidence_spans?.length || 0,
    resolved_items: [],
    next_items: snapshot.unresolved_items || [],
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
      const row = safeRows.find((entry) => entry.item_id === itemId);
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
      const row = safeRows.find((entry) => entry.item_id === itemId);
      const entry = document.createElement("li");
      entry.textContent = row ? `${row.label} · ${row.status}` : itemId;
      reviewList.appendChild(entry);
    });
  }

  itemTableBody.innerHTML = "";
  safeRows
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
  const evidence = snapshot.evidence_spans || [];
  if (!evidence.length) {
    evidenceList.innerHTML = '<li class="empty-cell">No evidence spans yet.</li>';
  } else {
    evidence.slice(-6).reverse().forEach((span) => {
      const itemRow = safeRows.find((row) => row.item_id === span.item_id);
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
  if (!response.ok) {
    throw new Error(`Export refresh failed (${response.status})`);
  }
  state.exportPayload = await response.json();
  downloadButton.disabled = false;
  renderSnapshot(state.exportPayload);
  setLink(summaryLink, `/chat/sessions/${state.sessionId}/summary`);
  setLink(exportLink, `/chat/sessions/${state.sessionId}/export`);
}

async function sendMessageText(text) {
  const cleaned = (text || "").trim();
  if (!cleaned) {
    return;
  }
  if (!state.sessionId) {
    await startSession();
    if (!state.sessionId) {
      return;
    }
  }

  setBusy(true);
  try {
    stopListening();
    if (speechSynthesisApi) {
      speechSynthesisApi.cancel();
    }

    renderTurn({ speaker: "user", text: cleaned });
    messageInput.value = "";

    const response = await fetch(`/chat/sessions/${state.sessionId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: cleaned }),
    });
    if (!response.ok) {
      throw new Error(`Turn failed (${response.status})`);
    }
    const payload = await response.json();
    renderTurn(payload.assistant_turn);
    maybeSpeak(payload.assistant_turn);
    await refreshExport();
    setStatusBanner("Turn processed. Structured view has been updated.", "success");
  } catch (error) {
    console.error(error);
    renderSystemMessage("Turn failed due to a runtime error. Please retry.");
    setStatusBanner("Turn failed. Check runtime and retry.", "error");
  } finally {
    setBusy(false);
  }
}

async function sendTurn(event) {
  event.preventDefault();
  await sendMessageText(messageInput.value);
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
    state.language = languageSelect.value;
    updateSessionBadge();
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
  return String(text)
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
updateSessionBadge();

fetchBootstrap()
  .then(() => {
    setStatusBanner("Runtime connected. Pick a profile or start chatting.", "success");
  })
  .catch((error) => {
    console.error(error);
    runtimeInfo.textContent = "Runtime config unavailable.";
    setStatusBanner("Backend bootstrap failed. Verify API service.", "error");
  });
