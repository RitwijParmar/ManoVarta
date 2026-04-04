const state = {
  sessionId: null,
  language: "en",
  exportPayload: null,
  profiles: [],
  runtime: null,
  isBusy: false,
};

const LANGUAGE_UI = {
  en: {
    placeholder: "Describe what changed, when it happens, and how it affects your day...",
    sessionReady: "Session ready for typed or spoken turns.",
    startSuccess: "Session started in English.",
    turnSuccess: "Turn processed. The confidence board has been updated.",
    runtimeReady: "Runtime connected. Pick a profile or start chatting.",
    nudgeIntro: "Use one of these nudges to share richer detail and stabilize scores faster.",
  },
  hi: {
    placeholder: "Jo badla hai, kab zyada hota hai, aur din bhar par kya asar padta hai, woh likhiye...",
    sessionReady: "Session typed ya voice response ke liye ready hai.",
    startSuccess: "Session Hindi mein start ho gaya.",
    turnSuccess: "Turn process ho gaya. Confidence board update ho gaya.",
    runtimeReady: "Runtime connect ho gaya. Profile pick kijiye ya seedha chat start kijiye.",
    nudgeIntro: "In nudges ka use karke zyada useful detail share kijiye aur scores ko jaldi stable banaiye.",
  },
  hinglish: {
    placeholder: "Kya change hua, kab zyada feel hota hai, aur daily routine par kya impact hai, woh share karo...",
    sessionReady: "Session typed ya voice turns ke liye ready hai.",
    startSuccess: "Session Hinglish mein start ho gaya.",
    turnSuccess: "Turn process ho gaya. Confidence board update ho gaya.",
    runtimeReady: "Runtime connect ho gaya. Demo profile launch karo ya chat start karo.",
    nudgeIntro: "In nudges se thodi aur concrete detail do, taaki confidence faster lock ho sake.",
  },
};

const NUDGE_LIBRARY = {
  en: {
    example: {
      title: "Add one recent example",
      description: "One concrete moment often gives the scorer more signal than a general statement.",
      text: "One recent moment that stands out is ",
    },
    timing: {
      title: "Add timing",
      description: "Say when it feels strongest, like mornings, nights, work hours, or after calls.",
      text: "This usually feels strongest when ",
    },
    impact: {
      title: "Add daily impact",
      description: "Share how it changed study, work, sleep, appetite, relationships, or routine.",
      text: "Because of this, my daily routine has changed by ",
    },
    mood: {
      title: "Name the heavier part",
      description: "Clarify whether the core issue is sadness, numbness, low interest, or guilt.",
      text: "The hardest part has been ",
    },
    sleep: {
      title: "Clarify the sleep pattern",
      description: "Say whether the issue is falling asleep, waking up, or sleeping too much.",
      text: "My sleep problem looks more like ",
    },
    anxiety: {
      title: "Describe the worry pattern",
      description: "Explain whether it feels mental, physical, or both.",
      text: "The worry feels most like ",
    },
    safety: {
      title: "Answer briefly if easier",
      description: "A short yes/no plus one line is enough when the question feels sensitive.",
      text: "A short answer is: ",
    },
  },
  hi: {
    example: {
      title: "Ek recent example dijiye",
      description: "Sirf ek recent moment batane se bhi kaafi signal mil jata hai.",
      text: "Ek recent example jo yaad aa raha hai woh yeh hai ki ",
    },
    timing: {
      title: "Kab zyada hota hai batayiye",
      description: "Subah, raat, kaam ke waqt, ya akela hone par zyada hota hai to woh batayiye.",
      text: "Yeh zyada tab hota hai jab ",
    },
    impact: {
      title: "Rozmarra par asar batayiye",
      description: "Padhai, kaam, neend, bhook, ya routine par kya farq pada hai woh likhiye.",
      text: "Iska roz ke routine par asar yeh hua hai ki ",
    },
    mood: {
      title: "Sabse bhaari hissa batayiye",
      description: "Udaasi, dil na lagna, guilt, ya thakan mein se kya zyada bhaari hai woh batayiye.",
      text: "Sabse bhaari hissa mere liye yeh hai ki ",
    },
    sleep: {
      title: "Neend ka pattern clear kijiye",
      description: "Sone mein der lagti hai, beech mein uthte hain, ya zyada sote hain, woh batayiye.",
      text: "Neend ki dikkat zyada is tarah ki hai ki ",
    },
    anxiety: {
      title: "Chinta ka pattern batayiye",
      description: "Zehn ki chinta, sharir ka tanav, ya dono saath mein feel hota hai, woh likhiye.",
      text: "Chinta zyada mujhe is tarah feel hoti hai ki ",
    },
    safety: {
      title: "Chhota jawab bhi theek hai",
      description: "Sensitive sawal par haan/nahin aur ek chhoti line bhi kaafi hai.",
      text: "Mera seedha jawab yeh hai ki ",
    },
  },
  hinglish: {
    example: {
      title: "One recent scene add karo",
      description: "Ek real recent scene batane se conversation zyada useful ho jati hai.",
      text: "Ek recent scene jo stick hua woh yeh tha ki ",
    },
    timing: {
      title: "Timing batao",
      description: "Kab spike hota hai, like mornings, nights, work ke time, ya alone hone par.",
      text: "Yeh mostly tab strong lagta hai jab ",
    },
    impact: {
      title: "Daily impact batao",
      description: "Routine, sleep, work, study, appetite, ya social life par kya effect hai woh add karo.",
      text: "Is wajah se meri daily life par yeh impact hua hai ki ",
    },
    mood: {
      title: "Heaviest feeling choose karo",
      description: "Low mood, dil na lagna, guilt, ya thakan mein se kya strongest hai woh bolo.",
      text: "Sabse heavy part mere liye yeh hai ki ",
    },
    sleep: {
      title: "Sleep issue clarify karo",
      description: "Sleep start karne mein, beech mein uthne mein, ya oversleeping mein issue hai woh bolo.",
      text: "Mera sleep issue zyada is type ka hai ki ",
    },
    anxiety: {
      title: "Worry pattern explain karo",
      description: "Mind worry, body tension, ya dono ka mix ho to woh clear karo.",
      text: "Mujhe worry zyada is tarah feel hoti hai ki ",
    },
    safety: {
      title: "Short answer bhi enough hai",
      description: "Sensitive point par short yes/no plus ek line bhi acceptable hai.",
      text: "Short answer yeh hai ki ",
    },
  },
};

const chatLog = document.getElementById("chatLog");
const sessionMeta = document.getElementById("sessionMeta");
const sessionBadge = document.getElementById("sessionBadge");
const sessionGoal = document.getElementById("sessionGoal");
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
const progressMeterFill = document.getElementById("progressMeterFill");
const progressMeterLabel = document.getElementById("progressMeterLabel");
const bonusSignals = document.getElementById("bonusSignals");
const nudgeDeck = document.getElementById("nudgeDeck");
const nudgeSubtitle = document.getElementById("nudgeSubtitle");
const composerHelper = document.getElementById("composerHelper");

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
const plannerStage = document.getElementById("plannerStage");
const plannerAction = document.getElementById("plannerAction");
const plannerTopic = document.getElementById("plannerTopic");
const plannerStyle = document.getElementById("plannerStyle");
const plannerTrend = document.getElementById("plannerTrend");
const plannerEfficiency = document.getElementById("plannerEfficiency");
const plannerHeldBack = document.getElementById("plannerHeldBack");
const plannerTransition = document.getElementById("plannerTransition");
const topicMap = document.getElementById("topicMap");
const unresolvedCount = document.getElementById("unresolvedCount");
const unresolvedList = document.getElementById("unresolvedList");
const reviewCount = document.getElementById("reviewCount");
const reviewList = document.getElementById("reviewList");
const itemTableBody = document.getElementById("itemTableBody");
const evidenceList = document.getElementById("evidenceList");
const personalizationBlend = document.getElementById("personalizationBlend");
const personalizationPacing = document.getElementById("personalizationPacing");
const personalizationSummary = document.getElementById("personalizationSummary");

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
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${tone}`;
}

function humanizeToken(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function updateSessionBadge() {
  if (!state.sessionId) {
    sessionBadge.textContent = "No session";
    sessionBadge.className = "chip soft";
    return;
  }
  sessionBadge.textContent = `${state.language.toUpperCase()} · ${state.sessionId.slice(0, 8)}`;
  sessionBadge.className = "chip";
}

function setLink(anchor, href) {
  if (!href) {
    anchor.href = "#";
    anchor.classList.add("disabled-link");
    return;
  }
  anchor.href = href;
  anchor.classList.remove("disabled-link");
}

function runtimeToText(payload) {
  const safetyMode = payload.hybrid_safety_enabled
    ? "local hybrid safety enabled"
    : payload.semantic_safety_enabled
      ? "semantic safety enabled"
      : "rule + HF safety enabled";
  return `${payload.provider} runtime · chat ${payload.chat_model} · extraction ${payload.extraction_model} · ${safetyMode}`;
}

function renderRuntime(payload) {
  state.runtime = payload;
  runtimeInfo.textContent = runtimeToText(payload);
}

function renderApiLinks(links) {
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
      <button type="button" class="button secondary profile-launch" data-profile-id="${escapeHtml(profile.patient_id)}">Launch scenario</button>
    `;
    profileList.appendChild(card);
  });

  document.querySelectorAll(".profile-launch").forEach((button) => {
    button.addEventListener("click", async () => {
      const profileId = button.getAttribute("data-profile-id");
      const profile = state.profiles.find((entry) => entry.patient_id === profileId);
      if (profile) {
        await launchProfile(profile);
      }
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
  applyLanguageDefaults(state.language);
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
    renderRuntime(payload.runtime);
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
  renderRuntime(runtimePayload);
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

function applyLanguageDefaults(language) {
  const copy = LANGUAGE_UI[language] || LANGUAGE_UI.en;
  messageInput.placeholder = copy.placeholder;
  nudgeSubtitle.textContent = copy.nudgeIntro;
}

async function startSession() {
  setBusy(true);
  try {
    state.language = languageSelect.value;
    applyLanguageDefaults(state.language);
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
    sessionMeta.textContent = `Session ${state.sessionId} · language ${state.language.toUpperCase()} · adaptive screening ready`;
    updateSessionBadge();
    downloadButton.disabled = true;
    setLink(summaryLink, null);
    setLink(exportLink, null);
    resetInsightPanel();
    updateVoiceStatus(LANGUAGE_UI[state.language].sessionReady);
    setStatusBanner(LANGUAGE_UI[state.language].startSuccess, "success");
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
  const isSystem = String(turn.text || "").startsWith("[System]");
  const speakerLabel = isSystem
    ? "System"
    : turn.speaker === "assistant"
      ? "Screening guide"
      : "Participant";
  card.className = `message ${isSystem ? "system" : turn.speaker}`;
  card.innerHTML = `
    <span class="speaker">${escapeHtml(speakerLabel)}</span>
    <div class="bubble">${escapeHtml(String(turn.text || ""))}</div>
  `;
  chatLog.appendChild(card);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function buildSessionGoal(dialogue, safety) {
  if (safety.level === "urgent") {
    return "Pause routine screening and route the conversation to urgent human review.";
  }
  if (dialogue.stage === "rapport") {
    return "Warm up the conversation, identify the first symptom cluster, and keep the opening low-pressure.";
  }
  if (dialogue.stage === "clarification") {
    return "Resolve mixed evidence so the score becomes stable instead of guessed.";
  }
  if (dialogue.stage === "safety") {
    return "Move carefully into a focused safety check while keeping the interaction supportive.";
  }
  if (dialogue.stage === "summary") {
    return "The evidence is nearly complete. Prepare a stable structured summary and final clarification.";
  }
  return "Expand the symptom picture with concrete details about pattern, intensity, and daily impact.";
}

function buildProgressLabel(coverage) {
  const remaining = Math.max((coverage.total_items || 0) - (coverage.touched_items || 0), 0);
  return `${coverage.touched_items}/${coverage.total_items} mapped · ${coverage.resolved_items.length} confidence locks · ${remaining} still open`;
}

function buildBonusSignals(dialogue, coverage) {
  const completion = Math.round((coverage.completion_ratio || 0) * 100);
  const stability = Number(dialogue.disclosure.resolved_per_user_turn || 0).toFixed(2);
  return [
    `${completion}% map revealed`,
    `${coverage.resolved_items.length} evidence locks`,
    `${stability} stable items / turn`,
    dialogue.next_action === "risk_check" ? "Safety checkpoint live" : `${humanizeToken(dialogue.target_topic)} in focus`,
  ];
}

function buildResponsePosture(userStyle) {
  if (userStyle.openness === "guarded") {
    return "gentle, low-pressure prompts";
  }
  if (userStyle.verbosity === "brief") {
    return "tight one-question pacing";
  }
  if (userStyle.verbosity === "detailed") {
    return "narrative-friendly follow-ups";
  }
  return "balanced, guided exploration";
}

function buildPersonalizationSummary(dialogue) {
  const { verbosity, openness, code_mix: codeMix, distress_trend: distressTrend } = dialogue.user_style;
  return `Detected style: ${verbosity} responses, ${openness} disclosure, ${codeMix} code-mix, and ${distressTrend} distress trend. ManoVarta mirrors that style lightly so the conversation feels natural while still collecting stronger screening evidence.`;
}

function buildComposerHelper(dialogue) {
  if (dialogue.next_action === "risk_check") {
    return "A short answer is enough here. The assistant is doing a careful safety check before returning to normal screening.";
  }
  if (dialogue.user_style.openness === "guarded") {
    return "Low-pressure mode is active: one recent example or one daily-life impact is enough to move the confidence meter.";
  }
  if (dialogue.user_style.verbosity === "brief") {
    return "Brief responses are okay. Adding one concrete example or timing detail will unlock more score confidence.";
  }
  if (dialogue.user_style.verbosity === "detailed") {
    return "Narrative mode is active: stay with the part that feels most important and the assistant will map it back to the screening graph.";
  }
  return "The assistant is mirroring your pace and asking the next highest-value follow-up based on evidence confidence.";
}

function buildNudgeSubtitle(dialogue) {
  if (dialogue.next_action === "risk_check") {
    return "Sensitive checkpoint: a short direct answer is enough. You do not need to write a long paragraph.";
  }
  if (dialogue.user_style.openness === "guarded") {
    return "Pick the easiest nudge. ManoVarta will use that small detail to reduce pressure and keep moving.";
  }
  if (dialogue.user_style.verbosity === "brief") {
    return "One extra concrete detail can move the session from vague signal to stable evidence.";
  }
  return "These nudges help the system collect stronger evidence with fewer turns.";
}

function buildNudgeMeta(dialogue) {
  if (dialogue.next_action === "risk_check") {
    return "Low-pressure prompt";
  }
  if (dialogue.user_style.openness === "guarded" || dialogue.user_style.verbosity === "brief") {
    return "Fast confidence unlock";
  }
  if (dialogue.user_style.verbosity === "detailed") {
    return "Narrative booster";
  }
  return "Evidence booster";
}

function buildSessionMetaLine(dialogue, coverage, safety) {
  const stage = humanizeToken(dialogue.stage);
  const topic = humanizeToken(dialogue.target_topic);
  const turns = dialogue.user_turns;
  const mapped = `${coverage.touched_items}/${coverage.total_items}`;
  const safetyLine = safety.level === "none" ? "standard safety monitoring" : `${humanizeToken(safety.level)} safety posture`;
  return `Live session · ${stage} stage · ${mapped} items mapped · ${turns} user turns · ${topic} in focus · ${safetyLine}`;
}

function pickNudges(language, dialogue) {
  const bank = NUDGE_LIBRARY[language] || NUDGE_LIBRARY.en;
  const nudges = [];
  const add = (key) => {
    const entry = bank[key];
    if (entry && !nudges.includes(entry)) {
      nudges.push(entry);
    }
  };

  if (dialogue.next_action === "risk_check" || dialogue.target_topic === "safety") {
    add("safety");
  }

  add(dialogue.target_topic);

  if (dialogue.user_style.verbosity === "brief") {
    add("example");
    add("timing");
    add("impact");
  } else if (dialogue.user_style.openness === "guarded") {
    add("impact");
    add("example");
    add("timing");
  } else {
    add("example");
    add("impact");
    add("timing");
  }

  return nudges.slice(0, 3);
}

function applyNudge(text) {
  const current = messageInput.value.trim();
  messageInput.value = current ? `${current} ${text}` : text;
  messageInput.focus();
  messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
}

function renderNudges(language, dialogue) {
  const nudges = pickNudges(language, dialogue);
  nudgeDeck.innerHTML = "";
  nudges.forEach((nudge) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nudge-card";
    button.innerHTML = `
      <span class="nudge-meta">${escapeHtml(buildNudgeMeta(dialogue))}</span>
      <strong>${escapeHtml(nudge.title)}</strong>
      <span>${escapeHtml(nudge.description)}</span>
    `;
    button.addEventListener("click", () => applyNudge(nudge.text));
    nudgeDeck.appendChild(button);
  });
}

function renderTopicMap(topicStates) {
  if (!topicStates.length) {
    topicMap.innerHTML = '<span class="topic-pill">No topic map yet.</span>';
    return;
  }

  topicMap.innerHTML = "";
  topicStates.forEach((topic) => {
    const pill = document.createElement("span");
    pill.className = `topic-pill ${topic.status}`;
    pill.innerHTML = `
      <strong>${escapeHtml(topic.label)}</strong>
      <span>${escapeHtml(topic.status)} · ${Number(topic.confidence || 0).toFixed(2)}</span>
    `;
    topicMap.appendChild(pill);
  });
}

function renderSnapshot(payload) {
  const { snapshot, summary, rows } = payload;
  const safeRows = rows || [];
  const dialogue = snapshot.coverage?.dialogue || {
    stage: "rapport",
    next_action: "open_question",
    target_topic: "mood",
    held_back_items: [],
    transition_hint: "Start a conversation to see how steering changes.",
    user_style: { verbosity: "balanced", openness: "cautious", distress_trend: "unclear", code_mix: "low" },
    disclosure: { items_per_user_turn: 0, resolved_per_user_turn: 0 },
    user_turns: 0,
  };
  const coverage = snapshot.coverage || {
    total_items: 16,
    touched_items: 0,
    resolved_items: [],
    next_items: [],
    review_items: [],
    completion_ratio: 0,
  };

  phqTotal.textContent = snapshot.totals.PHQ9 ?? 0;
  gadTotal.textContent = snapshot.totals.GAD7 ?? 0;
  safetyLevel.textContent = snapshot.safety.level;
  safetyLevel.className = `metric-value small ${snapshot.safety.level}`;
  snapshotMode.textContent = snapshot.mode;
  summaryText.textContent = summary;

  const completion = Math.round((coverage.completion_ratio || 0) * 100);
  coverageText.textContent = `Coverage ${coverage.touched_items}/${coverage.total_items}`;
  progressMeterFill.style.width = `${Math.max(completion, coverage.touched_items ? 8 : 0)}%`;
  progressMeterLabel.textContent = buildProgressLabel(coverage);

  plannerStage.textContent = dialogue.stage;
  plannerStage.className = `chip soft stage-${dialogue.stage}`;
  plannerAction.textContent = humanizeToken(dialogue.next_action);
  plannerTopic.textContent = humanizeToken(dialogue.target_topic);
  plannerStyle.textContent = `${dialogue.user_style.verbosity} · ${dialogue.user_style.openness}`;
  plannerTrend.textContent = humanizeToken(dialogue.user_style.distress_trend);
  plannerEfficiency.textContent = `${Number(dialogue.disclosure.items_per_user_turn || 0).toFixed(2)} items/turn`;
  plannerHeldBack.textContent = dialogue.held_back_items.length ? dialogue.held_back_items.join(", ") : "none";
  plannerTransition.textContent = `${dialogue.rationale || "Planner rationale unavailable."} ${dialogue.transition_hint || ""}`.trim();
  sessionGoal.textContent = buildSessionGoal(dialogue, snapshot.safety);
  sessionMeta.classList.remove("empty");
  sessionMeta.textContent = buildSessionMetaLine(dialogue, coverage, snapshot.safety);

  bonusSignals.innerHTML = "";
  buildBonusSignals(dialogue, coverage).forEach((signal) => {
    const chip = document.createElement("span");
    chip.className = "signal-pill";
    chip.textContent = signal;
    bonusSignals.appendChild(chip);
  });

  personalizationBlend.textContent = `${dialogue.user_style.code_mix} code-mix`;
  personalizationPacing.textContent = buildResponsePosture(dialogue.user_style);
  personalizationSummary.textContent = buildPersonalizationSummary(dialogue);
  composerHelper.textContent = buildComposerHelper(dialogue);
  nudgeSubtitle.textContent = buildNudgeSubtitle(dialogue);
  renderNudges(snapshot.language, dialogue);
  renderTopicMap(coverage.topic_states || []);

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
  safetyLevel.className = "metric-value small none";
  snapshotMode.textContent = "heuristic";
  coverageText.textContent = "Coverage 0/16";
  progressMeterFill.style.width = "0%";
  progressMeterLabel.textContent = "0 stabilized · 0 touched · 16 still open";
  plannerStage.textContent = "rapport";
  plannerStage.className = "chip soft";
  plannerAction.textContent = "Open Question";
  plannerTopic.textContent = "Mood";
  plannerStyle.textContent = "balanced · cautious";
  plannerTrend.textContent = "Unclear";
  plannerEfficiency.textContent = "0.00 items/turn";
  plannerHeldBack.textContent = "none";
  plannerTransition.textContent = "Start a conversation to see how the next topic is selected.";
  summaryText.textContent = "Start a conversation to generate the first summary.";
  sessionGoal.textContent = "Build trust, isolate the main concern, and collect enough evidence for stable scoring.";
  topicMap.innerHTML = '<span class="topic-pill">No topic map yet.</span>';
  unresolvedCount.textContent = "0 queued";
  reviewCount.textContent = "0 flagged";
  unresolvedList.innerHTML = "<li>No follow-up queue yet.</li>";
  reviewList.innerHTML = "<li>No review flags right now.</li>";
  itemTableBody.innerHTML = '<tr><td colspan="4" class="empty-cell">No item scores yet.</td></tr>';
  evidenceList.innerHTML = '<li class="empty-cell">No evidence spans yet.</li>';
  bonusSignals.innerHTML = `
    <span class="signal-pill">Voice interaction</span>
    <span class="signal-pill">Adaptive prompts</span>
    <span class="signal-pill">Safety gating</span>
  `;
  personalizationBlend.textContent = "low code-mix";
  personalizationPacing.textContent = "gentle and focused";
  personalizationSummary.textContent = "Start a session to see how ManoVarta adapts to the user’s language style and disclosure pace.";
  renderNudges(state.language, {
    target_topic: "mood",
    next_action: "open_question",
    user_style: { verbosity: "balanced", openness: "cautious", code_mix: "low" },
  });
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
    setStatusBanner(LANGUAGE_UI[state.language].turnSuccess, "success");
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
    applyLanguageDefaults(state.language);
    updateSessionBadge();
    updateVoiceStatus(`Voice language set to ${state.language}.`);
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
  if (!speechSynthesisApi || !speakToggle.checked || turn.speaker !== "assistant") {
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
applyLanguageDefaults(state.language);
updateSessionBadge();
resetInsightPanel();

fetchBootstrap()
  .then(() => {
    setStatusBanner(LANGUAGE_UI[state.language].runtimeReady, "success");
  })
  .catch((error) => {
    console.error(error);
    runtimeInfo.textContent = "Runtime config unavailable.";
    setStatusBanner("Backend bootstrap failed. Verify API service.", "error");
  });
