const state = {
  sessionId: null,
  language: "en",
  exportPayload: null,
  profiles: [],
  runtime: null,
  isBusy: false,
  recentCheckins: [],
  voiceLoopArmed: false,
  pendingNudge: null,
};

const HISTORY_KEY = "manovarta_recent_checkins_v2";

const TOKEN_LABELS = {
  hi: {
    check_in: "बातचीत",
    mood: "मनोदशा",
    sleep: "नींद",
    energy: "ऊर्जा",
    self_view: "अपने बारे में सोच",
    focus: "ध्यान",
    anxiety: "चिंता",
    safety: "सुरक्षा",
    none: "सामान्य",
    review: "समीक्षा",
    urgent: "तत्काल",
    hybrid: "संकर",
    local: "स्थानीय",
    rapport: "शुरुआती समझ",
    clarification: "स्पष्टता",
    summary: "सार",
    exploration: "खोज",
    risk_check: "सुरक्षा-जाँच",
    clarify: "स्पष्ट करना",
    symptom_probe: "लक्षण-जाँच",
    summarize: "सार बनाना",
    handoff: "मानवीय सहायता",
    rising: "बढ़ता हुआ",
    easing: "हल्का होता हुआ",
    stable: "स्थिर",
  },
};

const LANGUAGE_UI = {
  en: {
    placeholder: "Describe what changed, when it happens, and how it affects your day...",
    sessionReady: "You can type or speak whenever you are ready.",
    startSuccess: "Your private check-in has started in English.",
    turnSuccess: "Thanks. ManoVarta is holding onto that and is ready for the next part.",
    runtimeReady: "Ready when you are. Start with whatever feels easiest to say.",
    nudgeIntro: "These small prompts help you share useful detail without making the conversation feel heavy.",
  },
  hi: {
    placeholder: "जो बदला है, कब ज़्यादा होता है, और दिन भर पर क्या असर पड़ता है, वह लिखिए...",
    sessionReady: "अब आप आराम से टाइप या बोल सकते हैं।",
    startSuccess: "आपका निजी चेक-इन हिंदी में शुरू हो गया।",
    turnSuccess: "शुक्रिया। मनोवार्ता ने यह संभाल लिया है और अगले जवाब के लिए तैयार है।",
    runtimeReady: "सब तैयार है। जो सबसे आसान लगे, वहीं से बात शुरू कीजिए।",
    nudgeIntro: "ये छोटे संकेत बिना दबाव के ज़रूरी विवरण साझा करने में मदद करते हैं।",
  },
  hinglish: {
    placeholder: "Kya change hua, kab zyada feel hota hai, aur daily routine par kya impact hai, woh share karo...",
    sessionReady: "Ab tum aaraam se type ya bol sakte ho.",
    startSuccess: "Tumhara private check-in Hinglish mein start ho gaya.",
    turnSuccess: "Thanks. ManoVarta ne yeh note kar liya hai aur next message ke liye ready hai.",
    runtimeReady: "Everything is ready. Jo easiest lage, usse start karo.",
    nudgeIntro: "Yeh nudges thodi aur clear detail lane mein help karte hain, bina conversation ko heavy banaye.",
  },
};

const STARTER_LIBRARY = {
  en: [
    {
      title: "Start with energy",
      description: "Use this if the main change feels like fatigue or heaviness.",
      text: "Lately I have been feeling more drained than usual, and it is changing how I get through the day.",
    },
    {
      title: "Start with sleep",
      description: "Use this if sleep has been the clearest sign that something shifted.",
      text: "My sleep has changed a lot lately, and I think it is affecting my mood and focus.",
    },
    {
      title: "Start with worry",
      description: "Use this if the mind feels busy, tense, or restless.",
      text: "My mind has been worrying a lot, and it feels hard to settle down even when nothing is happening.",
    },
  ],
  hi: [
    {
      title: "थकान से शुरुआत कीजिए",
      description: "जब थकान या बोझ सबसे ज़्यादा महसूस हो रहा हो।",
      text: "पिछले कुछ दिनों से मुझे सामान्य से ज़्यादा थकान महसूस हो रही है, और दिन निकालना मुश्किल लग रहा है।",
    },
    {
      title: "नींद से शुरुआत कीजिए",
      description: "जब सबसे पहला बदलाव नींद में दिखाई दिया हो।",
      text: "मेरी नींद का पैटर्न काफ़ी बदल गया है, और उसका असर मनोदशा और ध्यान पर पड़ रहा है।",
    },
    {
      title: "चिंता से शुरुआत कीजिए",
      description: "जब दिमाग बहुत तेज़ चल रहा हो या तनाव शरीर में महसूस हो रहा हो।",
      text: "मेरा दिमाग काफ़ी ज़्यादा चिंता में रहता है और बिना वजह भी तनाव बना रहता है।",
    },
  ],
  hinglish: [
    {
      title: "Low energy se start karo",
      description: "Jab sabse obvious change thakan ya heaviness ho.",
      text: "Lately mujhe normal se kaafi zyada drained feel ho raha hai, aur din nikalna heavy lag raha hai.",
    },
    {
      title: "Sleep se start karo",
      description: "Jab sleep issue sabse clear signal ho.",
      text: "Meri sleep pattern kaafi off ho gayi hai, aur uska impact mood aur focus par clearly aa raha hai.",
    },
    {
      title: "Worry se start karo",
      description: "Jab mind overactive ho ya tension body mein feel ho.",
      text: "Mind kaafi overactive chal raha hai, aur bina reason bhi tension aur restlessness feel hoti rehti hai.",
    },
  ],
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
      title: "एक हाल का उदाहरण दीजिए",
      description: "सिर्फ़ एक हाल की घटना बताने से भी काफ़ी संकेत मिल जाते हैं।",
      text: "एक हाल का उदाहरण जो याद आ रहा है, वह यह है कि ",
    },
    timing: {
      title: "कब ज़्यादा होता है, बताइए",
      description: "सुबह, रात, काम के समय, या अकेले होने पर ज़्यादा होता है तो वह बताइए।",
      text: "यह ज़्यादा तब होता है जब ",
    },
    impact: {
      title: "रोज़मर्रा पर असर बताइए",
      description: "पढ़ाई, काम, नींद, भूख, या दिनचर्या पर क्या फ़र्क पड़ा है, वह लिखिए।",
      text: "इसका रोज़ की दिनचर्या पर असर यह हुआ है कि ",
    },
    mood: {
      title: "सबसे भारी हिस्सा बताइए",
      description: "उदासी, मन न लगना, अपराधबोध, या थकान में से क्या सबसे भारी है, वह बताइए।",
      text: "मेरे लिए सबसे भारी हिस्सा यह है कि ",
    },
    sleep: {
      title: "नींद का ढंग साफ़ कीजिए",
      description: "सोने में देर लगती है, बीच में उठते हैं, या बहुत ज़्यादा सोते हैं, वह बताइए।",
      text: "नींद की दिक्कत ज़्यादा इस तरह की है कि ",
    },
    anxiety: {
      title: "चिंता का ढंग बताइए",
      description: "दिमाग की चिंता, शरीर का तनाव, या दोनों साथ में महसूस होते हैं, वह लिखिए।",
      text: "चिंता मुझे ज़्यादा इस तरह महसूस होती है कि ",
    },
    safety: {
      title: "छोटा जवाब भी ठीक है",
      description: "संवेदनशील सवाल पर हाँ/नहीं और एक छोटी पंक्ति भी काफ़ी है।",
      text: "मेरा सीधा जवाब यह है कि ",
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
const voicePreview = document.getElementById("voicePreview");
const voicePreviewText = document.getElementById("voicePreviewText");
const voiceSendMode = document.getElementById("voiceSendMode");
const voiceUseButton = document.getElementById("voiceUseButton");
const statusBanner = document.getElementById("statusBanner");
const progressMeterFill = document.getElementById("progressMeterFill");
const progressMeterLabel = document.getElementById("progressMeterLabel");
const bonusSignals = document.getElementById("bonusSignals");
const nudgeDeck = document.getElementById("nudgeDeck");
const nudgeSubtitle = document.getElementById("nudgeSubtitle");
const composerHelper = document.getElementById("composerHelper");
const patientSummary = document.getElementById("patientSummary");
const whyThisQuestion = document.getElementById("whyThisQuestion");
const safetyNarrative = document.getElementById("safetyNarrative");
const starterDeck = document.getElementById("starterDeck");
const profileNameInput = document.getElementById("profileNameInput");
const profileAgeInput = document.getElementById("profileAgeInput");
const profileOccupationInput = document.getElementById("profileOccupationInput");
const profileLivingInput = document.getElementById("profileLivingInput");
const profileSupportInput = document.getElementById("profileSupportInput");
const profileContextInput = document.getElementById("profileContextInput");
const ritualCount = document.getElementById("ritualCount");
const ritualStreak = document.getElementById("ritualStreak");
const ritualCopy = document.getElementById("ritualCopy");
const historyList = document.getElementById("historyList");
const reflectionPrompt = document.getElementById("reflectionPrompt");

const runtimeInfo = document.getElementById("runtimeInfo");
const runtimeDetail = document.getElementById("runtimeDetail");
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
const detailModeLabel = document.getElementById("detailModeLabel");
const demoPanel = document.getElementById("demoPanel");
const insightPanel = document.getElementById("insightPanel");
const demoToggle = document.getElementById("demoToggle");
const insightsToggle = document.getElementById("insightsToggle");
const architectureButton = document.getElementById("architectureButton");
const architectureClose = document.getElementById("architectureClose");
const architectureModal = document.getElementById("architectureModal");
const backstageToggle = document.getElementById("backstageToggle");
const backstageClose = document.getElementById("backstageClose");
const backstagePanel = document.getElementById("backstagePanel");
const languageTabs = Array.from(document.querySelectorAll(".language-tab"));

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;
const speechSynthesisApi = window.speechSynthesis || null;

let recognition = null;
let listening = false;
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let currentAudio = null;
let pendingVoiceTranscript = "";
const reviewMode = window.location.pathname.startsWith("/review");

function setBusy(isBusy) {
  state.isBusy = isBusy;
  startButton.disabled = isBusy;
  chatForm.querySelector('button[type="submit"]').disabled = isBusy;
}

function handsFreeVoiceEnabled() {
  return Boolean(autoSendToggle?.checked && speakToggle?.checked);
}

function setStatusBanner(message, tone = "info") {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${tone}`;
}

function setHasHistory(hasHistory) {
  document.body.classList.toggle("has-history", Boolean(hasHistory));
}

function setDisclosureState(panel, button, open, labels) {
  if (!panel || !button) {
    return;
  }
  panel.classList.toggle("is-hidden", !open);
  panel.setAttribute("aria-hidden", String(!open));
  button.setAttribute("aria-expanded", String(open));
  button.textContent = open ? labels.close : labels.open;
}

function toggleDisclosure(panel, button, labels) {
  const open = panel.classList.contains("is-hidden");
  setDisclosureState(panel, button, open, labels);
}

function openArchitectureModal() {
  architectureModal.classList.remove("is-hidden");
  architectureModal.setAttribute("aria-hidden", "false");
}

function closeArchitectureModal() {
  architectureModal.classList.add("is-hidden");
  architectureModal.setAttribute("aria-hidden", "true");
}

function setSessionLiveState(isLive) {
  document.body.classList.toggle("session-live", Boolean(isLive));
}

function humanizeToken(value, language = state.language) {
  const raw = String(value || "");
  const normalized = raw.replaceAll(" ", "_").toLowerCase();
  const localized = TOKEN_LABELS[language]?.[normalized];
  if (localized) {
    return localized;
  }
  return raw
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function renderStarterDeck(language) {
  const starters = STARTER_LIBRARY[language] || STARTER_LIBRARY.en;
  starterDeck.innerHTML = "";
  starters.forEach((starter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "starter-card";
    button.innerHTML = `
      <strong>${escapeHtml(starter.title)}</strong>
      <span>${escapeHtml(starter.description)}</span>
    `;
    button.addEventListener("click", () => applyNudge(starter.text));
    starterDeck.appendChild(button);
  });
}

function syncLanguageTabs(language) {
  languageTabs.forEach((button) => {
    const active = button.getAttribute("data-language") === language;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
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

function collectProfileContext() {
  const ageValue = Number(profileAgeInput?.value || "");
  return {
    preferred_name: profileNameInput?.value.trim() || null,
    age: Number.isFinite(ageValue) && ageValue > 0 ? ageValue : null,
    occupation: profileOccupationInput?.value.trim() || null,
    living_situation: profileLivingInput?.value.trim() || null,
    support_system: profileSupportInput?.value.trim() || null,
    context_note: profileContextInput?.value.trim() || null,
    recent_checkins: (state.recentCheckins || []).slice(0, 3).map((entry) => ({
      topic: entry.topic || "check_in",
      language: entry.language || state.language,
      safety: entry.safety || "none",
      completion: Number(entry.completion || 0),
      summary: String(entry.summary || "").slice(0, 180),
    })),
  };
}

function loadRecentCheckins() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error(error);
    return [];
  }
}

function saveRecentCheckins() {
  try {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(state.recentCheckins.slice(0, 6)));
  } catch (error) {
    console.error(error);
  }
}

function dayKey(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

function computeCheckinStreak(entries) {
  const uniqueDays = Array.from(new Set(entries.map((entry) => dayKey(entry.savedAt)).filter(Boolean)));
  if (!uniqueDays.length) {
    return 0;
  }

  const sorted = uniqueDays
    .map((value) => new Date(`${value}T00:00:00`))
    .sort((left, right) => right - left);
  let streak = 1;
  for (let index = 1; index < sorted.length; index += 1) {
    const previous = sorted[index - 1];
    const current = sorted[index];
    const delta = (previous - current) / (1000 * 60 * 60 * 24);
    if (delta === 1) {
      streak += 1;
    } else if (delta > 1) {
      break;
    }
  }
  return streak;
}

function formatCheckinDate(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return "Recently";
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function renderHistory() {
  if (!historyList || !ritualCount || !ritualStreak || !ritualCopy) {
    return;
  }

  const entries = state.recentCheckins || [];
  setHasHistory(entries.length > 0);
  ritualCount.textContent = String(entries.length);
  ritualStreak.textContent = String(computeCheckinStreak(entries));

  if (!entries.length) {
    ritualCopy.textContent = "After your first conversation, ManoVarta will keep a lightweight private memory here so the app feels easier to return to.";
    historyList.innerHTML = `
      <article class="history-card empty">
        <p class="history-meta">No check-ins yet</p>
        <p>Start one conversation and your recent reflections will appear here.</p>
      </article>
    `;
    return;
  }

  const latest = entries[0];
  ritualCopy.textContent = state.language === "hi"
    ? `हाल में सहेजा गया मुख्य फोकस: ${humanizeToken(latest.topic || "check_in", "hi")} (${String(latest.language || "en").toUpperCase()}).`
    : `Latest saved focus: ${humanizeToken(latest.topic || "check_in").toLowerCase()} in ${String(latest.language || "en").toUpperCase()}.`;

  historyList.innerHTML = "";
  entries.slice(0, 4).forEach((entry) => {
    const card = document.createElement("article");
    card.className = "history-card";
    const summary = String(entry.summary || "A private check-in was saved on this device.").slice(0, 140);
    card.innerHTML = `
      <p class="history-meta">${escapeHtml(formatCheckinDate(entry.savedAt))} · ${escapeHtml(String(entry.language || "en").toUpperCase())}</p>
      <strong>${escapeHtml(humanizeToken(entry.topic || "check_in", state.language))}</strong>
      <p>${escapeHtml(summary)}${summary.length >= 140 ? "..." : ""}</p>
      <div class="history-tags">
        <span class="history-tag">${escapeHtml(Math.round(Number(entry.completion || 0) * 100))}% complete</span>
        <span class="history-tag">${escapeHtml(state.language === "hi" ? `${humanizeToken(entry.safety || "none", "hi")} सुरक्षा` : `${humanizeToken(entry.safety || "none")} safety`)}</span>
      </div>
    `;
    historyList.appendChild(card);
  });
}

function setVoicePreview(transcript = "", { visible = false } = {}) {
  pendingVoiceTranscript = transcript || "";
  if (!voicePreview || !voicePreviewText || !voiceSendMode) {
    return;
  }
  voicePreview.classList.toggle("is-hidden", !visible);
  voicePreviewText.textContent = transcript || "Transcript preview";
  voiceSendMode.textContent = autoSendToggle?.checked ? "Sends when you stop talking" : "Review before sending";
  if (voiceUseButton) {
    voiceUseButton.textContent = autoSendToggle?.checked ? "Send now" : "Use transcript";
  }
}

function detectRecordingMimeType() {
  if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
    return "";
  }
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
    "audio/wav",
  ];
  return candidates.find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
}

function rememberCheckin(payload) {
  const snapshot = payload?.snapshot;
  if (!snapshot || !state.sessionId) {
    return;
  }

  const entry = {
    sessionId: state.sessionId,
    savedAt: new Date().toISOString(),
    language: snapshot.language || state.language,
    topic: snapshot.coverage?.dialogue?.target_topic || "check_in",
    safety: snapshot.safety?.level || "none",
    completion: Number(snapshot.coverage?.completion_ratio || 0),
    summary: payload.summary || buildPatientSummary(snapshot.coverage?.dialogue || { stage: "rapport", target_topic: "mood" }, snapshot.safety || { level: "none" }),
  };

  state.recentCheckins = [entry, ...state.recentCheckins.filter((item) => item.sessionId !== entry.sessionId)].slice(0, 6);
  saveRecentCheckins();
  renderHistory();
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

function buildClientExportPayload(payload) {
  if (!payload?.snapshot) {
    return null;
  }
  return {
    __partial: true,
    session_id: state.sessionId,
    language: state.language,
    summary: payload.summary || "",
    snapshot: payload.snapshot,
    rows: payload.rows || [],
  };
}

function runtimeToText(payload) {
  if (payload.hybrid_safety_enabled) {
    if (payload.cloud_voice_enabled) {
      return "Voice, multilingual support, and quiet safety checks are ready.";
    }
    return "Multilingual conversation and quiet safety checks are ready.";
  }
  if (payload.cloud_voice_enabled) {
    return "Voice and multilingual conversation are ready.";
  }
  return "Conversation service is ready.";
}

function runtimeToDetail(payload) {
  const safetyMode = payload.hybrid_safety_enabled
    ? "local hybrid safety enabled"
    : payload.semantic_safety_enabled
      ? "semantic safety enabled"
      : "rule + HF safety enabled";
  const voiceMode = payload.cloud_voice_enabled ? "cloud STT/TTS enabled" : "browser voice wrapper";
  const providerLabel = payload.self_hosted_inference_enabled ? "self-hosted local runtime" : `${payload.provider} runtime`;
  return `${providerLabel} · chat ${payload.chat_model} · extraction ${payload.extraction_model} · ${safetyMode} · ${voiceMode}`;
}

function renderRuntime(payload) {
  state.runtime = payload;
  runtimeInfo.textContent = runtimeToText(payload);
  if (runtimeDetail) {
    runtimeDetail.textContent = runtimeToDetail(payload);
  }
  if (payload.cloud_voice_enabled) {
    updateVoiceStatus("Cloud voice is ready when microphone access is allowed.");
  } else if (SpeechRecognitionCtor) {
    updateVoiceStatus("Browser voice is ready when microphone access is allowed.");
  } else {
    updateVoiceStatus("Voice is available by typing in this browser right now.");
  }
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
      <p class="profile-title">${escapeHtml((profile.language || "en").toUpperCase())} scenario · ${escapeHtml(profile.patient_id)}</p>
      <p class="profile-meta">${escapeHtml(profile.occupation || "participant")} · age ${escapeHtml(String(profile.age || "n/a"))}</p>
      <p class="profile-context">${escapeHtml(profile.context || profile.notes || "No context available.")}</p>
      <p class="profile-tags">${escapeHtml(tags || "guided conversation demo")}</p>
      <button type="button" class="button secondary profile-launch" data-profile-id="${escapeHtml(profile.patient_id)}">Load scenario</button>
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
    serviceHealth.textContent = payload.health.status === "ok"
      ? "Ready"
      : "Waking up";
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
  serviceHealth.textContent = healthPayload.status === "ok"
    ? "Ready"
    : "Waking up";
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
  syncLanguageTabs(language);
  renderStarterDeck(language);
}

async function requestSessionStart(options = {}) {
  const {
    resetChat = true,
    renderOpening = true,
    announce = true,
    speakOpening = true,
    stopVoiceCapture = true,
  } = options;

  state.language = languageSelect.value;
  applyLanguageDefaults(state.language);
  if (stopVoiceCapture) {
    stopListening();
  }
  setVoicePreview("", { visible: false });

  const response = await fetch("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: state.language, profile: collectProfileContext() }),
  });
  if (!response.ok) {
    throw new Error(`Could not start session (${response.status})`);
  }

  const payload = await response.json();
  state.sessionId = payload.session_id;
  state.exportPayload = null;
  state.pendingNudge = null;
  if (resetChat) {
    chatLog.innerHTML = "";
  }
  if (renderOpening) {
    renderTurn(payload.assistant_turn);
  }

  state.voiceLoopArmed = handsFreeVoiceEnabled();
  if (renderOpening && speakOpening) {
    maybeSpeak(payload.assistant_turn);
  } else if (state.voiceLoopArmed) {
    maybeResumeVoiceLoop();
  }

  sessionMeta.classList.remove("empty");
  sessionMeta.textContent = "Your private check-in is open. Start with whatever feels most real right now.";
  updateSessionBadge();
  setSessionLiveState(true);
  downloadButton.disabled = false;
  setLink(summaryLink, `/chat/sessions/${payload.session_id}/summary`);
  setLink(exportLink, `/chat/sessions/${payload.session_id}/export`);

  if (announce) {
    resetInsightPanel();
    setDisclosureState(demoPanel, demoToggle, false, {
      open: "Show demo scenarios",
      close: "Hide demo scenarios",
    });
    setDisclosureState(insightPanel, insightsToggle, false, {
      open: "Show care details",
      close: "Hide care details",
    });
    updateVoiceStatus(LANGUAGE_UI[state.language].sessionReady);
    setStatusBanner(LANGUAGE_UI[state.language].startSuccess, "success");
  }

  return payload;
}

async function startSession() {
  setBusy(true);
  try {
    await requestSessionStart();
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
  const emptyCard = chatLog.querySelector(".empty-chat-card");
  if (emptyCard) {
    emptyCard.remove();
  }
  const card = document.createElement("article");
  const isSystem = String(turn.text || "").startsWith("[System]");
  const speakerLabel = isSystem
    ? "System"
    : turn.speaker === "assistant"
      ? "ManoVarta"
      : "You";
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
    return "Pause the normal flow and make space for immediate human support.";
  }
  if (dialogue.stage === "rapport") {
    return "Stay gentle, understand the main concern, and keep the conversation low-pressure.";
  }
  if (dialogue.stage === "clarification") {
    return "Clarify one missing detail so ManoVarta does not rush into assumptions.";
  }
  if (dialogue.stage === "safety") {
    return "Slow down and check safety carefully before moving on.";
  }
  if (dialogue.stage === "summary") {
    return "The picture is becoming steady enough to end with a clear summary.";
  }
  return "Understand the pattern, impact, and intensity of what you are feeling.";
}

function buildProgressLabel(coverage) {
  const remaining = Math.max((coverage.total_items || 0) - (coverage.touched_items || 0), 0);
  return `${coverage.touched_items} of ${coverage.total_items} areas have some clarity so far, with ${remaining} still open.`;
}

function buildBonusSignals(dialogue, coverage) {
  const completion = Math.round((coverage.completion_ratio || 0) * 100);
  const posture = buildResponsePosture(dialogue.user_style);
  return [
    `${completion}% covered`,
    `${humanizeToken(dialogue.target_topic)} focus`,
    posture,
    dialogue.fatigue === "high" ? "Low-burden follow-up" : dialogue.next_action === "risk_check" ? "Safety pause" : "Guided follow-up",
  ];
}

function buildResponsePosture(userStyle) {
  if (userStyle.openness === "guarded") {
    return "Low-pressure pacing";
  }
  if (userStyle.verbosity === "brief") {
    return "Short focused prompts";
  }
  if (userStyle.verbosity === "detailed") {
    return "Narrative-friendly flow";
  }
  return "Balanced guided pace";
}

function resolveUiLanguage(language) {
  return language || state.language || "en";
}

function buildPersonalizationSummary(dialogue, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    return "मनोवार्ता आपके जवाब की लंबाई, खुलापन और भाषा के ढंग को देखकर अगला सवाल बदल रही है। यह किसी तय स्क्रिप्ट पर नहीं चल रही।";
  }
  const { verbosity, openness, code_mix: codeMix, distress_trend: distressTrend, steering_preference: steeringPreference } = dialogue.user_style;
  return `ManoVarta is adapting to ${verbosity} responses, ${openness} disclosure, ${codeMix} code-mix, and a ${distressTrend} pattern. Right now it is using a ${steeringPreference} steering style instead of a fixed script.`;
}

function buildComposerHelper(dialogue, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (dialogue.next_action === "risk_check") {
      return "यहाँ छोटा और सीधा जवाब भी काफ़ी है। मनोवार्ता सामान्य प्रवाह पर लौटने से पहले सावधानी से सुरक्षा-जाँच कर रही है।";
    }
    if (dialogue.fatigue === "high") {
      return "अभी गति हल्की रखी जा रही है। एक छोटा सा ठोस विवरण भी काफ़ी है।";
    }
    if (dialogue.readiness === "ready_to_close") {
      return "तस्वीर अब काफ़ी साफ़ हो रही है। पुनरावलोकन से पहले बस एक आख़िरी स्पष्टता काफ़ी हो सकती है।";
    }
    if (dialogue.user_style.openness === "guarded") {
      return "हल्का मोड चालू है: एक हाल का उदाहरण या रोज़मर्रा पर एक असर बताना भी काफ़ी है।";
    }
    if (dialogue.user_style.verbosity === "brief") {
      return "छोटे जवाब भी ठीक हैं। एक उदाहरण या समय का एक संकेत बहुत मदद करेगा।";
    }
    if (dialogue.user_style.verbosity === "detailed") {
      return "वर्णनात्मक मोड चालू है: जो हिस्सा सबसे ज़रूरी लग रहा है, उसी पर टिकिए। मनोवार्ता पीछे से उसे शांति से व्यवस्थित करेगी।";
    }
    return "मनोवार्ता आपके दिए गए विवरण के हिसाब से अगला सवाल बदल रही है और वही अगला हिस्सा पूछ रही है जो सबसे ज़्यादा स्पष्टता देगा।";
  }
  if (dialogue.next_action === "risk_check") {
    return "A short direct answer is enough here. ManoVarta is doing a careful safety check before returning to the normal flow.";
  }
  if (dialogue.fatigue === "high") {
    return "The pace is being kept light right now. One short concrete detail is enough.";
  }
  if (dialogue.readiness === "ready_to_close") {
    return "The picture is getting steady. One final clarification may be enough before the recap.";
  }
  if (dialogue.user_style.openness === "guarded") {
    return "Low-pressure mode is active: one recent example or one daily-life impact is enough.";
  }
  if (dialogue.user_style.verbosity === "brief") {
    return "Brief responses are okay. One example or one timing detail will help a lot.";
  }
  if (dialogue.user_style.verbosity === "detailed") {
    return "Narrative mode is active: stay with the part that feels most important and ManoVarta will organize it quietly in the background.";
  }
  return "ManoVarta is adapting to how much detail you are giving and asking for the next piece that adds real clarity.";
}

function buildNudgeSubtitle(dialogue, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (dialogue.next_action === "risk_check") {
      return "यह एक संवेदनशील जाँच है: छोटा और सीधा जवाब भी काफ़ी है। आपको लंबा पैराग्राफ़ लिखने की ज़रूरत नहीं है।";
    }
    if ((dialogue.disclosure?.nudge_effectiveness || 0) < 0) {
      return "पिछले संकेत से ज़्यादा विवरण नहीं खुला, इसलिए ये संकेत अब थोड़ा अलग रास्ता सुझा रहे हैं।";
    }
    if (dialogue.user_style.openness === "guarded") {
      return "जो संकेत सबसे आसान लगे, वही चुनिए। मनोवार्ता उसी छोटे विवरण से दबाव कम रखेगी और आगे बढ़ेगी।";
    }
    if (dialogue.user_style.verbosity === "brief") {
      return "बस एक अतिरिक्त ठोस विवरण सत्र को अस्पष्ट संकेत से स्थिर प्रमाण तक ले जा सकता है।";
    }
      return "ये संकेत कम संदेशों में ज़्यादा मज़बूत प्रमाण इकट्ठा करने में मदद करते हैं।";
  }
  if (dialogue.next_action === "risk_check") {
    return "Sensitive checkpoint: a short direct answer is enough. You do not need to write a long paragraph.";
  }
  if ((dialogue.disclosure?.nudge_effectiveness || 0) < 0) {
    return "The last prompt did not unlock much detail, so these nudges shift strategy and try a different angle.";
  }
  if (dialogue.user_style.openness === "guarded") {
    return "Pick the easiest nudge. ManoVarta will use that small detail to reduce pressure and keep moving.";
  }
  if (dialogue.user_style.verbosity === "brief") {
    return "One extra concrete detail can move the session from vague signal to stable evidence.";
  }
  return "These nudges help the system collect stronger evidence with fewer turns.";
}

function buildNudgeMeta(dialogue, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (dialogue.next_action === "risk_check") {
      return "हल्का संकेत";
    }
    if ((dialogue.disclosure?.nudge_effectiveness || 0) > 0.2) {
      return "पिछली बार उपयोगी";
    }
    if (dialogue.user_style.openness === "guarded" || dialogue.user_style.verbosity === "brief") {
      return "जल्दी स्पष्टता";
    }
    if (dialogue.user_style.verbosity === "detailed") {
      return "विवरण को बढ़ाने वाला संकेत";
    }
    return "प्रमाण मज़बूत करने वाला संकेत";
  }
  if (dialogue.next_action === "risk_check") {
    return "Low-pressure prompt";
  }
  if ((dialogue.disclosure?.nudge_effectiveness || 0) > 0.2) {
    return "Helpful last time";
  }
  if (dialogue.user_style.openness === "guarded" || dialogue.user_style.verbosity === "brief") {
    return "Fast confidence unlock";
  }
  if (dialogue.user_style.verbosity === "detailed") {
    return "Narrative booster";
  }
  return "Evidence booster";
}

function buildSessionMetaLine(dialogue, coverage, safety, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (safety.level === "none") {
      return "अभी मनोवार्ता इसी हिस्से को थोड़ा और साफ़ कर रही है, जबकि सुरक्षा-जाँच पृष्ठभूमि में शांत रूप से चल रही है।";
    }
    return "अभी मनोवार्ता बातचीत को इसी हिस्से पर टिकाए हुए है, और सुरक्षा पर थोड़ा ज़्यादा ध्यान रखा जा रहा है।";
  }
  const topic = humanizeToken(dialogue.target_topic);
  const safetyLine = safety.level === "none" ? "safety monitoring stays in the background" : `${humanizeToken(safety.level)} safety care is active`;
  return `Right now ManoVarta is staying with ${topic.toLowerCase()}, while ${safetyLine}.`;
}

function buildPatientSummary(dialogue, safety, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (safety.level === "urgent") {
      return "मनोवार्ता ने कुछ ऐसा सुना है जिसके लिए तुरंत मानवीय मदद ज़रूरी हो सकती है, इसलिए यह सामान्य जाँच-प्रवाह से हट रही है।";
    }
    if (safety.level === "review") {
      return "कुछ संवेदनशील बात सामने आई है, इसलिए बातचीत अब थोड़ी ज़्यादा सावधानी से आगे बढ़ रही है।";
    }
    if (dialogue.stage === "rapport") {
      return "बातचीत अभी दिशा पकड़ रही है। मनोवार्ता समझ रही है कि अभी सबसे ज़्यादा दबाव किस हिस्से से आ रहा है।";
    }
    if (dialogue.stage === "clarification") {
      return "उपयोगी जानकारी मिल चुकी है, लेकिन आगे बढ़ने से पहले एक बात और साफ़ करनी है।";
    }
    if (dialogue.stage === "summary") {
      return "अब तस्वीर काफ़ी साफ़ हो रही है। मनोवार्ता एक स्थिर सार के काफ़ी पास है।";
    }
    return "अभी मनोवार्ता इस हिस्से को समझ रही है और देख रही है कि इसका रोज़मर्रा की ज़िंदगी पर क्या असर पड़ रहा है।";
  }
  const topic = humanizeToken(dialogue.target_topic).toLowerCase();
  if (safety.level === "urgent") {
    return "ManoVarta heard something that may need immediate human support, so it is shifting away from normal screening.";
  }
  if (safety.level === "review") {
    return "Something sensitive has come up, so the conversation is becoming more careful while safety stays in view.";
  }
  if (dialogue.stage === "rapport") {
    return `The conversation is still getting oriented. Right now ManoVarta is trying to understand whether ${topic} is the biggest source of strain.`;
  }
  if (dialogue.stage === "clarification") {
    return `There is already useful context, but ManoVarta still needs one clearer detail about ${topic} before moving on.`;
  }
  if (dialogue.stage === "summary") {
    return "The overall picture is getting clearer. ManoVarta is close to having enough information for a stable structured summary.";
  }
  return `Right now ManoVarta is exploring ${topic} and how it is affecting day-to-day life.`;
}

function buildWhyThisQuestion(dialogue, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  const itemReasonMap = uiLanguage === "hi"
    ? {
        phq_q3_sleep: "अगला सवाल यह साफ़ कर रहा है कि नींद की दिक्कत किस तरह की है, ताकि मनोवार्ता सिर्फ़ समय सुनकर अनुमान न लगा ले।",
        gad_q2_control_worry: "अगला सवाल यह समझ रहा है कि चिंता पर काबू पाना मुश्किल है या नहीं, सिर्फ़ यह नहीं कि चिंता मौजूद है।",
        gad_q4_trouble_relaxing: "अगला सवाल यह देख रहा है कि यह ज़्यादा व्यस्त दिमाग है, तना हुआ शरीर है, या दोनों, ताकि अगला सवाल सटीक रहे।",
        gad_q5_restlessness: "अगला सवाल यह समझ रहा है कि बेचैनी किस तरह सामने आती है, सिर्फ़ यह नहीं कि कब होती है।",
      }
    : {
        phq_q3_sleep: "The next question is checking what kind of sleep disruption this is, so ManoVarta does not confuse timing with the sleep problem itself.",
        gad_q2_control_worry: "The next question is checking whether the worry is hard to control, not just whether it is present.",
        gad_q4_trouble_relaxing: "The next question is checking whether this is a busy mind, a tense body, or both, so the follow-up stays precise.",
        gad_q5_restlessness: "The next question is checking how the restlessness shows up, not just when it happens, so ManoVarta does not keep circling the same point.",
      };
  if (uiLanguage === "hi") {
    if (dialogue.next_action === "risk_check") {
      return "यह सवाल पहले इसलिए पूछा जा रहा है क्योंकि सुरक्षा, जाँच जल्दी पूरी करने से ज़्यादा महत्वपूर्ण है।";
    }
    if (dialogue.target_item && itemReasonMap[dialogue.target_item]) {
      return itemReasonMap[dialogue.target_item];
    }
    if (dialogue.stage === "clarification") {
      return "यह सवाल एक छूटी हुई बात साफ़ करने के लिए है, ताकि मनोवार्ता अनुमान लगाने के बजाय स्पष्ट समझ बना सके।";
    }
    if (dialogue.user_style.openness === "guarded") {
      return "अगला सवाल जानबूझकर छोटा और हल्का रखा गया है, ताकि जवाब देना आसान रहे।";
    }
    return "अगला सवाल उसी हिस्से पर है जहाँ बातचीत को अभी सबसे मज़बूत प्रमाण की ज़रूरत है।";
  }
  if (dialogue.next_action === "risk_check") {
    return "This question comes first because safety matters more than finishing the screening quickly.";
  }
  if (dialogue.target_item && itemReasonMap[dialogue.target_item]) {
    return itemReasonMap[dialogue.target_item];
  }
  if (dialogue.stage === "clarification") {
    return `The assistant is checking one missing detail so it does not guess about ${humanizeToken(dialogue.target_topic).toLowerCase()}.`;
  }
  if (dialogue.user_style.openness === "guarded") {
    return "The next question is intentionally smaller and gentler so it is easier to answer.";
  }
  return `The next question is about ${humanizeToken(dialogue.target_topic).toLowerCase()} because that is where the conversation still needs the strongest evidence.`;
}

function buildSafetyNarrative(safety, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  if (uiLanguage === "hi") {
    if (safety.level === "urgent") {
      return "अभी सुरक्षा-सहायता को सबसे ऊपर रखा जा रहा है।";
    }
    if (safety.level === "review") {
      return "एक संवेदनशील संकेत दिखा है, इसलिए मनोवार्ता अब थोड़ा और सावधानी से आगे बढ़ रही है।";
    }
    return "पूरी बातचीत के दौरान सुरक्षा-जाँच शांत रूप से पृष्ठभूमि में चलती रहती है।";
  }
  if (safety.level === "urgent") {
    return "Safety support is being prioritized right now.";
  }
  if (safety.level === "review") {
    return "A sensitive signal has been noticed, so ManoVarta is moving more carefully.";
  }
  return "Safety checks are running quietly in the background throughout the conversation.";
}

function buildReflectionPrompt(snapshot, summary, language = state.language) {
  const uiLanguage = resolveUiLanguage(language);
  const safety = snapshot?.safety?.level || "none";
  const completion = Number(snapshot?.coverage?.completion_ratio || 0);
  if (uiLanguage === "hi") {
    if (safety === "urgent") {
      return "इस बातचीत में कुछ ऐसा सामने आया है जिस पर तुरंत मानवीय मदद ज़रूरी हो सकती है। अभी सामान्य जाँच रोककर तुरंत सहायता लें।";
    }
    if (safety === "review") {
      return "इस सत्र में कुछ संवेदनशील बात सामने आई है। चाहें तो यहीं रुकें, छोटा जवाब दें, या किसी भरोसेमंद सहारे के साथ फिर लौटें।";
    }
    if (completion >= 0.7) {
      return "मनोवार्ता के पास अब काफ़ी साफ़ तस्वीर है। आप चाहें तो यहीं रुक सकते हैं या बाद में लौट सकते हैं।";
    }
    return "यदि अभी के लिए इतना काफ़ी लगे तो आप यहीं रुक सकते हैं, या तस्वीर को थोड़ा और साफ़ करने के लिए एक और सवाल ले सकते हैं।";
  }
  if (safety === "urgent") {
    return "This check-in surfaced something urgent. Pause the screening flow and reach for immediate human support now.";
  }
  if (safety === "review") {
    return "This session touched something sensitive. It is okay to pause here, keep the answer short, or come back with support nearby.";
  }
  if (completion >= 0.7) {
    return `${summary || "ManoVarta has enough to hold a clearer picture now."} You can stop here or return later if anything shifts.`;
  }
  return "You can stop here if this already feels like enough, or answer one more question to make the picture clearer.";
}

function pickNudges(language, dialogue) {
  const bank = NUDGE_LIBRARY[language] || NUDGE_LIBRARY.en;
  const nudges = [];
  const add = (key) => {
    const entry = bank[key];
    if (entry && !nudges.some((nudge) => nudge.key === key)) {
      nudges.push({ key, ...entry });
    }
  };

  (dialogue.recommended_nudges || []).forEach(add);

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
  const payload = typeof text === "string" ? { text, key: null, title: null } : text;
  state.pendingNudge = payload.key
    ? { id: payload.key, strategy: payload.key, title: payload.title || payload.key }
    : null;
  const current = messageInput.value.trim();
  messageInput.value = current ? `${current} ${payload.text}` : payload.text;
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
      <span class="nudge-meta">${escapeHtml(buildNudgeMeta(dialogue, language))}</span>
      <strong>${escapeHtml(nudge.title)}</strong>
      <span>${escapeHtml(nudge.description)}</span>
    `;
    button.addEventListener("click", () => applyNudge(nudge));
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
    user_style: { verbosity: "balanced", openness: "cautious", distress_trend: "unclear", code_mix: "low", steering_preference: "balanced" },
    disclosure: { items_per_user_turn: 0, resolved_per_user_turn: 0 },
    user_turns: 0,
    readiness: "opening",
    fatigue: "low",
    recommended_nudges: [],
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
  snapshotMode.textContent = humanizeToken(snapshot.mode);
  if (detailModeLabel) {
    detailModeLabel.textContent = humanizeToken(snapshot.mode);
  }
  summaryText.textContent = summary;
  patientSummary.textContent = buildPatientSummary(dialogue, snapshot.safety, snapshot.language);
  whyThisQuestion.textContent = buildWhyThisQuestion(dialogue, snapshot.language);
  safetyNarrative.textContent = buildSafetyNarrative(snapshot.safety, snapshot.language);
  if (reflectionPrompt) {
    reflectionPrompt.textContent = buildReflectionPrompt(snapshot, summary, snapshot.language);
  }

  const completion = Math.round((coverage.completion_ratio || 0) * 100);
  coverageText.textContent = `${coverage.touched_items}/${coverage.total_items} explored`;
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
  sessionMeta.textContent = buildSessionMetaLine(dialogue, coverage, snapshot.safety, snapshot.language);

  bonusSignals.innerHTML = "";
  buildBonusSignals(dialogue, coverage).forEach((signal) => {
    const chip = document.createElement("span");
    chip.className = "signal-pill";
    chip.textContent = signal;
    bonusSignals.appendChild(chip);
  });

  personalizationBlend.textContent = `${dialogue.user_style.code_mix} code-mix`;
  personalizationPacing.textContent = buildResponsePosture(dialogue.user_style);
  personalizationSummary.textContent = buildPersonalizationSummary(dialogue, snapshot.language);
  composerHelper.textContent = buildComposerHelper(dialogue, snapshot.language);
  nudgeSubtitle.textContent = buildNudgeSubtitle(dialogue, snapshot.language);
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
  const hindi = state.language === "hi";
  phqTotal.textContent = "0";
  gadTotal.textContent = "0";
  safetyLevel.textContent = "none";
  safetyLevel.className = "metric-value small none";
  snapshotMode.textContent = "Heuristic";
  if (detailModeLabel) {
    detailModeLabel.textContent = "Guided conversation";
  }
  coverageText.textContent = "Just getting started";
  progressMeterFill.style.width = "0%";
  progressMeterLabel.textContent = "Nothing explored yet";
  plannerStage.textContent = "rapport";
  plannerStage.className = "chip soft";
  plannerAction.textContent = "Open Question";
  plannerTopic.textContent = "Mood";
  plannerStyle.textContent = "balanced · cautious";
  plannerTrend.textContent = "Unclear";
  plannerEfficiency.textContent = "0.00 items/turn";
  plannerHeldBack.textContent = "none";
  plannerTransition.textContent = hindi
    ? "बातचीत शुरू होने पर यहाँ दिखेगा कि अगला विषय कैसे चुना जा रहा है।"
    : "Start a conversation to see how the next topic is selected.";
  summaryText.textContent = hindi
    ? "बातचीत शुरू होने पर यहाँ पहला सार दिखाई देगा।"
    : "Start a conversation to generate the first summary.";
  patientSummary.textContent = hindi
    ? "बातचीत शुरू होने पर यहाँ एक सरल सार दिखाई देगा।"
    : "Start a conversation to see a gentle plain-language summary here.";
  whyThisQuestion.textContent = hindi
    ? "बातचीत शुरू होने पर यहाँ दिखेगा कि अगला सवाल क्यों पूछा जा रहा है।"
    : "Start a conversation to see why the next question is being asked.";
  safetyNarrative.textContent = hindi
    ? "पूरी बातचीत के दौरान सुरक्षा-जाँच शांत रूप से पृष्ठभूमि में चलती रहती है।"
    : "Safety checks are running quietly in the background throughout the conversation.";
  sessionGoal.textContent = hindi
    ? "पहले सहजता बनाइए, फिर मुख्य चिंता को साफ़ समझिए।"
    : "Build comfort first, then understand the main concern clearly.";
  topicMap.innerHTML = '<span class="topic-pill">No topic map yet.</span>';
  unresolvedCount.textContent = "0 queued";
  reviewCount.textContent = "0 flagged";
    unresolvedList.innerHTML = hindi ? "<li>अभी कोई अगला लंबित सवाल नहीं है।</li>" : "<li>No follow-up queue yet.</li>";
    reviewList.innerHTML = hindi ? "<li>अभी कोई समीक्षा संकेत नहीं है।</li>" : "<li>No review flags right now.</li>";
  itemTableBody.innerHTML = hindi
      ? '<tr><td colspan="4" class="empty-cell">अभी किसी बिंदु का अंकन उपलब्ध नहीं है।</td></tr>'
    : '<tr><td colspan="4" class="empty-cell">No item scores yet.</td></tr>';
  evidenceList.innerHTML = hindi
      ? '<li class="empty-cell">अभी कोई प्रमाण अंश उपलब्ध नहीं है।</li>'
    : '<li class="empty-cell">No evidence spans yet.</li>';
  bonusSignals.innerHTML = `
    <span class="signal-pill">Gentle pacing</span>
    <span class="signal-pill">Voice available</span>
    <span class="signal-pill">Safety checks on</span>
  `;
  personalizationBlend.textContent = "low code-mix";
  personalizationPacing.textContent = "Balanced guided pacing";
  personalizationSummary.textContent = hindi
      ? "सत्र शुरू होने पर यहाँ दिखेगा कि मनोवार्ता अपनी गति, मार्गदर्शन-शैली और अगली पूछताछ का दबाव कैसे बदलती है।"
    : "Start a session to see how ManoVarta adapts its pacing, steering style, and follow-up burden.";
  if (reflectionPrompt) {
    reflectionPrompt.textContent = hindi
      ? "जब बातचीत थोड़ा स्थिर होगी, मनोवार्ता यहाँ एक सरल पुनरावलोकन छोड़ेगी ताकि आपको पता रहे कि वह क्या संभाल रही है।"
      : "Once the conversation starts settling, ManoVarta will leave a simple recap here so you know what it is holding onto.";
  }
  renderNudges(state.language, {
    target_topic: "mood",
    next_action: "open_question",
    user_style: { verbosity: "balanced", openness: "cautious", code_mix: "low", steering_preference: "balanced" },
    disclosure: { nudge_effectiveness: 0 },
    recommended_nudges: [],
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
  rememberCheckin(state.exportPayload);
  setLink(summaryLink, `/chat/sessions/${state.sessionId}/summary`);
  setLink(exportLink, `/chat/sessions/${state.sessionId}/export`);
}

async function sendMessageText(text, options = {}) {
  const { fromVoice = false, allowRecovery = true } = options;
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
    setVoicePreview("", { visible: false });
    state.voiceLoopArmed = fromVoice && handsFreeVoiceEnabled();
    if (speechSynthesisApi) {
      speechSynthesisApi.cancel();
    }
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    renderTurn({ speaker: "user", text: cleaned });
    messageInput.value = "";
    const pendingNudge = state.pendingNudge;
    state.pendingNudge = null;

    let response = await fetch(`/chat/sessions/${state.sessionId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: cleaned,
        from_voice: fromVoice,
        nudge_id: pendingNudge?.id || null,
        nudge_strategy: pendingNudge?.strategy || null,
        nudge_title: pendingNudge?.title || null,
      }),
    });
    if (response.status === 404 && allowRecovery) {
      setStatusBanner("The session refreshed in the background. Sending your last message again...", "info");
      await requestSessionStart({
        resetChat: false,
        renderOpening: false,
        announce: false,
        speakOpening: false,
        stopVoiceCapture: false,
      });
      response = await fetch(`/chat/sessions/${state.sessionId}/turns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: cleaned,
          from_voice: fromVoice,
          nudge_id: pendingNudge?.id || null,
          nudge_strategy: pendingNudge?.strategy || null,
          nudge_title: pendingNudge?.title || null,
        }),
      });
    }
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Turn failed (${response.status}): ${detail}`);
    }
    const payload = await response.json();
    renderTurn(payload.assistant_turn);
    state.exportPayload = buildClientExportPayload(payload);
    if (payload.snapshot && payload.summary) {
      renderSnapshot({
        snapshot: payload.snapshot,
        summary: payload.summary,
        rows: payload.rows || [],
      });
      rememberCheckin(state.exportPayload);
    }
    maybeSpeak(payload.assistant_turn);
    setStatusBanner(LANGUAGE_UI[state.language].turnSuccess, "success");
  } catch (error) {
    console.error(error);
    renderSystemMessage("Turn failed due to a runtime error. Please retry.");
    setStatusBanner("Turn failed. Check runtime and retry.", "error");
    state.voiceLoopArmed = false;
  } finally {
    setBusy(false);
  }
}

async function sendTurn(event) {
  event.preventDefault();
  await sendMessageText(messageInput.value, { fromVoice: false });
}

async function downloadExport() {
  if ((!state.exportPayload || state.exportPayload.__partial) && state.sessionId) {
    try {
      await refreshExport();
    } catch (error) {
      console.error(error);
      setStatusBanner("Could not prepare the export right now. Please retry.", "error");
      return;
    }
  }
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

function backendVoiceAvailable() {
  return Boolean(state.runtime?.speech_to_text_enabled || state.runtime?.cloud_voice_enabled);
}

function browserVoiceAvailable() {
  return Boolean(recognition);
}

function shouldPreferBrowserVoice() {
  return browserVoiceAvailable();
}

function startBrowserVoiceCapture(statusMessage = "Requesting microphone access...") {
  if (!recognition) {
    updateVoiceStatus("Browser voice is not available here.", true);
    return false;
  }
  try {
    recognition.lang = mapVoiceLanguage(languageSelect.value);
    setVoicePreview("", { visible: false });
    updateVoiceStatus(statusMessage);
    recognition.start();
    return true;
  } catch (error) {
    console.error(error);
    updateVoiceStatus("Microphone could not start. Please check browser mic permission and try again.", true);
    return false;
  }
}

function updateMicButtonLabel() {
  if (!micButton) {
    return;
  }
  if (listening) {
    micButton.textContent = "Stop";
    return;
  }
  micButton.textContent = autoSendToggle?.checked ? "Speak and auto-send" : "Tap to talk";
}

function assistantAudioActive() {
  return Boolean(currentAudio || (speechSynthesisApi && (speechSynthesisApi.speaking || speechSynthesisApi.pending)));
}

function maybeResumeVoiceLoop() {
  if (!state.voiceLoopArmed || !handsFreeVoiceEnabled() || state.isBusy || assistantAudioActive()) {
    return;
  }
  window.setTimeout(() => {
    if (!state.voiceLoopArmed || !handsFreeVoiceEnabled() || state.isBusy || listening || assistantAudioActive()) {
      return;
    }
    if (shouldPreferBrowserVoice()) {
      startBrowserVoiceCapture("Your turn. Speak when ready.");
      return;
    }
    if (backendVoiceAvailable()) {
      updateVoiceStatus("Your turn. Recording will start now.");
      startBackendRecording().catch((error) => {
        console.error(error);
        if (recognition) {
          startBrowserVoiceCapture("Your turn. Switching to browser voice...");
          return;
        }
        updateVoiceStatus("Voice conversation could not restart. Tap the mic to continue.", true);
      });
    }
  }, 450);
}

function cleanupMediaStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  mediaRecorder = null;
}

function handleCapturedTranscript(transcript, sourceLabel = "voice") {
  const cleaned = (transcript || "").trim();
  if (!cleaned) {
    updateVoiceStatus("I could not hear enough to transcribe. Please try again.", true);
    setVoicePreview("", { visible: false });
    return;
  }
  messageInput.value = cleaned;
  setVoicePreview(cleaned, { visible: true });
  updateVoiceStatus(`Transcript captured from ${sourceLabel}.`);
  if (autoSendToggle.checked) {
    void sendMessageText(cleaned, { fromVoice: true });
  }
}

async function startBackendRecording() {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    throw new Error("Voice recording is not available in this browser.");
  }

  const mimeType = detectRecordingMimeType();
  if (!mimeType) {
    throw new Error("No supported recording format is available in this browser.");
  }

  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
  recordedChunks = [];
  mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };
  mediaRecorder.onstop = async () => {
    listening = false;
    updateMicButtonLabel();
    updateVoiceStatus("Transcribing your voice...");
    const blob = new Blob(recordedChunks, { type: mimeType || "audio/webm" });
    recordedChunks = [];
    cleanupMediaStream();
    try {
      const formData = new FormData();
      const extension = mimeType.includes("ogg") ? "ogg" : mimeType.includes("wav") ? "wav" : "webm";
      formData.append("audio", blob, `voice.${extension}`);
      const response = await fetch(`/voice/transcribe?language=${encodeURIComponent(state.language)}`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Voice transcription failed (${response.status})`);
      }
      const payload = await response.json();
      handleCapturedTranscript(payload.transcript || "", "cloud voice");
    } catch (error) {
      console.error(error);
      if (recognition) {
        updateVoiceStatus("Cloud transcription struggled. Try speaking once more and I’ll capture it live in the browser.");
        return;
      }
      updateVoiceStatus("Voice transcription failed. Please try typing instead.", true);
    }
  };
  mediaRecorder.start();
  listening = true;
  updateMicButtonLabel();
  updateVoiceStatus("Recording for cloud transcription...", false, true);
}

function stopBackendRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

function setupVoice() {
  if (SpeechRecognitionCtor) {
    recognition = new SpeechRecognitionCtor();
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.lang = mapVoiceLanguage(languageSelect.value);

    recognition.onstart = () => {
      listening = true;
      updateMicButtonLabel();
      setVoicePreview("", { visible: false });
      updateVoiceStatus("Listening now. Tap stop when you are done.", false, true);
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      if (!transcript) {
        return;
      }
      const finalResult = event.results[event.results.length - 1];
      if (finalResult?.isFinal) {
        handleCapturedTranscript(transcript, "browser voice");
      } else {
        setVoicePreview(transcript, { visible: true });
      }
    };

    recognition.onerror = (event) => {
      listening = false;
      updateMicButtonLabel();
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        state.voiceLoopArmed = false;
        updateVoiceStatus("Microphone access is blocked. Allow mic access in the browser and try again.", true);
        return;
      }
      if (event.error === "no-speech") {
        if (handsFreeVoiceEnabled() && state.voiceLoopArmed) {
          updateVoiceStatus("I did not catch speech that time. Listening again...");
          maybeResumeVoiceLoop();
          return;
        }
        updateVoiceStatus("I did not catch speech that time. Try once more.", true);
        return;
      }
      updateVoiceStatus(`Voice error: ${event.error}`, true);
    };

    recognition.onend = () => {
      listening = false;
      updateMicButtonLabel();
      if (handsFreeVoiceEnabled() && state.voiceLoopArmed && !state.isBusy && !pendingVoiceTranscript) {
        maybeResumeVoiceLoop();
        return;
      }
      if (!voiceStatus.classList.contains("error")) {
        updateVoiceStatus("Voice ready.");
      }
    };
  }

  micButton.addEventListener("click", toggleListening);
  voiceUseButton?.addEventListener("click", () => {
    if (!pendingVoiceTranscript) {
      return;
    }
    messageInput.value = pendingVoiceTranscript;
    if (autoSendToggle.checked) {
      void sendMessageText(pendingVoiceTranscript, { fromVoice: true });
    } else {
      messageInput.focus();
      updateVoiceStatus("Transcript moved into the message box.");
    }
  });
  autoSendToggle?.addEventListener("change", () => {
    if (autoSendToggle.checked && speakToggle && !speakToggle.checked) {
      speakToggle.checked = true;
    }
    if (!autoSendToggle.checked) {
      state.voiceLoopArmed = false;
    } else if (state.sessionId) {
      state.voiceLoopArmed = true;
    }
    updateMicButtonLabel();
    setVoicePreview(pendingVoiceTranscript, { visible: Boolean(pendingVoiceTranscript) });
    updateVoiceStatus(
      autoSendToggle.checked
        ? "Continuous voice is on. Speak, pause, and ManoVarta will answer aloud."
        : "Continuous voice is off. You can review the transcript before sending."
    );
    if (autoSendToggle.checked && state.sessionId) {
      maybeResumeVoiceLoop();
    }
  });
  speakToggle?.addEventListener("change", () => {
    if (!speakToggle.checked) {
      state.voiceLoopArmed = false;
      if (autoSendToggle?.checked) {
        autoSendToggle.checked = false;
      }
    }
  });
  languageSelect.addEventListener("change", () => {
    if (recognition) {
      recognition.lang = mapVoiceLanguage(languageSelect.value);
    }
    state.language = languageSelect.value;
    applyLanguageDefaults(state.language);
    updateSessionBadge();
    updateVoiceStatus(`Voice language set to ${state.language.toUpperCase()}.`);
  });

  languageTabs.forEach((button) => {
    button.addEventListener("click", () => {
      const nextLanguage = button.getAttribute("data-language") || "en";
      languageSelect.value = nextLanguage;
      languageSelect.dispatchEvent(new Event("change"));
    });
  });

  if (SpeechRecognitionCtor) {
    updateVoiceStatus("Tap the mic to start. In continuous voice mode, ManoVarta will keep the conversation moving aloud.");
  } else {
    updateVoiceStatus("Tap the mic to record. ManoVarta will transcribe it in the cloud.");
  }
  if (autoSendToggle?.checked && speakToggle && !speakToggle.checked) {
    speakToggle.checked = true;
  }
  updateMicButtonLabel();
}

function toggleListening() {
  if (listening) {
    stopListening();
    return;
  }
  if (shouldPreferBrowserVoice()) {
    startBrowserVoiceCapture("Requesting microphone access...");
    return;
  }
  if (backendVoiceAvailable()) {
    updateVoiceStatus("Requesting microphone access...");
    startBackendRecording().catch((error) => {
      console.error(error);
      if (recognition) {
        startBrowserVoiceCapture("Cloud recording could not start. Switching to browser voice...");
        return;
      }
      updateVoiceStatus("Voice recording could not start. Please type instead.", true);
    });
    return;
  }
  if (!recognition) {
    updateVoiceStatus("Voice is not available in this browser.", true);
    return;
  }
  recognition.lang = mapVoiceLanguage(languageSelect.value);
  updateVoiceStatus("Requesting microphone access...");
  recognition.start();
}

function stopListening() {
  state.voiceLoopArmed = false;
  if (recognition && listening) {
    recognition.stop();
    return;
  }
  if (backendVoiceAvailable() && mediaRecorder && mediaRecorder.state !== "inactive") {
    stopBackendRecording();
  }
}

function maybeSpeak(turn) {
  if (!speakToggle.checked || turn.speaker !== "assistant") {
    state.voiceLoopArmed = false;
    return;
  }

  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  if (state.runtime?.text_to_speech_enabled) {
    updateVoiceStatus("ManoVarta is replying aloud...");
    fetch(`/voice/speak?language=${encodeURIComponent(state.language)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: turn.text }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Voice synthesis failed (${response.status})`);
        }
        return response.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        currentAudio = new Audio(url);
        currentAudio.preload = "auto";
        currentAudio.onended = () => {
          URL.revokeObjectURL(url);
          currentAudio = null;
          updateVoiceStatus("Your turn. Speak when ready.");
          maybeResumeVoiceLoop();
        };
        currentAudio.onerror = () => {
          URL.revokeObjectURL(url);
          currentAudio = null;
          fallbackSpeak(turn.text);
        };
        currentAudio.play().catch(() => {
          URL.revokeObjectURL(url);
          currentAudio = null;
          fallbackSpeak(turn.text);
        });
      })
      .catch((error) => {
        console.error(error);
        if (speechSynthesisApi) {
          fallbackSpeak(turn.text);
          return;
        }
        state.voiceLoopArmed = false;
      });
    return;
  }

  if (speechSynthesisApi) {
    fallbackSpeak(turn.text);
    return;
  }

  state.voiceLoopArmed = false;
}

function fallbackSpeak(text) {
  if (!speechSynthesisApi) {
    state.voiceLoopArmed = false;
    return;
  }

  speechSynthesisApi.cancel();
  updateVoiceStatus("ManoVarta is replying aloud...");
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = mapVoiceLanguage(state.language);
  const voice = pickVoice(utterance.lang);
  if (voice) {
    utterance.voice = voice;
  }
  utterance.onend = () => {
    updateVoiceStatus("Your turn. Speak when ready.");
    maybeResumeVoiceLoop();
  };
  utterance.onerror = () => {
    state.voiceLoopArmed = false;
  };
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
downloadButton?.addEventListener("click", downloadExport);
backstageToggle?.addEventListener("click", () => {
  toggleDisclosure(backstagePanel, backstageToggle, {
    open: "Presenter tools",
    close: "Hide presenter tools",
  });
});
backstageClose?.addEventListener("click", () => {
  setDisclosureState(backstagePanel, backstageToggle, false, {
    open: "Presenter tools",
    close: "Hide presenter tools",
  });
});
demoToggle?.addEventListener("click", () => {
  toggleDisclosure(demoPanel, demoToggle, {
    open: "Show demo scenarios",
    close: "Hide demo scenarios",
  });
});
insightsToggle?.addEventListener("click", () => {
  toggleDisclosure(insightPanel, insightsToggle, {
    open: "Show care details",
    close: "Hide care details",
  });
});
architectureButton?.addEventListener("click", openArchitectureModal);
architectureClose?.addEventListener("click", closeArchitectureModal);
architectureModal?.addEventListener("click", (event) => {
  if (event.target === architectureModal) {
    closeArchitectureModal();
  }
});
document.addEventListener("keydown", (event) => {
  if (architectureModal && event.key === "Escape" && !architectureModal.classList.contains("is-hidden")) {
    closeArchitectureModal();
  }
});

if (demoPanel && demoToggle) {
  setDisclosureState(demoPanel, demoToggle, false, {
    open: "Show demo scenarios",
    close: "Hide demo scenarios",
  });
}
if (insightPanel && insightsToggle) {
  setDisclosureState(insightPanel, insightsToggle, false, {
    open: "Show care details",
    close: "Hide care details",
  });
}
if (backstagePanel && backstageToggle) {
  setDisclosureState(backstagePanel, backstageToggle, false, {
    open: "Presenter tools",
    close: "Hide presenter tools",
  });
}

setupVoice();
applyLanguageDefaults(state.language);
updateSessionBadge();
resetInsightPanel();
state.recentCheckins = loadRecentCheckins();
renderHistory();
setSessionLiveState(false);
document.body.classList.toggle("review-mode", reviewMode);
if (reviewMode) {
  if (backstagePanel && backstageToggle) {
    setDisclosureState(backstagePanel, backstageToggle, true, {
      open: "Presenter tools",
      close: "Hide presenter tools",
    });
  }
}

fetchBootstrap()
  .then(() => {
    setStatusBanner(LANGUAGE_UI[state.language].runtimeReady, "success");
  })
  .catch((error) => {
    console.error(error);
    runtimeInfo.textContent = "Runtime config unavailable.";
    setStatusBanner("Backend bootstrap failed. Verify API service.", "error");
  });
