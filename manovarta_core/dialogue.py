from __future__ import annotations

from dataclasses import dataclass
import re
from statistics import mean
from typing import Dict, Iterable, Optional, Tuple

from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import (
    ChatSession,
    CoveragePlan,
    DialoguePlan,
    DisclosureMetrics,
    FatigueLevel,
    NudgeEvent,
    ReadinessLevel,
    ScreeningSnapshot,
    SteeringPreference,
    TopicState,
    UserStyleProfile,
)


OPENING_PROMPTS = {
    "en": "Thanks for being here. Over the last couple of weeks, what has felt the heaviest lately?",
    "hi": "शुक्रिया, आप यहाँ आए। पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?",
    "hinglish": "Thanks for joining. Pichhle do hafton mein sabse zyada kya heavy laga?",
}

SAFETY_MESSAGES = {
    "en": "I’m concerned by what you just shared. I’m pausing the screening flow and marking this for urgent human review.",
    "hi": "आपने जो बताया उससे तुरंत चिंता हो रही है। मैं सामान्य जाँच-प्रवाह रोककर इसे तत्काल मानवीय समीक्षा के लिए चिह्नित कर रहा हूँ।",
    "hinglish": "Jo aapne share kiya usse concern ho raha hai. Main normal screening pause karke ise urgent human review ke liye mark kar raha hoon.",
}

CLOSING_MESSAGES = {
    "en": "I have enough detail for a structured summary now. If one important detail still feels missing, you can say it directly.",
    "hi": "मेरे पास अब एक संरचित सार के लिए काफ़ी जानकारी है। अगर कोई एक ज़रूरी बात अभी भी छूटी लग रही हो, तो आप उसे सीधे बता सकते हैं।",
    "hinglish": "Ab mere paas structured summary ke liye enough detail hai. Agar ek important detail abhi bhi missing lag rahi ho, to aap use seedha bol sakte ho.",
}

FINAL_HOLD_MESSAGES = {
    "en": "Okay. I’ll hold that as the current summary for now. If one important detail still feels missing later, you can say it directly.",
    "hi": "ठीक है। अभी के लिए मैं इसे वर्तमान सार मानकर रखता हूँ। अगर बाद में कोई एक ज़रूरी बात छूटी लगे, तो आप उसे सीधे बता सकते हैं।",
    "hinglish": "Theek hai. Abhi ke liye main ise current summary maan kar hold kar raha hoon. Agar baad mein koi ek zaroori detail missing lage, to aap use seedha bol sakte ho.",
}

FINAL_HOLD_VARIANTS = {
    "en": (
        FINAL_HOLD_MESSAGES["en"],
        "Understood. I’ll keep this as the current summary for now. If one concrete missing detail stands out later, you can add just that.",
        "That makes sense. I’m holding the current summary as it is for now. If one important detail still feels missing later, you can say it directly.",
    ),
    "hi": (
        FINAL_HOLD_MESSAGES["hi"],
        "समझ गया। अभी के लिए मैं इसी सार को पकड़े रखता हूँ। अगर बाद में कोई एक साफ़ छूटी हुई बात याद आए, तो आप उसे सीधे बता सकते हैं।",
        "ठीक है। मैं अभी यही मौजूदा सार रख रहा हूँ। अगर बाद में कोई एक ज़रूरी बात छूटी लगे, तो आप उसे सीधे बता सकते हैं।",
    ),
    "hinglish": (
        FINAL_HOLD_MESSAGES["hinglish"],
        "Samajh gaya. Abhi ke liye main isi current summary ko hold kar raha hoon. Agar baad mein koi ek clear missing detail lage, to aap use seedha bol sakte ho.",
        "Theek hai. Main abhi isi summary ko hold kar raha hoon. Agar baad mein koi ek zaroori detail missing lage, to aap use seedha bol sakte ho.",
    ),
}

FINAL_REST_MESSAGES = {
    "en": "Okay. We can leave it here for now.",
    "hi": "ठीक है, अभी यहीं रोकते हैं।",
    "hinglish": "Theek hai, abhi yahin rok dete hain.",
}

POST_CLOSE_CHOOSER_MESSAGES = {
    "en": "If you want, you can add the one missing detail that matters most, or we can leave this as the current summary.",
    "hi": "अगर आप चाहें, तो सबसे ज़्यादा महत्वपूर्ण एक छूटी हुई बात जोड़ सकते हैं, या हम इसे अभी का सार मानकर यहीं छोड़ सकते हैं।",
    "hinglish": "Agar aap chahein, to jo ek missing detail sabse important lag rahi ho woh bol sakte ho, ya hum ise current summary maan kar yahin chhod sakte hain.",
}

ANXIETY_LOOP_BREAK_PROMPTS = {
    "en": "Let me pause and reflect what I’m hearing: this anxiety seems to build at certain times, affect both mind and body, and feel heavier on stressful days. If that fits, tell me just one last thing: does it mostly stay around work or responsibilities, or does it spread into other parts of life too?",
    "hi": "मैं थोड़ा रुककर जो समझ आ रहा है उसे पकड़ना चाहता हूँ: यह चिंता कुछ खास समय पर बढ़ती है, दिमाग और शरीर दोनों पर असर डालती है, और तनाव वाले दिनों में ज्यादा लग सकती है। अगर यह सही लग रहा है, तो बस एक आख़िरी बात बताइए: यह ज़्यादा काम या जिम्मेदारियों तक रहती है, या दूसरी बातों में भी फैल जाती है?",
    "hinglish": "Main thoda ruk kar jo samajh aa raha hai use hold karna chahta hoon: yeh anxiety kuch specific times par build hoti hai, mind aur body dono par effect karti hai, aur stressful days mein heavier lag sakti hai. Agar yeh sahi lag raha hai, to bas ek last cheez batao: yeh zyada work ya responsibilities tak rehti hai, ya life ke aur parts mein bhi spread ho jaati hai?",
}

ANXIETY_LOOP_CLOSE_PROMPTS = {
    "en": "I have enough to hold onto the main pattern now: this anxiety builds more at certain times, affects both mind and body, and can feel heavier on stressful days. I can treat that as the working summary unless there is one important detail you still want to add.",
    "hi": "अब मेरे पास मुख्य पैटर्न पकड़ने लायक काफ़ी जानकारी है: यह चिंता कुछ खास समय पर बढ़ती है, दिमाग और शरीर दोनों पर असर डालती है, और तनाव वाले दिनों में ज्यादा लग सकती है। अगर कोई बहुत ज़रूरी बात बाकी न हो, तो मैं इसे अभी कामचलाऊ सार मान सकता हूँ।",
    "hinglish": "Ab mere paas main pattern hold karne ke liye enough detail hai: yeh anxiety kuch specific times par build hoti hai, mind aur body dono par effect karti hai, aur stressful days mein heavier lag sakti hai. Agar koi bahut important detail baaki nahi hai, to main ise abhi working summary maan sakta hoon.",
}

RAPPORT_PROMPTS = {
    "en": "Has it been feeling more like low mood, constant worry, poor sleep, or a mix of those?",
    "hi": "क्या यह ज़्यादा उदासी, लगातार चिंता, नींद की दिक्कत, या इनका मिश्रण लग रहा है?",
    "hinglish": "Kya yeh zyada low mood, constant worry, sleep issue, ya in sab ka mix lag raha hai?",
}

REFLECTION_PREFIXES = {
    "en": {
        "moderate": "Thanks for sharing that.",
        "high": "That sounds hard.",
    },
    "hi": {
        "moderate": "यह बताने के लिए शुक्रिया।",
        "high": "यह काफ़ी मुश्किल लग रहा है।",
    },
    "hinglish": {
        "moderate": "Yeh share karne ke liye thanks.",
        "high": "Yeh kaafi hard lag raha hai.",
    },
}

SOFTENING_SUFFIXES = {
    "en": "Whichever part feels easier to answer is okay.",
    "hi": "जो हिस्सा जवाब देना आसान लगे, उसी से शुरू करना ठीक है।",
    "hinglish": "Jo part answer karna easier lage, usse start karna bilkul fine hai.",
}

BRIEF_DETAIL_SUFFIXES = {
    "en": "One recent example or one timing detail is enough.",
    "hi": "एक हाल का उदाहरण या समय का एक संकेत भी काफ़ी है।",
    "hinglish": "Ek recent example ya ek timing detail bhi enough hai.",
}

OPEN_STORY_SUFFIXES = {
    "en": "You can answer in your own words and stay with the part that feels most important.",
    "hi": "आप अपने शब्दों में जवाब दे सकते हैं और जो हिस्सा सबसे महत्वपूर्ण लगे, उसी पर टिक सकते हैं।",
    "hinglish": "Aap apne words mein jawab de sakte ho aur jo part sabse important lage us par reh sakte ho.",
}

SAFETY_SHORT_ANSWER_SUFFIXES = {
    "en": "A short direct answer is okay here.",
    "hi": "यहाँ एक छोटा और सीधा जवाब भी ठीक है।",
    "hinglish": "Yahan short direct answer bhi bilkul theek hai.",
}

TOPIC_PROMPTS: Dict[str, Dict[str, str]] = {
    "mood": {
        "en": "On most days, has it felt more like low mood itself, or more like losing interest in things you usually enjoy?",
        "hi": "ज़्यादातर दिनों में यह ज़्यादा उदास मन जैसा लगता है, या पहले जो चीज़ें अच्छी लगती थीं उनमें दिल कम लगता है?",
        "hinglish": "Most days yeh zyada low mood jaisa lagta hai, ya pehle jo cheezein achhi lagti thi unmein mann kam lagta hai?",
    },
    "sleep": {
        "en": "Has sleep mostly been hard to start, hard to stay asleep, or are you sleeping more than usual?",
        "hi": "नींद में ज़्यादा दिक्कत सोने की शुरुआत में है, बीच-बीच में उठने में, या ज़रूरत से ज़्यादा नींद आ रही है?",
        "hinglish": "Sleep issue zyada sone ki shuruat mein hai, beech beech mein uthne mein, ya usual se zyada sleep ho rahi hai?",
    },
    "energy": {
        "en": "Is it more like low energy through the day, changes in appetite, or both?",
        "hi": "क्या बात ज़्यादा दिन भर की थकान की है, भूख के बदलाव की, या दोनों की?",
        "hinglish": "Kya issue zyada low energy ka hai, appetite change ka, ya dono ka?",
    },
    "self_view": {
        "en": "When things feel this heavy, do you also end up blaming yourself or feeling like a burden?",
        "hi": "जब चीज़ें इतनी भारी लगती हैं, क्या आप खुद को ज़्यादा दोष देने लगते हैं या बोझ जैसा महसूस होता है?",
        "hinglish": "Jab cheezein itni heavy lagti hain, kya aap khud ko zyada blame karte ho ya burden jaisa feel hota hai?",
    },
    "focus": {
        "en": "When you try to study or work, is it more that your focus keeps breaking, or that you keep rereading or rechecking because things do not stick?",
        "hi": "जब आप पढ़ने या काम करने बैठते हैं, क्या ज़्यादा दिक्कत ध्यान टूटने की होती है, या एक ही चीज़ बार-बार देखनी पड़ती है क्योंकि बात टिकती नहीं?",
        "hinglish": "Jab aap study ya work karte ho, kya zyada issue focus break hone ka hota hai, ya same cheez baar baar dekhni padti hai kyunki woh stick nahi karti?",
    },
    "anxiety": {
        "en": "Does this feel more like constant worry in your mind, tension in your body, or both at the same time?",
        "hi": "क्या यह ज़्यादा दिमाग की लगातार चिंता जैसा लगता है, शरीर के तनाव जैसा, या दोनों साथ में?",
        "hinglish": "Kya yeh zyada constant worry in the mind jaisa lagta hai, body tension jaisa, ya dono ek saath?",
    },
    "safety": {
        "en": "I want to check carefully because your safety matters. Have thoughts of hurting yourself or not wanting to be alive shown up at all?",
        "hi": "मैं ध्यान से पूछना चाहता हूँ क्योंकि आपकी सुरक्षा ज़रूरी है। क्या खुद को नुकसान पहुँचाने या ज़िंदा न रहने के ख़याल आए हैं?",
        "hinglish": "Main carefully poochna chahta hoon kyunki aapki safety matter karti hai. Kya khud ko hurt karne ya zinda na rehne wale thoughts aaye hain?",
    },
}

UNDERCOVERED_ITEM_BOOSTS: Dict[str, int] = {
    "phq_q5_appetite": 3,
    "phq_q6_worthlessness": 4,
    "phq_q7_concentration": 3,
    "gad_q2_control_worry": 3,
    "gad_q3_excessive_worry": 2,
    "gad_q4_trouble_relaxing": 3,
    "gad_q6_irritability": 2,
    "gad_q7_fear_awful": 3,
}

TOPIC_LABELS = {
    "mood": {"en": "mood", "hi": "मनोदशा", "hinglish": "mood"},
    "sleep": {"en": "sleep", "hi": "नींद", "hinglish": "sleep"},
    "energy": {"en": "energy", "hi": "ऊर्जा", "hinglish": "energy"},
    "self_view": {"en": "self-view", "hi": "अपने बारे में सोच", "hinglish": "self-view"},
    "focus": {"en": "focus", "hi": "ध्यान", "hinglish": "focus"},
    "anxiety": {"en": "anxiety", "hi": "चिंता", "hinglish": "anxiety"},
    "safety": {"en": "safety", "hi": "सुरक्षा", "hinglish": "safety"},
    "summary": {"en": "summary", "hi": "सार", "hinglish": "summary"},
    "check_in": {"en": "check-in", "hi": "बातचीत", "hinglish": "check-in"},
}

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_TOKEN_RE = re.compile(r"[A-Za-z]+")

TRANSLITERATED_HINDI_MARKERS = (
    "nahi",
    "haan",
    "bahut",
    "mann",
    "mujhe",
    "mera",
    "meri",
    "kya",
    "kyun",
    "kaafi",
    "thoda",
    "lagta",
    "ho raha",
    "rehi",
    "raha",
    "dimag",
)
ENGLISH_CONTEXT_MARKERS = (
    "sleep",
    "work",
    "college",
    "class",
    "mind",
    "focus",
    "job",
    "future",
    "stress",
    "routine",
    "anxiety",
    "mood",
)
HEDGE_MARKERS = (
    "not sure",
    "don't know",
    "do not know",
    "idk",
    "maybe",
    "i guess",
    "kind of",
    "sort of",
    "pata nahi",
    "shayad",
)
DETAIL_MARKERS = (
    "because",
    "for example",
    "for instance",
    "usually",
    "mostly",
    "lately",
    "when",
    "since",
    "after",
    "jab",
    "kyunki",
    "subah",
    "raat",
)
IMPACT_MARKERS = (
    "work",
    "study",
    "routine",
    "day",
    "appetite",
    "sleep",
    "focus",
    "kaam",
    "padhai",
    "routine",
    "din",
    "neend",
    "bhook",
)
CLOSURE_MARKERS = (
    "that's mostly it",
    "that is mostly it",
    "that's the main thing",
    "that is the main thing",
    "i think that's it",
    "i think that is it",
    "bas itna hi",
    "yehi main baat hai",
    "aur kuch khaas nahi",
    "haan aap maan lo",
    "हाँ आप मान लो",
    "मान लो",
)
FATIGUE_MARKERS = (
    "not sure what else",
    "i don't know what else",
    "that is all",
    "that's all",
    "too tired",
    "hard to explain",
    "bas",
    "aur nahi",
    "samjhana mushkil",
)
ACTIVATION_MARKERS = (
    "low energy",
    "energy down",
    "energy low",
    "energy bhi down",
    "energy bhi low",
    "energy down ho",
    "heavy in the morning",
    "hard to get started",
    "harder to get started",
    "taking longer to get started",
    "takes longer to get started",
    "mind taking longer",
    "mind feels slow",
    "mind feels slower",
    "brain fog",
    "slow to start",
    "slow to get started",
    "subah heavy",
    "mind ko start hone mein time lagta",
    "mind ko start hone me time lagta",
    "start hone mein time lagta",
    "start hone me time lagta",
    "ऊर्जा",
    "ऊर्जा कम",
    "सुबह भारी",
    "दिमाग धीमा",
    "धीमा लग",
)
SLEEP_PATTERN_MARKERS = (
    "hard to fall asleep",
    "cannot fall asleep",
    "can't fall asleep",
    "trouble falling asleep",
    "wake up around",
    "wake up at",
    "wake around",
    "waking during the night",
    "wake during the night",
    "middle of the night",
    "wake too early",
    "waking too early",
    "waking up too early",
    "3 am",
    "4 am",
    "3 or 4 am",
    "stay asleep",
    "staying asleep",
    "नींद आने में",
    "सोने में",
    "बीच में जाग",
    "बार-बार उठ",
    "बहुत जल्दी उठ",
    "3 बजे",
    "4 बजे",
    "raat ko 3 baje",
    "raat ko 4 baje",
    "aankh khul",
)
SLEEP_IMPACT_MARKERS = (
    "tired the next morning",
    "tired next morning",
    "next morning",
    "morning tired",
    "not fresh",
    "not rested",
    "सुबह थक",
    "सुबह थकान",
    "थकान रहती",
    "fresh feel nahi",
    "fresh नहीं",
)
TIME_MARKERS = (
    "night",
    "nights",
    "morning",
    "mornings",
    "evening",
    "evenings",
    "afternoon",
    "late night",
    "subah",
    "raat",
    "shaam",
    "din mein",
    "रात",
    "रात में",
    "सुबह",
    "सुबह में",
    "शाम",
    "देर रात",
    "by the end of the day",
    "end of the day",
    "day ke end",
    "din ke end",
    "दिन के अंत",
    "दिन के end",
)
FREQUENCY_MARKERS = (
    "every day",
    "daily",
    "days a week",
    "nights a week",
    "times a week",
    "most days",
    "usually",
    "often",
    "roz",
    "har din",
    "hafte mein",
    "week mein",
    "हफ़्ते में",
    "हफ्ते में",
    "रोज़",
    "रोज",
    "हर दिन",
    "अक्सर",
)
FREQUENCY_PATTERNS = (
    re.compile(r"\b(?:every day|daily|most days|often|usually)\b"),
    re.compile(r"\b(?:once|twice)\s+a\s+(?:day|week)\b"),
    re.compile(r"\b(?:\d+|one|two|three|four|five|six|seven)\s*(?:-|to)?\s*(?:\d+|one|two|three|four|five|six|seven)?\s*(?:day|days|time|times)\s+a\s+week\b"),
    re.compile(r"\b(?:hafte|week)\s+mein\b"),
    re.compile(r"(?:हफ़्ते|हफ्ते)\s*में"),
    re.compile(r"(?:कई|एक|दो|तीन|चार|पांच|पाँच|छह|सात|\d+)\s*बार"),
    re.compile(r"(?:कई|चार|पांच|पाँच|\d+)\s*(?:-|–|—)?\s*(?:चार|पांच|पाँच|\d+)?\s*दिन"),
)
WORRY_DOMAIN_MARKERS = (
    "work",
    "job",
    "money",
    "family",
    "mother",
    "mom",
    "father",
    "dad",
    "future",
    "rent",
    "exam",
    "office",
    "studies",
    "maa",
    "mummy",
    "papa",
    "काम",
    "काम को लेकर",
    "नौकरी",
    "पैसे",
    "परिवार",
    "मां",
    "मम्मी",
    "पापा",
    "पिता",
    "भविष्य",
    "पढ़ाई",
    "इम्तहान",
)
AWFUL_OUTCOME_MARKERS = (
    "something bad",
    "bad news",
    "worst",
    "out of control",
    "spiral",
    "awful",
    "terrible",
    "कुछ बुरा",
    "कुछ गलत",
    "बुरी खबर",
    "हाथ से निकल",
    "सब बिगड़",
    "गड़बड़ हो",
    "गलत हो जाएगा",
)
PERSISTENT_WORRY_MARKERS = (
    "keep going",
    "keeps going",
    "kept going",
    "keep running",
    "keeps running",
    "kept running",
    "going no matter",
    "no matter how much i try",
    "won't stop",
    "wont stop",
    "loop",
    "looping",
    "chalta rehta",
    "chalta rehti",
    "chalte rehta",
    "chalte rehti",
    "चलती रहती",
    "चलता रहता",
    "चलते रहता",
    "रुकती नहीं",
    "रुकता नहीं",
    "बंद नहीं",
    "काफी ज्यादा चले",
    "लंबे समय तक",
    "देर तक",
    "अटका रहता",
    "अटकी रहती",
)
LINGERING_TENSION_MARKERS = (
    "long time",
    "for a long time",
    "stays stuck",
    "stuck for a long time",
    "long after",
    "lambe samay tak",
    "lambe waqt tak",
    "der tak",
    "lamba time",
    "लंबे समय तक",
    "लंबे वक्त तक",
    "देर तक",
    "अटका रहता",
    "अटकी रहती",
)
WORRY_SCOPE_SPREAD_MARKERS = (
    "spreads to other things",
    "spread to other things",
    "spreads to other areas",
    "spreads into other parts",
    "many things",
    "several things",
    "other things too",
    "more than one thing",
    "kai baat",
    "kai cheez",
    "कई बात",
    "कई चीज",
    "दूसरी बातों में",
    "कई बातों में फैल",
    "कई चीजों में फैल",
)
WORRY_SCOPE_SINGLE_MARKERS = (
    "one main issue",
    "one thing",
    "one same thing",
    "single issue",
    "same issue",
    "same thing",
    "only one thing",
    "only around",
    "mostly one thing",
    "ek main baat",
    "ek hi baat",
    "ek hi cheez",
    "ek issue",
    "sirf ek",
    "keval ek",
    "एक मुख्य बात",
    "एक ही बात",
    "एक ही चीज",
    "एक मुद्दे",
    "सिर्फ",
    "केवल",
    "इसी तक",
)
SHORT_FOLLOWUP_MARKERS = (
    "yes",
    "yeah",
    "yep",
    "no",
    "nah",
    "nope",
    "both",
    "mostly",
    "body",
    "mind",
    "thoughts",
    "physical",
    "night",
    "morning",
    "evening",
    "sometimes",
    "usually",
    "dono",
    "dono saath mein",
    "saath mein",
    "दोनों",
    "दोनों साथ में",
    "साथ में",
)
CLOSE_ACK_MARKERS = (
    "ok",
    "okay",
    "theek hai",
    "ठीक है",
    "haan theek hai",
    "हाँ ठीक है",
    "haan aap maan lo",
    "हाँ आप मान लो",
    "maan lo",
    "मान लो",
    "haan puch lo",
    "haan pooch lo",
    "हाँ पूछ लो",
    "पूछ लो",
    "haan aap maan lo",
    "yes use that",
)
SENSITIVE_ITEM_IDS = (
    "phq_q6_worthlessness",
    "phq_q9_self_harm",
    "gad_q7_fear_awful",
)

TOPIC_REFLECTIONS = {
    "mood": {
        "en": "It sounds like the emotional weight itself has been hard to carry.",
        "hi": "लगता है भावनात्मक बोझ अपने-आप में ही काफ़ी भारी हो गया है।",
        "hinglish": "Lag raha hai emotional weight khud hi kaafi heavy ho gaya hai.",
    },
    "sleep": {
        "en": "It sounds like sleep is taking a real hit here.",
        "hi": "लगता है इसका असर नींद पर काफ़ी सीधा पड़ रहा है।",
        "hinglish": "Lag raha hai sleep par iska kaafi direct impact aa raha hai.",
    },
    "energy": {
        "en": "It sounds like the day is taking more effort than it used to.",
        "hi": "लगता है रोज़ का दिन पहले से ज़्यादा मेहनत माँग रहा है।",
        "hinglish": "Lag raha hai normal day pehle se zyada effort le raha hai.",
    },
    "self_view": {
        "en": "It sounds like this is affecting how you are talking to yourself too.",
        "hi": "लगता है इसका असर इस बात पर भी पड़ रहा है कि आप अपने-आप से कैसे बात कर रहे हैं।",
        "hinglish": "Lag raha hai iska effect aap apne aap se kaise baat karte ho us par bhi aa raha hai.",
    },
    "focus": {
        "en": "It sounds like this is getting in the way of staying with tasks.",
        "hi": "लगता है इसकी वजह से काम पर टिके रहना मुश्किल हो रहा है।",
        "hinglish": "Lag raha hai tasks par tikna is wajah se mushkil ho raha hai.",
    },
    "anxiety": {
        "en": "It sounds like the worry is staying active even when things are quiet.",
        "hi": "लगता है चिंता तब भी सक्रिय रहती है जब बाहर सब शांत हो।",
        "hinglish": "Lag raha hai worry tab bhi active rehti hai jab bahar sab quiet ho.",
    },
    "safety": {
        "en": "I want to slow this down and stay very clear for a moment.",
        "hi": "मैं एक पल के लिए गति धीमी करके इसे बहुत साफ़ तौर पर समझना चाहता हूँ।",
        "hinglish": "Main ek moment ke liye pace slow karke bahut clearly samajhna chahta hoon.",
    },
}

ITEM_REFLECTIONS = {
    "phq_q1_anhedonia": {
        "en": "It sounds like things that usually matter to you are feeling flatter right now.",
        "hi": "लगता है जो चीज़ें पहले मायने रखती थीं, उनमें अभी मन कम लग रहा है।",
        "hinglish": "Lag raha hai jo cheezein pehle matter karti thi, unmein ab mann kam lag raha hai.",
    },
    "phq_q2_low_mood": {
        "en": "It sounds like the days themselves have been feeling heavy.",
        "hi": "लगता है दिन अपने-आप में ही भारी लग रहे हैं।",
        "hinglish": "Lag raha hai din khud hi heavy feel ho rahe hain.",
    },
    "phq_q3_sleep": {
        "en": "It sounds like sleep is getting hit in a real way.",
        "hi": "लगता है इसका असर नींद पर साफ़ पड़ रहा है।",
        "hinglish": "Lag raha hai iska effect sleep par kaafi clearly aa raha hai.",
    },
    "phq_q6_worthlessness": {
        "en": "It sounds like this is starting to affect how you are seeing yourself too.",
        "hi": "लगता है इसका असर इस पर भी पड़ रहा है कि आप अपने बारे में क्या महसूस कर रहे हैं।",
        "hinglish": "Lag raha hai iska effect is par bhi aa raha hai ki aap apne baare mein kya feel kar rahe ho.",
    },
    "phq_q7_concentration": {
        "en": "It sounds like this is making it harder to stay with work or study.",
        "hi": "लगता है इसकी वजह से काम या पढ़ाई पर टिके रहना मुश्किल हो रहा है।",
        "hinglish": "Lag raha hai is wajah se work ya study par tikna mushkil ho raha hai.",
    },
    "gad_q2_control_worry": {
        "en": "It sounds like the worry is hard to switch off once it starts.",
        "hi": "लगता है चिंता शुरू होने के बाद उसे रोकना आसान नहीं पड़ रहा।",
        "hinglish": "Lag raha hai worry ek baar start ho jaaye to switch off karna easy nahi pad raha.",
    },
    "gad_q4_trouble_relaxing": {
        "en": "It sounds like settling down is taking more effort than it should.",
        "hi": "लगता है खुद को शांत करना जितना होना चाहिए, उससे ज़्यादा मुश्किल हो रहा है।",
        "hinglish": "Lag raha hai settle hona jitna hona chahiye usse zyada effort le raha hai.",
    },
    "gad_q5_restlessness": {
        "en": "It sounds like your mind or body is staying keyed up for longer than you want.",
        "hi": "लगता है दिमाग या शरीर उम्मीद से ज़्यादा देर तक बेचैन बना रहता है।",
        "hinglish": "Lag raha hai mind ya body expected se zyada der tak keyed up rehte hain.",
    },
    "gad_q3_excessive_worry": {
        "en": "It sounds like the worry may be spreading across more than one part of life.",
        "hi": "लगता है चिंता एक बात तक सीमित न रहकर दूसरी बातों में भी फैल सकती है।",
        "hinglish": "Lag raha hai worry ek hi cheez tak limited nahi rehkar life ke aur parts mein bhi spread ho sakti hai.",
    },
    "gad_q7_fear_awful": {
        "en": "It sounds like the anxiety can start pointing toward what might go wrong next.",
        "hi": "लगता है चिंता आगे क्या गलत हो सकता है, उस तरफ़ भी खिंचने लगती है।",
        "hinglish": "Lag raha hai anxiety agla kya galat ho sakta hai us direction mein bhi kheenchne lagti hai.",
    },
}

CONTEXTUAL_REFLECTIONS = {
    "worry_domain_focus": {
        "en": "It sounds like work or future thoughts are what the worry keeps locking onto.",
        "hi": "लगता है चिंता बार-बार काम या भविष्य की तरफ़ ही अटक जाती है।",
        "hinglish": "Lag raha hai worry baar baar work ya future wali line par hi atak jaati hai.",
    },
    "worry_single_issue": {
        "en": "It sounds like this keeps circling one same issue more than everything at once.",
        "hi": "लगता है यह एक ही बात के इर्द-गिर्द ज़्यादा घूमती रहती है, सब तरफ़ नहीं फैलती।",
        "hinglish": "Lag raha hai yeh sab taraf spread hone se zyada ek hi baat ke around ghoomti rehti hai.",
    },
    "flat_while_functioning": {
        "en": "It sounds like you are still getting through the day, but it feels flat underneath.",
        "hi": "लगता है आप दिन तो निकाल रहे हैं, लेकिन अंदर से सब कुछ सपाट-सा लग रहा है।",
        "hinglish": "Lag raha hai aap din nikaal rahe ho, lekin andar se sab flat sa lag raha hai.",
    },
}

ITEM_FOLLOW_UPS: Dict[str, Dict[str, Dict[str, str]]] = {
    "phq_q1_anhedonia": {
        "default": {
            "en": "When you try to do things you usually care about, does the interest drop before you start, or do you go through with them but feel very little from them?",
            "hi": "जब आप उन कामों की तरफ़ जाते हैं जो पहले अच्छे लगते थे, क्या शुरू करने से पहले ही मन हट जाता है, या आप कर लेते हैं लेकिन उनसे बहुत कम महसूस होता है?",
            "hinglish": "Jab aap un cheezon ki taraf jaate ho jo pehle achhi lagti thi, kya start karne se pehle hi mann hat jata hai, ya aap kar lete ho lekin unse bahut kam feel hota hai?",
        },
        "timing_known": {
            "en": "That timing helps. Around that part of the day, does the interest fade before you start things, or do you still do them but feel very little from them?",
            "hi": "यह समय-सूचना मददगार है। उस समय के आसपास, क्या काम शुरू करने से पहले ही मन हट जाता है, या आप कर लेते हैं लेकिन उनसे बहुत कम महसूस होता है?",
            "hinglish": "Yeh timing helpful hai. Us waqt ke around, kya cheezon ko start karne se pehle hi mann hat jata hai, ya aap kar lete ho lekin unse bahut kam feel hota hai?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, does the interest fade before you start things, or do you still do them but feel very little from them?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या काम शुरू करने से पहले ही मन हट जाता है, या आप कर लेते हैं लेकिन उनसे बहुत कम महसूस होता है?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab aisa hota hai, kya cheezon ko start karne se pehle hi mann hat jata hai, ya aap kar lete ho lekin unse bahut kam feel hota hai?",
        },
    },
    "phq_q2_low_mood": {
        "default": {
            "en": "When this hits, does it sit more like sadness or heaviness through the day, or does it come in waves around certain times?",
            "hi": "जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?",
            "hinglish": "Jab yeh feel hota hai, kya yeh zyada poore din ki sadness ya heaviness jaisa rehta hai, ya kuch specific times par waves mein aata hai?",
        },
        "repeat_probe": {
            "en": "When that feeling is there, is it more like a steady heavy mood through the day, or more like emotional numbness that comes and goes?",
            "hi": "जब यह बना रहता है, क्या यह ज़्यादा दिन भर का लगातार भारी मन लगता है, या भावनात्मक सुन्नपन जैसा जो आता-जाता रहता है?",
            "hinglish": "Jab yeh bana rehta hai, kya yeh zyada poore din ka steady heavy mood lagta hai, ya emotional numbness jaisa jo aata-jaata rehta hai?",
        },
        "deepening_probe": {
            "en": "When that flat or heavy feeling is there, can small moments still cut through it if something needs your attention, or does it stay with you even while you keep going through the motions?",
            "hi": "जब यह सपाट या भारी एहसास रहता है, क्या किसी ज़रूरी चीज़ पर ध्यान देने पर थोड़ा सा हल्का होता है, या काम करते रहने पर भी वैसा ही बना रहता है?",
            "hinglish": "Jab yeh flat ya heavy feeling rehti hai, kya kisi zaroori cheez par dhyaan dene se thoda cut through hota hai, ya aap kaam karte rehte ho phir bhi yeh saath bana rehta hai?",
        },
        "functional_impact": {
            "en": "On days when you keep going through the motions, does it mostly slow you down and make basic things feel heavier, or can you function on the outside while still feeling emotionally flat underneath?",
            "hi": "जिन दिनों आप किसी तरह काम करते रहते हैं, क्या ज़्यादा ऐसा होता है कि साधारण काम भी भारी पड़ने लगते हैं, या आप बाहर से काम करते रहते हैं लेकिन अंदर से सब सपाट-सा लगता है?",
            "hinglish": "Jin dinon aap bas motions mein chalte rehte ho, kya zyada aisa hota hai ki basic cheezein bhi heavy lagne lagti hain, ya bahar se aap function kar lete ho lekin andar se sab flat lagta hai?",
        },
        "timing_known": {
            "en": "That timing helps. Around that part of the day, does it feel more like a steady heaviness, or more like a wave that rises and then passes?",
            "hi": "यह समय-सूचना मददगार है। उस समय के आसपास, क्या यह ज़्यादा लगातार भारीपन जैसा लगता है, या लहर की तरह आता-जाता है?",
            "hinglish": "Yeh timing helpful hai. Us waqt ke around, kya yeh zyada steady heaviness jaisa lagta hai, ya wave ki tarah aata-jata hai?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it shows up. When it does, does it feel more like steady heaviness, or more like a wave that rises and passes?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या यह ज़्यादा लगातार भारीपन जैसा लगता है, या लहर की तरह आता-जाता है?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab aisa hota hai, kya yeh zyada steady heaviness jaisa lagta hai, ya wave ki tarah aata-jata hai?",
        },
    },
    "phq_q3_sleep": {
        "default": {
            "en": "When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?",
            "hi": "जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?",
            "hinglish": "Jab sleep disturb hoti hai, kya zyada issue sone ki shuruat mein hota hai, raat mein baar baar uthne mein, ya bahut jaldi uth jaane mein?",
        },
        "pattern_known": {
            "en": "That helps place the sleep pattern. Roughly how many nights a week has it been happening like that?",
            "hi": "इससे नींद का पैटर्न थोड़ा साफ़ हो रहा है। लगभग हफ्ते में कितनी रातों में ऐसा होता है?",
            "hinglish": "Isse sleep pattern thoda clearer ho raha hai. Roughly week mein kitni raaton mein aisa hota hai?",
        },
        "timing_known": {
            "en": "That timing helps. When it happens, is it more trouble falling asleep, staying asleep, or waking up too early?",
            "hi": "यह समय-सूचना मददगार है। जब ऐसा होता है, क्या ज़्यादा मुश्किल नींद आने में होती है, नींद बनाए रखने में, या बहुत जल्दी उठ जाने में?",
            "hinglish": "Yeh timing helpful hai. Jab yeh hota hai, kya zyada issue sleep start hone mein hota hai, sleep banaye rakhne mein, ya bahut jaldi uth jaane mein?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. On those nights, is it more that sleep is hard to start, hard to stay in, or that you wake up too early?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। उन रातों में, क्या ज़्यादा दिक्कत नींद शुरू होने में होती है, नींद बनाए रखने में, या बहुत जल्दी उठ जाने में?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Un raaton mein, kya zyada issue sleep start hone mein hota hai, sleep banaye rakhne mein, ya bahut jaldi uth jaane mein?",
        },
        "pattern_and_frequency_known": {
            "en": "That gives me a clearer picture. The next morning, does it mostly leave you tired, foggy, or not properly rested?",
            "hi": "इससे तस्वीर थोड़ी साफ़ हो रही है। अगली सुबह क्या ज़्यादा थकान, दिमागी धुंधलापन, या ठीक से आराम न मिलने जैसा लगता है?",
            "hinglish": "Isse picture thodi clearer ho rahi hai. Agli subah zyada tired, foggy, ya properly rested na lagne jaisa hota hai?",
        },
    },
    "phq_q4_fatigue": {
        "default": {
            "en": "When the energy drops, is it more like your body feels heavy, your mind feels slow to get going, or both?",
            "hi": "जब थकान या ऊर्जा की कमी बढ़ती है, क्या ज़्यादा ऐसा लगता है कि शरीर भारी पड़ रहा है, दिमाग शुरू होने में धीमा है, या दोनों?",
            "hinglish": "Jab low energy build hoti hai, kya zyada body heavy lagti hai, mind ko start hone mein time lagta hai, ya dono?",
        },
        "timing_known": {
            "en": "That timing helps. Around that part of the day, is it more like body heaviness, a slow-starting mind, or both together?",
            "hi": "यह समय-सूचना मददगार है। उस समय के आसपास, क्या ज़्यादा शरीर भारी लगता है, दिमाग शुरू होने में धीमा पड़ता है, या दोनों साथ में?",
            "hinglish": "Yeh timing helpful hai. Us waqt ke around, kya zyada body heavy lagti hai, mind slow start hota hai, ya dono saath mein?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it hits, is it more like body heaviness, a slow-starting mind, or both together?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या ज़्यादा शरीर भारी लगता है, दिमाग शुरू होने में धीमा पड़ता है, या दोनों साथ में?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya zyada body heavy lagti hai, mind slow start hota hai, ya dono saath mein?",
        },
    },
    "phq_q7_concentration": {
        "default": {
            "en": "When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?",
            "hi": "जब आप काम या पढ़ाई पर बैठते हैं, क्या ज़्यादा ऐसा होता है कि ध्यान बार-बार भटक जाता है, या एक ही बात पर लौटते रहते हैं लेकिन वह टिकती नहीं?",
            "hinglish": "Jab aap work ya study par baithte ho, kya zyada aisa hota hai ki attention baar baar slip ho jata hai, ya same line par wapas aate rehte ho lekin woh stick nahi karti?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, does your attention drift away quickly, or do you get stuck rereading or rechecking the same thing?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या ध्यान जल्दी भटक जाता है, या आप एक ही चीज़ को बार-बार देखते रहते हैं?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab aisa hota hai, kya attention jaldi drift ho jata hai, ya aap same cheez baar baar dekhte rehte ho?",
        },
    },
    "gad_q2_control_worry": {
        "default": {
            "en": "When the worry starts, can you pull your mind away from it, or does it keep looping even when you try to stop it?",
            "hi": "जब चिंता शुरू होती है, क्या आप दिमाग को उससे हटा पाते हैं, या रोकने की कोशिश के बाद भी वह चलती रहती है?",
            "hinglish": "Jab worry start hoti hai, kya aap mind ko usse hata paate ho, ya rokne ki koshish ke baad bhi woh loop hoti rehti hai?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it shows up. When it does, can you pull your mind away from it, or does it keep looping even when you try to stop it?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब यह होता है, क्या आप दिमाग को उससे हटा पाते हैं, या रोकने की कोशिश के बाद भी वह चलता रहता है?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya aap mind ko usse hata paate ho, ya rokne ki koshish ke baad bhi woh loop hoti rehti hai?",
        },
    },
    "gad_q3_excessive_worry": {
        "default": {
            "en": "When the worry keeps running, does it spread across things like work, family, money, or the future, or does it usually get stuck on one main issue?",
            "hi": "जब चिंता चलती रहती है, क्या यह ज़्यादा काम, परिवार, पैसों या भविष्य जैसी कई बातों में फैल जाती है, या आम तौर पर किसी एक मुख्य बात पर अटकती है?",
            "hinglish": "Jab worry chalti rehti hai, kya yeh zyada work, family, money ya future jaise kai issues mein spread ho jaati hai, ya usually kisi ek main baat par atak jaati hai?",
        },
        "repeat_probe": {
            "en": "When it keeps running, does the worry jump between several things, or does it stay locked onto one main issue most of the time?",
            "hi": "जब यह चलती रहती है, क्या चिंता कई बातों के बीच घूमती रहती है, या ज़्यादातर समय एक ही मुख्य बात पर अटकी रहती है?",
            "hinglish": "Jab yeh chalti rehti hai, kya worry kai issues ke beech jump karti rehti hai, ya zyada waqt ek hi main baat par atki rehti hai?",
        },
        "timing_known": {
            "en": "That timing helps. Around that point, does the worry spread across several things, or does it stay locked onto one main issue?",
            "hi": "यह समय-सूचना मददगार है। उस समय के आसपास, क्या चिंता कई बातों में फैल जाती है, या एक मुख्य बात पर अटकी रहती है?",
            "hinglish": "Yeh timing helpful hai. Us waqt ke around, kya worry kai cheezon mein spread ho jaati hai, ya ek main issue par atki rehti hai?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, does the worry spread across several things, or stay stuck on one main issue?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या चिंता कई बातों में फैल जाती है, या एक मुख्य बात पर अटकी रहती है?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya worry kai cheezon mein spread ho jaati hai, ya ek main issue par atki rehti hai?",
        },
    },
    "gad_q4_trouble_relaxing": {
        "default": {
            "en": "When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?",
            "hi": "जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल दिमाग को शांत करना होता है, शरीर को ढीला करना, या दोनों?",
            "hinglish": "Jab aap settle hone ki koshish karte ho, kya zyada mushkil thoughts ko quiet karna hota hai, body relax karna, ya dono?",
        },
        "domain_known": {
            "en": "So once work or future worry gets going, what is harder then: quieting your thoughts, easing the body tension, or both together?",
            "hi": "तो जब काम या भविष्य की चिंता पकड़ लेती है, उस समय ज़्यादा मुश्किल क्या होता है: दिमाग को शांत करना, शरीर का तनाव ढीला करना, या दोनों साथ में?",
            "hinglish": "To jab work ya future wali worry pakad leti hai, us waqt zyada mushkil kya hota hai: thoughts ko quiet karna, body tension ko ease karna, ya dono saath mein?",
        },
        "single_issue_known": {
            "en": "So when it gets stuck on that one same issue, is the harder part quieting your thoughts, easing the body tension, or both together?",
            "hi": "तो जब यह उसी एक बात पर अटक जाती है, उस समय ज़्यादा मुश्किल क्या होता है: दिमाग को शांत करना, शरीर का तनाव ढीला करना, या दोनों साथ में?",
            "hinglish": "To jab yeh usi ek baat par atak jaati hai, us waqt zyada mushkil kya hota hai: thoughts ko quiet karna, body tension ko ease karna, ya dono saath mein?",
        },
        "repeat_probe": {
            "en": "It sounds like both mind and body can get pulled in here. When this builds up, does it settle once the moment passes, or does the tension stay stuck for a long time afterward?",
            "hi": "लगता है यहाँ दिमाग और शरीर दोनों खिंच जाते हैं। जब यह बढ़ता है, क्या पल गुजरने के बाद यह शांत हो जाता है, या तनाव लंबे समय तक अटका रहता है?",
            "hinglish": "Lag raha hai yahan mind aur body dono pull ho jaate hain. Jab yeh build hota hai, kya moment nikalne ke baad settle ho jata hai, ya tension kaafi der tak atka rehta hai?",
        },
        "timing_known": {
            "en": "That timing helps. When it hits, is it more like a busy mind, a tense body, or both together?",
            "hi": "यह समय-सूचना मददगार है। जब ऐसा होता है, क्या यह ज़्यादा व्यस्त दिमाग जैसा लगता है, तना हुआ शरीर जैसा, या दोनों साथ में?",
            "hinglish": "Yeh timing helpful hai. Jab yeh hit karta hai, kya yeh zyada busy mind jaisa lagta hai, tense body jaisa, ya dono saath mein?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it hits, does it feel more like a busy mind, a tense body, or both together?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब यह होता है, क्या यह ज़्यादा व्यस्त दिमाग जैसा लगता है, तना हुआ शरीर जैसा, या दोनों साथ में?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hit karta hai, kya yeh zyada busy mind jaisa lagta hai, tense body jaisa, ya dono saath mein?",
        },
    },
    "gad_q7_fear_awful": {
        "default": {
            "en": "When the anxiety peaks, does it feel more like something specific might go wrong, that you may get bad news, or that things could spiral out of control?",
            "hi": "जब चिंता सबसे तेज़ होती है, क्या ज़्यादा लगता है कि कुछ खास गलत हो सकता है, कोई बुरी खबर मिल सकती है, या चीज़ें हाथ से निकल सकती हैं?",
            "hinglish": "Jab anxiety peak karti hai, kya zyada lagta hai ki kuch specific galat ho sakta hai, koi bad news mil sakti hai, ya cheezein control se bahar ja sakti hain?",
        },
        "timing_known": {
            "en": "That timing helps. At that point, is the fear more about something specific going wrong, bad news, or things spiraling out of control?",
            "hi": "यह समय-सूचना मददगार है। उस समय, क्या डर ज़्यादा किसी खास गड़बड़ी का होता है, बुरी खबर का, या चीज़ों के हाथ से निकल जाने का?",
            "hinglish": "Yeh timing helpful hai. Us waqt, kya fear zyada kisi specific problem ka hota hai, bad news ka, ya cheezon ke control se bahar jaane ka?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, is the fear more about something specific going wrong, bad news, or things spiraling out of control?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या डर ज़्यादा किसी खास गड़बड़ी का होता है, बुरी खबर का, या चीज़ों के हाथ से निकल जाने का?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya fear zyada kisi specific problem ka hota hai, bad news ka, ya cheezon ke control se bahar jaane ka?",
        },
    },
    "gad_q5_restlessness": {
        "default": {
            "en": "When that restless feeling shows up, is it more that your body cannot sit still, or that your mind feels agitated even if you stay still?",
            "hi": "जब यह बेचैनी आती है, क्या ज़्यादा ऐसा लगता है कि शरीर चैन से बैठ नहीं पा रहा, या दिमाग बेचैन रहता है चाहे आप शांत बैठे हों?",
            "hinglish": "Jab yeh restlessness aati hai, kya zyada body chain se baith nahi paati, ya mind agitated rehta hai chahe aap still baithe ho?",
        },
        "timing_known": {
            "en": "That timing helps. When it shows up then, is it more like pacing or needing to move, or more like inner agitation even while you stay still?",
            "hi": "यह समय-सूचना मददगार है। जब उस समय यह होता है, क्या ज़्यादा इधर-उधर चलने या हिलने की ज़रूरत लगती है, या अंदर की बेचैनी होती है चाहे आप शांत बैठे हों?",
            "hinglish": "Yeh timing helpful hai. Jab us waqt yeh hota hai, kya zyada pacing ya move karne ki need lagti hai, ya inner agitation hoti hai chahe aap still baithe ho?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, do you mostly feel the urge to move around, or more like inner agitation even if you stay still?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब यह होता है, क्या ज़्यादा इधर-उधर चलने की इच्छा होती है, या अंदर की बेचैनी होती है चाहे आप शांत बैठे हों?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya zyada move karne ki urge hoti hai, ya inner agitation hoti hai chahe aap still baithe ho?",
        },
    },
}

ITEM_SIGNAL_MARKERS: Dict[str, Tuple[str, ...]] = {
    "phq_q1_anhedonia": ("not interested", "no interest", "disconnected", "nothing feels good", "used to enjoy", "feel flat", "feels flat", "flat now", "flat lagta", "flat lagti", "flat lagti hai", "flat lagti hain", "numb", "feel very little from them", "get much from them", "do not get much from them", "don't get much from them", "feel nahi hota", "kuch feel nahi hota", "go through the motions", "go through motions", "mann nahi lagta", "मन नहीं लगता", "दिल नहीं करता", "फीका लगता", "बहुत कम महसूस", "कटा-कटा", "कटा कटा"),
    "phq_q2_low_mood": ("low mood", "sad", "down", "empty", "heavy", "heaviness", "मन भारी", "भारी", "उदास"),
    "phq_q4_fatigue": ("tired", "drained", "fatigue", "low energy", "energy down", "wiped", "heavy in the morning", "slow to start", "slow to get started", "mind feels slow", "brain fog", "subah heavy", "थक", "थकान", "ऊर्जा", "ऊर्जा कम", "सुबह भारी", "दिमाग धीमा"),
    "phq_q6_worthlessness": ("burden", "extra burden", "burden hoon", "worthless", "useless", "make things heavier", "making things heavier", "ashamed", "shame", "बोझ", "बोझ हूँ", "सबके लिए बोझ", "बेकार", "मेरी वजह से", "शर्म"),
    "phq_q3_sleep": ("sleep", "asleep", "wake", "waking", "sleep disturb", "neend disturb", "नींद", "रात", "रात में", "उठ जाती", "switch off"),
    "phq_q7_concentration": ("focus", "concentrat", "attention", "cannot focus", "can't focus", "harder to focus", "hard to focus", "taking longer to get started", "takes longer to get started", "mind taking longer", "mind feels slow", "brain fog", "ध्यान", "focus nahi", "ध्यान नहीं टिक", "mind blanks", "screen", "start hone mein time lagta", "start hone me time lagta", "mind ko start hone mein time lagta", "mind ko start hone me time lagta", "दिमाग धीमा"),
    "gad_q2_control_worry": ("worry", "loop", "looping", "replay", "mind won't stop", "mind wont stop", "चिंता", "सोच बंद"),
    "gad_q3_excessive_worry": ("future", "rent", "family", "money", "what if", "work", "job", "exam", "काम", "काम को लेकर", "परिवार", "पैसे", "भविष्य", "हर बात"),
    "gad_q4_trouble_relaxing": ("switch off", "settle down", "quiet your thoughts", "तनाव", "शांत", "relax", "off karna", "busy mind", "tense body", "body tense", "tense in my body", "body stays tense", "stay tense in my body", "tense lagti"),
    "gad_q5_restlessness": ("restless", "restlessness", "sit still", "pacing", "बेचैनी", "chain se baith", "move around"),
}

TOPIC_SIGNAL_MARKERS: Dict[str, Tuple[str, ...]] = {
    "mood": ("low mood", "sad", "down", "empty", "heavy", "heaviness", "disconnected", "usually enjoy", "used to enjoy", "flat lagta", "flat lagti", "flat lagti hai", "flat lagti hain", "उदासी", "उदास", "खाली", "low feel", "भारी", "मन भारी", "मन नहीं लगता", "कटा-कटा", "कटा कटा"),
    "sleep": ("sleep", "asleep", "wake up", "waking", "neend", "नींद", "सोने", "उठ जाती", "night", "रात"),
    "energy": ("tired", "drained", "fatigue", "wiped", "low energy", "energy down", "energy bhi down", "energy bhi low", "energy down ho", "heavy in the morning", "slow to start", "slow to get started", "mind feels slow", "brain fog", "subah heavy", "din ke end", "day ke end", "दिन के अंत", "thak", "थक", "थका", "थकान", "ऊर्जा", "सुबह भारी", "दिमाग धीमा", "धीमा लग"),
    "self_view": ("burden", "extra burden", "burden hoon", "worthless", "useless", "guilt", "make things heavier", "making things heavier", "ashamed", "shame", "बोझ", "बोझ हूँ", "सबके लिए बोझ", "बेकार", "गलती मेरी", "शर्म", "worthless"),
    "focus": ("focus", "concentrat", "attention", "mind blanks", "cannot focus", "can't focus", "harder to focus", "hard to focus", "get started", "taking longer to get started", "takes longer to get started", "mind taking longer", "mind feels slow", "screen", "ध्यान", "focus nahi", "ध्यान नहीं", "ध्यान नहीं टिक", "start hone mein time lagta", "start hone me time lagta", "mind ko start hone mein time lagta", "mind ko start hone me time lagta", "दिमाग धीमा"),
    "anxiety": ("worry", "restless", "tense", "panic", "loop", "बेचैनी", "चिंता", "घबराहट", "mind won't stop"),
    "safety": ("hurt myself", "not wake up", "suicide", "मर", "खुद को नुकसान", "zinda na"),
}

AFFECTIVE_TOPIC_FAMILY = {"mood", "sleep", "energy", "self_view", "focus"}
ANXIETY_CORE_ITEMS = {"gad_q1_nervous", "gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}


@dataclass(frozen=True)
class TopicNode:
    topic_id: str
    label: str
    item_ids: Tuple[str, ...]
    priority: int
    transitions: Tuple[str, ...]


TOPIC_GRAPH: Dict[str, TopicNode] = {
    "mood": TopicNode(
        topic_id="mood",
        label="Mood and interest",
        item_ids=("phq_q1_anhedonia", "phq_q2_low_mood"),
        priority=5,
        transitions=("sleep", "energy", "self_view", "focus", "anxiety", "safety"),
    ),
    "sleep": TopicNode(
        topic_id="sleep",
        label="Sleep",
        item_ids=("phq_q3_sleep",),
        priority=4,
        transitions=("energy", "focus", "mood", "anxiety"),
    ),
    "energy": TopicNode(
        topic_id="energy",
        label="Energy and appetite",
        item_ids=("phq_q4_fatigue", "phq_q5_appetite"),
        priority=3,
        transitions=("sleep", "mood", "focus"),
    ),
    "self_view": TopicNode(
        topic_id="self_view",
        label="Self-worth",
        item_ids=("phq_q6_worthlessness",),
        priority=4,
        transitions=("mood", "safety", "anxiety"),
    ),
    "focus": TopicNode(
        topic_id="focus",
        label="Focus and activation",
        item_ids=("phq_q7_concentration", "phq_q8_psychomotor"),
        priority=3,
        transitions=("sleep", "energy", "mood", "anxiety"),
    ),
    "anxiety": TopicNode(
        topic_id="anxiety",
        label="Worry and tension",
        item_ids=(
            "gad_q1_nervous",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
            "gad_q5_restlessness",
            "gad_q6_irritability",
            "gad_q7_fear_awful",
        ),
        priority=5,
        transitions=("sleep", "focus", "mood", "safety"),
    ),
    "safety": TopicNode(
        topic_id="safety",
        label="Safety",
        item_ids=("phq_q9_self_harm",),
        priority=6,
        transitions=("mood", "self_view", "summary"),
    ),
}

ITEM_TO_TOPIC = {
    item_id: node.topic_id
    for node in TOPIC_GRAPH.values()
    for item_id in node.item_ids
}


class DialoguePlanner:
    def _topic_label(self, topic: Optional[str], language: str) -> str:
        normalized = str(topic or "check_in").replace(" ", "_").lower()
        return TOPIC_LABELS.get(normalized, {}).get(language, str(topic or "check-in").replace("_", " "))

    def opening_prompt(self, language: str, profile=None) -> str:
        base = OPENING_PROMPTS[language]
        if profile is None:
            return base

        preferred_name = getattr(profile, "preferred_name", None)
        occupation = getattr(profile, "occupation", None)
        context_note = getattr(profile, "context_note", None)
        recent_checkins = getattr(profile, "recent_checkins", None) or []
        recent_topic = None
        if recent_checkins and isinstance(recent_checkins[0], dict):
            recent_topic = self._topic_label(recent_checkins[0].get("topic") or "check_in", language)
        if language == "en":
            if preferred_name and occupation:
                return f"Hi {preferred_name}. Thanks for being here. Before we go deeper, how have things been feeling lately in day-to-day life as a {occupation}?"
            if context_note:
                return f"Thanks for being here. Keeping {context_note} in mind, what has felt the heaviest over the last couple of weeks?"
            if recent_topic:
                return f"Welcome back. If this connects to your recent {recent_topic} check-in, tell me what feels similar or different today."
        if language == "hi":
            if preferred_name and occupation:
                return f"नमस्ते {preferred_name}। शुक्रिया। {occupation} के रूप में रोज़मर्रा की ज़िंदगी में पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?"
            if context_note:
                return f"शुक्रिया, आप यहाँ आए। {context_note} को ध्यान में रखते हुए पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?"
            if recent_topic:
                return f"फिर से स्वागत है। अगर यह आपकी हाल की {recent_topic} बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।"
        if language == "hinglish":
            if preferred_name and occupation:
                return f"Hi {preferred_name}. Thanks for being here. {occupation} wali day-to-day life mein pichhle do hafton mein sabse zyada kya heavy laga?"
            if context_note:
                return f"Thanks for joining. {context_note} ko dhyan mein rakhte hue pichhle do hafton mein sabse zyada kya heavy laga?"
            if recent_topic:
                return f"Welcome back. Agar yeh recent {recent_topic} check-in se connected lag raha hai, to batao aaj kya same hai aur kya different."
        return base

    def next_reply(self, snapshot: ScreeningSnapshot, session: ChatSession) -> Tuple[str, Optional[str]]:
        snapshot.coverage = self.build_plan(snapshot, session)
        plan = snapshot.coverage.dialogue
        language = session.language
        latest_user_text = self._latest_user_text(session)
        last_assistant_text = self._last_assistant_text(session)

        if snapshot.safety.level == "urgent" or plan.next_action == "handoff":
            return SAFETY_MESSAGES[language], plan.target_item
        if self._should_close_after_break_answer(session):
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        post_close_reply = self._post_close_followup_reply(session, latest_user_text, language)
        if post_close_reply is not None:
            return post_close_reply, None
        if self._should_break_after_relax_duration_answer(session):
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if self._should_close_anxiety_after_scope_answer(plan, session):
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        if self._should_break_after_anxiety_core_rotation(session):
            if self._already_used_segment(last_assistant_text, ANXIETY_LOOP_BREAK_PROMPTS[language]):
                return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if self._should_close_after_relax_duration_answer(session):
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        if self._should_use_anxiety_loop_break(plan, session):
            if self._already_used_segment(last_assistant_text, ANXIETY_LOOP_BREAK_PROMPTS[language]) or self._should_close_anxiety_loop(plan, session):
                return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if plan.next_action == "summarize":
            return CLOSING_MESSAGES[language], None
        if plan.stage == "rapport":
            targeted_prompt = self._build_prompt_for_target(language, plan, session)
            if targeted_prompt and self._should_use_targeted_rapport(plan, session):
                return self._compose_prompt(language, targeted_prompt, plan, session), plan.target_item
            return self._compose_prompt(language, RAPPORT_PROMPTS[language], plan, session), plan.target_item

        prompt = self._build_prompt_for_target(language, plan, session)
        if prompt:
            return self._compose_prompt(language, prompt, plan, session), plan.target_item
        return CLOSING_MESSAGES[language], None

    def _should_use_targeted_rapport(self, plan: DialoguePlan, session: ChatSession) -> bool:
        if not plan.target_item or plan.target_topic in {"rapport", "summary"}:
            return False
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return False
        words = len(latest_user_text.split())
        return words >= 6 or self._has_timing_or_frequency_answer(latest_user_text)

    def _should_use_anxiety_loop_break(self, plan: DialoguePlan, session: ChatSession) -> bool:
        if plan.target_topic != "anxiety":
            return False
        loop_items = {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}
        recent = session.asked_items[-5:]
        if len(recent) < 4:
            return False
        if sum(item in loop_items for item in recent) < 4:
            return False
        latest_user_text = self._latest_user_text(session)
        if self._has_new_anxiety_branch_detail(latest_user_text):
            return False
        repeated_target = recent.count(plan.target_item) >= 2 if plan.target_item else False
        short_latest = self._is_nonexpansive_followup(latest_user_text)
        repeated_timing = self._has_timing_or_frequency_answer(latest_user_text) and recent.count("gad_q3_excessive_worry") >= 2
        return repeated_target and (short_latest or repeated_timing)

    def _should_close_anxiety_loop(self, plan: DialoguePlan, session: ChatSession) -> bool:
        if plan.target_topic != "anxiety":
            return False
        latest_user_text = self._latest_user_text(session)
        if self._has_new_anxiety_branch_detail(latest_user_text):
            return False
        recent = session.asked_items[-5:]
        repeated_worry_probe = recent.count("gad_q3_excessive_worry") >= 2
        if plan.target_item == "gad_q3_excessive_worry" and repeated_worry_probe and self._is_nonexpansive_followup(latest_user_text):
            return True
        return False

    def _should_close_anxiety_after_scope_answer(self, plan: DialoguePlan, session: ChatSession) -> bool:
        if not session.asked_items:
            return False
        if session.asked_items[-1] != "gad_q3_excessive_worry":
            return False
        latest_user_text = self._latest_user_text(session)
        if not self._has_worry_scope_answer(latest_user_text):
            return False
        recent_anxiety_items = [
            item_id
            for item_id in session.asked_items[-5:]
            if ITEM_TO_TOPIC.get(item_id) == "anxiety"
        ]
        return len(set(recent_anxiety_items)) >= 2

    def _should_close_after_relax_duration_answer(self, session: ChatSession) -> bool:
        if not session.asked_items:
            return False
        if session.asked_items[-1] != "gad_q4_trouble_relaxing":
            return False
        if session.asked_items[-4:].count("gad_q4_trouble_relaxing") < 2:
            return False
        latest_user_text = self._latest_user_text(session)
        if not self._has_lingering_tension_signal(latest_user_text):
            return False
        recent_anxiety_items = {
            item_id
            for item_id in session.asked_items[-6:]
            if ITEM_TO_TOPIC.get(item_id) == "anxiety"
        }
        return "gad_q2_control_worry" in recent_anxiety_items and "gad_q3_excessive_worry" in recent_anxiety_items

    def _should_break_after_relax_duration_answer(self, session: ChatSession) -> bool:
        if not session.asked_items:
            return False
        if session.asked_items[-1] != "gad_q4_trouble_relaxing":
            return False
        last_assistant_text = self._last_assistant_text(session)
        if self._already_used_segment(last_assistant_text, ANXIETY_LOOP_BREAK_PROMPTS[session.language]):
            return False
        latest_user_text = self._latest_user_text(session)
        if not self._has_lingering_tension_signal(latest_user_text):
            return False
        recent_anxiety_items = {
            item_id
            for item_id in session.asked_items[-6:]
            if ITEM_TO_TOPIC.get(item_id) == "anxiety"
        }
        return "gad_q2_control_worry" in recent_anxiety_items and "gad_q3_excessive_worry" in recent_anxiety_items

    def _should_close_after_break_answer(self, session: ChatSession) -> bool:
        last_assistant_text = self._last_assistant_text(session)
        if not self._already_used_segment(last_assistant_text, ANXIETY_LOOP_BREAK_PROMPTS[session.language]):
            return False
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return False
        if self._is_close_acknowledgement(latest_user_text):
            return True
        if self._has_worry_scope_answer(latest_user_text):
            return True
        if self._has_worry_domain_signal(latest_user_text):
            return True
        if self._is_nonexpansive_followup(latest_user_text):
            return True
        return False

    def _recent_anxiety_core_items(self, session: ChatSession, lookback: int = 8) -> list[str]:
        return [item_id for item_id in session.asked_items[-lookback:] if item_id in ANXIETY_CORE_ITEMS]

    def _has_recent_anxiety_core_coverage(self, session: ChatSession) -> bool:
        recent_core = set(self._recent_anxiety_core_items(session))
        return {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}.issubset(recent_core)

    def _should_break_after_anxiety_core_rotation(self, session: ChatSession) -> bool:
        if not session.asked_items:
            return False
        if not self._has_recent_anxiety_core_coverage(session):
            return False
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return False
        last_item = session.asked_items[-1]
        if last_item not in ANXIETY_CORE_ITEMS:
            return False
        if self._has_high_priority_post_close_signal(latest_user_text):
            return False
        if self._has_timing_or_frequency_answer(latest_user_text):
            return False
        if self._has_worry_scope_answer(latest_user_text):
            return True
        if self._has_worry_domain_signal(latest_user_text) and last_item in {"gad_q1_nervous", "gad_q4_trouble_relaxing"}:
            return True
        if self._is_nonexpansive_followup(latest_user_text):
            return True
        if self._has_persistent_worry_signal(latest_user_text) and not self._has_worry_domain_signal(latest_user_text):
            return True
        return False

    def build_plan(self, snapshot: ScreeningSnapshot, session: ChatSession) -> CoveragePlan:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        held_back_items = self._held_back_items(snapshot, session)
        topic_states = self._build_topic_states(snapshot, held_back_items)
        current_topic = self._infer_current_topic(snapshot, session)
        low_confidence_topics = [
            topic.topic_id
            for topic in topic_states
            if topic.status in {"pending", "probing", "review"}
            and topic.topic_id != "safety"
        ]
        covered_topics = [topic.topic_id for topic in topic_states if topic.touched or topic.status == "stable"]
        user_style = self._infer_user_style(snapshot, session, topic_states)
        disclosure = self._build_disclosure_metrics(snapshot, session, topic_states)
        readiness = self._infer_readiness(snapshot, session, topic_states, user_style)
        fatigue = self._infer_fatigue(snapshot, session)
        stage = self._select_stage(snapshot, topic_states, len(user_turns), held_back_items, readiness, fatigue)
        target_topic = self._select_target_topic(
            snapshot,
            session,
            topic_states,
            current_topic,
            stage,
            held_back_items,
            user_style,
            readiness,
            fatigue,
        )
        target_item = self._select_target_item(snapshot, session, target_topic, held_back_items, fatigue, user_style)
        if target_item and ITEM_TO_TOPIC.get(target_item) and ITEM_TO_TOPIC.get(target_item) != target_topic:
            target_topic = ITEM_TO_TOPIC[target_item]
        next_items = self._rank_next_items(snapshot, session, target_topic, held_back_items, fatigue, user_style)
        review_items = [
            item_id
            for item_id, item in snapshot.items.items()
            if item.review_recommended or item.status in {"contradicted", "abstained"}
        ]
        reflective_anchor = self._build_reflective_anchor(session.language, target_topic, user_style, fatigue)
        continuity_note = self._build_continuity_note(session.language, session, target_topic)
        recommended_nudges = self._recommend_nudges(session, target_topic, user_style, stage, fatigue)
        dialogue = DialoguePlan(
            stage=stage,
            next_action=self._select_action(stage, target_topic, user_style, fatigue, readiness),
            current_topic=current_topic,
            target_topic=target_topic,
            target_item=target_item,
            rationale=self._build_rationale(snapshot, target_topic, topic_states, held_back_items),
            user_turns=len(user_turns),
            low_confidence_topics=low_confidence_topics,
            covered_topics=covered_topics,
            held_back_items=held_back_items,
            transition_hint=self._build_transition_hint(current_topic, target_topic, stage, user_style, fatigue, readiness),
            user_style=user_style,
            disclosure=disclosure,
            readiness=readiness,
            fatigue=fatigue,
            reflective_anchor=reflective_anchor,
            continuity_note=continuity_note,
            recommended_nudges=recommended_nudges,
        )
        return snapshot.coverage.model_copy(
            update={
                "next_items": next_items,
                "review_items": review_items,
                "review_required": snapshot.safety.needs_human_review or bool(review_items),
                "topic_states": topic_states,
                "dialogue": dialogue,
            }
        )

    def _infer_user_style(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        topic_states: list[TopicState],
    ) -> UserStyleProfile:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        if not user_turns:
            return UserStyleProfile(
                code_mix="high" if session.language == "hinglish" else "low",
                openness="cautious",
            )

        normalized_turns = [self._normalize(turn.text) for turn in user_turns]
        word_counts = [len(turn.text.split()) for turn in user_turns]
        avg_words = round(mean(word_counts), 1) if word_counts else 0.0
        detail_hits = sum(any(marker in text for marker in DETAIL_MARKERS) for text in normalized_turns)
        impact_hits = sum(any(marker in text for marker in IMPACT_MARKERS) for text in normalized_turns)
        hedge_hits = sum(any(marker in text for marker in HEDGE_MARKERS) for text in normalized_turns)
        explicit_feeling_hits = sum(
            any(token in text for token in ("i feel", "it feels", "mujhe", "lagta hai", "feel hota", "feel ho raha"))
            for text in normalized_turns
        )

        if avg_words < 8 and detail_hits == 0:
            verbosity = "brief"
        elif avg_words < 18 or detail_hits <= 1:
            verbosity = "balanced"
        else:
            verbosity = "detailed"

        code_mix = self._infer_code_mix(session.language, user_turns)

        touched_ratio = snapshot.coverage.touched_items / max(len(user_turns), 1)
        detail_ratio = (detail_hits + impact_hits + explicit_feeling_hits) / max(len(user_turns), 1)
        if hedge_hits >= max(1, len(user_turns) // 2) and detail_ratio < 1.2 and avg_words < 12:
            openness = "guarded"
        elif detail_ratio >= 1.5 or (avg_words >= 14 and explicit_feeling_hits >= 1):
            openness = "open"
        elif avg_words < 12 and touched_ratio < 1.1:
            openness = "cautious"
        else:
            openness = "cautious"

        distress_trend = self._distress_trend(snapshot, session)
        steering_preference = self._infer_steering_preference(
            avg_words=avg_words,
            openness=openness,
            touched_ratio=touched_ratio,
            detail_hits=detail_hits + impact_hits,
            user_turn_count=len(user_turns),
        )
        empathy_level = "high" if openness != "open" or distress_trend == "rising" or snapshot.safety.level != "none" else "moderate"
        return UserStyleProfile(
            avg_words_per_turn=avg_words,
            verbosity=verbosity,
            openness=openness,
            code_mix=code_mix,
            distress_trend=distress_trend,
            empathy_level=empathy_level,
            steering_preference=steering_preference,
        )

    def _build_disclosure_metrics(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        topic_states: list[TopicState],
    ) -> DisclosureMetrics:
        user_turns = len([turn for turn in session.turns if turn.speaker == "user"])
        stable_topics = len([topic for topic in topic_states if topic.status == "stable"])
        return DisclosureMetrics(
            user_turns=user_turns,
            touched_items=snapshot.coverage.touched_items,
            resolved_items=len(snapshot.coverage.resolved_items),
            stable_topics=stable_topics,
            items_per_user_turn=round(snapshot.coverage.touched_items / max(user_turns, 1), 2),
            resolved_per_user_turn=round(len(snapshot.coverage.resolved_items) / max(user_turns, 1), 2),
            nudge_effectiveness=round(self._recent_nudge_effectiveness(session), 2),
        )

    def _normalize(self, text: str) -> str:
        return " ".join(text.lower().split())

    def _infer_code_mix(self, language: str, user_turns: list) -> str:
        if language == "hinglish":
            return "high"

        mixed_script_turns = 0
        translit_turns = 0
        for turn in user_turns:
            text = turn.text
            normalized = self._normalize(text)
            has_devanagari = bool(DEVANAGARI_RE.search(text))
            latin_tokens = LATIN_TOKEN_RE.findall(text)
            has_english_context = any(token.lower() in ENGLISH_CONTEXT_MARKERS for token in latin_tokens)
            has_transliterated_hindi = any(marker in normalized for marker in TRANSLITERATED_HINDI_MARKERS)

            if has_devanagari and latin_tokens:
                mixed_script_turns += 1
            elif has_transliterated_hindi and has_english_context:
                translit_turns += 1

        if mixed_script_turns >= max(1, len(user_turns) // 2) or translit_turns >= max(1, len(user_turns) // 2):
            return "high"
        if mixed_script_turns or translit_turns:
            return "medium"
        return "low"

    def _infer_steering_preference(
        self,
        *,
        avg_words: float,
        openness: str,
        touched_ratio: float,
        detail_hits: int,
        user_turn_count: int,
    ) -> SteeringPreference:
        if openness == "guarded" or avg_words < 8:
            return "guided"
        if detail_hits >= 2 or (user_turn_count >= 2 and touched_ratio >= 1.4):
            return "user_led"
        return "balanced"

    def _infer_readiness(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        topic_states: list[TopicState],
        user_style: UserStyleProfile,
    ) -> ReadinessLevel:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        if len(user_turns) <= 1:
            return "opening"

        stable_topics = len([topic for topic in topic_states if topic.status == "stable" and topic.topic_id != "safety"])
        recent_text = " ".join(self._normalize(turn.text) for turn in user_turns[-2:])
        closure_signal = any(marker in recent_text for marker in CLOSURE_MARKERS)
        completion = snapshot.coverage.completion_ratio

        if completion >= 0.62 and (closure_signal or stable_topics >= 3 or user_style.steering_preference == "guided"):
            return "ready_to_close"
        if completion >= 0.42 or stable_topics >= 2:
            return "steady"
        return "building"

    def _infer_fatigue(self, snapshot: ScreeningSnapshot, session: ChatSession) -> FatigueLevel:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        if len(user_turns) < 2:
            return "low"

        normalized_recent = [self._normalize(turn.text) for turn in user_turns[-3:]]
        recent_word_counts = [len(turn.text.split()) for turn in user_turns[-3:]]
        shrinking = len(recent_word_counts) >= 2 and recent_word_counts[-1] <= max(4, int(recent_word_counts[0] * 0.6))
        fatigue_signal = any(any(marker in text for marker in FATIGUE_MARKERS) for text in normalized_recent)
        repeated_items = len(session.asked_items[-3:]) != len(set(session.asked_items[-3:]))
        unhelpful_nudges = len([event for event in session.nudge_events[-2:] if event.outcome == "unhelpful"])

        if fatigue_signal or (shrinking and repeated_items) or unhelpful_nudges >= 2:
            return "high"
        if shrinking or len(user_turns) >= 4 or snapshot.coverage.completion_ratio >= 0.45:
            return "medium"
        return "low"

    def _recent_nudge_effectiveness(self, session: ChatSession) -> float:
        if not session.nudge_events:
            return 0.0
        window = session.nudge_events[-3:]
        if not window:
            return 0.0
        score = 0.0
        for event in window:
            if event.outcome == "helpful":
                score += 1.0
            elif event.outcome == "unhelpful":
                score -= 1.0
        return score / len(window)

    def _build_topic_states(self, snapshot: ScreeningSnapshot, held_back_items: Iterable[str]) -> list[TopicState]:
        held_back = set(held_back_items)
        topic_states: list[TopicState] = []
        for node in TOPIC_GRAPH.values():
            items = [snapshot.items[item_id] for item_id in node.item_ids]
            weights = [max(ITEM_INDEX[item.item_id].priority, 1) for item in items]
            weighted_total = sum(item.confidence * weight for item, weight in zip(items, weights))
            total_weight = sum(weights) or 1
            resolved_items = [item.item_id for item in items if item.status == "resolved"]
            unresolved_items = [item.item_id for item in items if item.status != "resolved" and item.item_id not in held_back]
            review_items = [
                item.item_id
                for item in items
                if item.review_recommended or item.status in {"contradicted", "abstained"}
            ]
            touched = any(item.evidence_span_ids for item in items)
            topic_states.append(
                TopicState(
                    topic_id=node.topic_id,
                    label=node.label,
                    item_ids=list(node.item_ids),
                    touched=touched,
                    priority=node.priority,
                    confidence=round(weighted_total / total_weight, 2),
                    status=self._topic_status(node.topic_id, touched, unresolved_items, review_items, held_back),
                    resolved_items=resolved_items,
                    unresolved_items=unresolved_items,
                    review_items=review_items,
                )
            )
        return topic_states

    def _topic_status(
        self,
        topic_id: str,
        touched: bool,
        unresolved_items: list[str],
        review_items: list[str],
        held_back_items: set[str],
    ) -> str:
        if any(item_id in held_back_items for item_id in TOPIC_GRAPH[topic_id].item_ids):
            return "held_back"
        if review_items:
            return "review"
        if not unresolved_items:
            return "stable"
        if touched:
            return "probing"
        return "pending"

    def _select_stage(
        self,
        snapshot: ScreeningSnapshot,
        topic_states: list[TopicState],
        user_turn_count: int,
        held_back_items: list[str],
        readiness: ReadinessLevel,
        fatigue: FatigueLevel,
    ) -> str:
        if snapshot.safety.level == "urgent":
            return "safety"
        if snapshot.safety.level == "review" and "phq_q9_self_harm" not in held_back_items:
            return "safety"
        if user_turn_count == 1 and snapshot.coverage.touched_items >= 1:
            return "clarification"
        if user_turn_count <= 1 and snapshot.coverage.touched_items < 3:
            return "rapport"
        if any(topic.status in {"review", "probing"} for topic in topic_states if topic.topic_id != "safety"):
            return "clarification"
        stable_topics = [topic for topic in topic_states if topic.status == "stable" and topic.topic_id != "safety"]
        if readiness == "ready_to_close":
            return "summary"
        if fatigue == "high" and snapshot.coverage.completion_ratio >= 0.45:
            return "clarification"
        if snapshot.coverage.completion_ratio >= 0.72 or len(stable_topics) >= 4:
            return "summary"
        return "exploration"

    def _select_target_topic(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        topic_states: list[TopicState],
        current_topic: str,
        stage: str,
        held_back_items: list[str],
        user_style: UserStyleProfile,
        readiness: ReadinessLevel,
        fatigue: FatigueLevel,
    ) -> str:
        continuity_item = self._continuity_item(snapshot, session, held_back_items, fatigue)
        if continuity_item:
            return ITEM_TO_TOPIC.get(continuity_item, current_topic)
        if stage == "safety":
            return "safety"
        if stage == "summary":
            return current_topic if current_topic in TOPIC_GRAPH else "mood"
        latest_signal_topics = self._latest_signal_topics(session)
        latest_signal_items = self._latest_signal_items(session)
        recent_signal_topics = self._recent_signal_topics(session)

        latest_user_text = self._latest_user_text(session)
        if current_topic == "anxiety" and self._has_sleep_choice_signal(latest_user_text):
            return "sleep"
        if current_topic == "sleep" and "gad_q4_trouble_relaxing" in latest_signal_items:
            return "anxiety"

        if stage == "rapport":
            touched_candidates = [
                topic
                for topic in topic_states
                if topic.topic_id != "safety" and topic.touched and topic.unresolved_items
            ]
            if touched_candidates:
                return max(
                    touched_candidates,
                    key=lambda topic: (
                        topic.topic_id == current_topic,
                        topic.status == "probing",
                        self._topic_coverage_boost(snapshot, topic.topic_id),
                        topic.priority,
                        1.0 - topic.confidence,
                    ),
                ).topic_id
            signal_candidates = [
                topic
                for topic in topic_states
                if topic.topic_id in latest_signal_topics and topic.topic_id != "safety"
            ]
            if signal_candidates:
                preferred_signal = max(
                    signal_candidates,
                    key=lambda topic: (
                        topic.topic_id == "mood" and "self_view" in latest_signal_topics and "phq_q6_worthlessness" in held_back_items,
                        topic.priority,
                        topic.topic_id == current_topic,
                    ),
                )
                if preferred_signal.topic_id == "self_view" and "phq_q6_worthlessness" in held_back_items:
                    return "mood"
                return preferred_signal.topic_id

        held_back = set(held_back_items)
        candidates = [
            topic
            for topic in topic_states
            if topic.unresolved_items or topic.review_items
            if not (topic.topic_id == "safety" and snapshot.safety.level == "none")
        ]
        if not candidates:
            return current_topic if current_topic in TOPIC_GRAPH else "mood"

        recent_topics = [ITEM_TO_TOPIC.get(item_id) for item_id in session.asked_items[-3:] if ITEM_TO_TOPIC.get(item_id)]
        affective_signal_active = bool((latest_signal_topics | recent_signal_topics) & AFFECTIVE_TOPIC_FAMILY)
        anxiety_signal_active = "anxiety" in latest_signal_topics

        def rank(topic: TopicState) -> tuple[int, float]:
            score = topic.priority * 10
            score += int((len(topic.unresolved_items) / max(len(topic.item_ids), 1)) * 10)
            score += self._topic_coverage_boost(snapshot, topic.topic_id) * 2
            if topic.status == "review":
                score += 20
            elif topic.status == "probing":
                score += 14
            else:
                score += 8
            if topic.touched:
                score += 8
            if topic.touched and topic.confidence < 0.62:
                score += 6
            if topic.topic_id == current_topic:
                score += 4
            if current_topic in TOPIC_GRAPH and topic.topic_id in TOPIC_GRAPH[current_topic].transitions:
                score += 3
            if recent_topics.count(topic.topic_id) >= 2:
                score -= 10 if fatigue != "low" else 4
            if fatigue == "high" and topic.topic_id == current_topic:
                score -= 8
            if readiness == "ready_to_close" and topic.topic_id != current_topic:
                score -= 10
            if user_style.steering_preference == "user_led" and topic.topic_id == current_topic and topic.touched:
                score += 8
            if user_style.steering_preference == "guided" and not topic.touched:
                score += 4
            if topic.topic_id in latest_signal_topics:
                score += 18
            elif topic.topic_id in recent_signal_topics:
                score += 8
            if (
                current_topic in AFFECTIVE_TOPIC_FAMILY
                and recent_topics
                and recent_topics[-1] == current_topic
                and not anxiety_signal_active
                and "anxiety" not in recent_signal_topics
            ):
                if topic.topic_id == current_topic:
                    score += 8
                elif topic.topic_id == "anxiety":
                    score -= 18
            if current_topic in AFFECTIVE_TOPIC_FAMILY and affective_signal_active and not anxiety_signal_active:
                if topic.topic_id in AFFECTIVE_TOPIC_FAMILY:
                    score += 16
                if topic.topic_id == current_topic:
                    score += 8
                if topic.topic_id == "anxiety":
                    score -= 18
            if current_topic == "anxiety" and anxiety_signal_active:
                if topic.topic_id == "anxiety":
                    score += 10
                elif topic.topic_id in AFFECTIVE_TOPIC_FAMILY:
                    score -= 4
            if topic.topic_id == "safety" and "phq_q9_self_harm" in held_back:
                score -= 40
            if topic.topic_id == "safety" and snapshot.safety.level == "none":
                score -= 8
            return score, 1.0 - topic.confidence

        return max(candidates, key=rank).topic_id

    def _select_target_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> Optional[str]:
        directed_followup = self._directed_followup_item(snapshot, session, target_topic, held_back_items)
        if directed_followup:
            return directed_followup
        continuity_item = self._continuity_item(snapshot, session, held_back_items, fatigue)
        if continuity_item and ITEM_TO_TOPIC.get(continuity_item) == target_topic:
            return continuity_item
        if target_topic not in TOPIC_GRAPH:
            return None

        held_back = set(held_back_items)
        latest_user_text = self._latest_user_text(session)
        if (
            self._has_self_view_signal(latest_user_text)
            and "phq_q6_worthlessness" not in held_back
            and snapshot.items["phq_q6_worthlessness"].status != "resolved"
        ):
            return "phq_q6_worthlessness"
        candidates = [
            item_id
            for item_id in TOPIC_GRAPH[target_topic].item_ids
            if item_id not in held_back and snapshot.items[item_id].status != "resolved"
        ]
        if not candidates:
            return None
        latest_signal_items = self._latest_signal_items(session)
        if latest_signal_items:
            signaled_candidates = [item_id for item_id in candidates if item_id in latest_signal_items]
            if signaled_candidates and (
                not session.asked_items
                or not self._has_timing_or_frequency_answer(self._latest_user_text(session))
            ):
                return max(
                    signaled_candidates,
                    key=lambda item_id: self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style),
                )
        return max(candidates, key=lambda item_id: self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style))

    def _directed_followup_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
    ) -> Optional[str]:
        if not session.asked_items:
            return None
        last_item = session.asked_items[-1]
        latest_user_text = self._latest_user_text(session)
        held_back = set(held_back_items)
        recent_signal_items = self._recent_signal_items(session)
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)

        def available(item_id: str) -> bool:
            return (
                item_id not in held_back
                and item_id in snapshot.items
                and snapshot.items[item_id].status != "resolved"
            )

        if last_item in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"}:
            if (
                last_item == "phq_q2_low_mood"
                and session.asked_items.count("phq_q2_low_mood") >= 2
                and self._has_functional_impact_answer(latest_user_text)
                and available("phq_q7_concentration")
            ):
                return "phq_q7_concentration"
            if (
                last_item == "phq_q2_low_mood"
                and self._has_flat_functioning_signal(latest_user_text)
                and available("phq_q2_low_mood")
            ):
                return "phq_q2_low_mood"
            if (
                last_item == "phq_q2_low_mood"
                and session.asked_items[-4:].count("phq_q2_low_mood") >= 3
                and self._has_flat_functioning_signal(latest_user_text)
                and available("phq_q7_concentration")
            ):
                return "phq_q7_concentration"
            if self._has_self_view_signal(latest_user_text) and available("phq_q6_worthlessness"):
                return "phq_q6_worthlessness"
            if "phq_q7_concentration" in latest_signal_items and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if (
                last_item == "phq_q1_anhedonia"
                and not self._has_timing_or_frequency_answer(latest_user_text)
                and self._has_anhedonia_signal(latest_user_text)
                and available("phq_q2_low_mood")
            ):
                return "phq_q2_low_mood"
            if session.asked_items[-3:].count("phq_q1_anhedonia") >= 2 and available("phq_q2_low_mood"):
                return "phq_q2_low_mood"
            if (
                last_item == "phq_q2_low_mood"
                and session.asked_items.count("phq_q1_anhedonia") >= 1
                and not self._has_timing_or_frequency_answer(latest_user_text)
                and self._has_anhedonia_signal(latest_user_text)
                and available("phq_q2_low_mood")
            ):
                return "phq_q2_low_mood"
            if last_item != "phq_q1_anhedonia" and "phq_q1_anhedonia" in latest_signal_items and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"
            if last_item != "phq_q2_low_mood" and "phq_q2_low_mood" in latest_signal_items and available("phq_q2_low_mood"):
                return "phq_q2_low_mood"
            if target_topic == "focus" and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if target_topic == "mood" and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"

        if last_item == "phq_q7_concentration":
            if self._has_concentration_answer(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if self._has_activation_signal(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "phq_q4_fatigue" in recent_signal_items and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "phq_q7_concentration" in recent_signal_items and available("phq_q7_concentration") and not self._has_concentration_answer(latest_user_text):
                return "phq_q7_concentration"
            if "energy" in latest_signal_topics and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "focus" in latest_signal_topics and available("phq_q7_concentration") and not self._has_concentration_answer(latest_user_text):
                return "phq_q7_concentration"
            if target_topic == "focus" and available("phq_q7_concentration") and not self._has_concentration_answer(latest_user_text):
                return "phq_q7_concentration"
            if target_topic == "energy" and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"

        if last_item == "phq_q4_fatigue":
            if self._has_timing_or_frequency_answer(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if self._has_activation_signal(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "phq_q4_fatigue" in latest_signal_items and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "energy" in latest_signal_topics and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"

        if last_item == "gad_q2_control_worry" and target_topic == "anxiety":
            if self._has_worry_domain_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if "phq_q3_sleep" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if "gad_q4_trouble_relaxing" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if "gad_q5_restlessness" in recent_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if self._has_awful_outcome_signal(latest_user_text) and available("gad_q7_fear_awful"):
                return "gad_q7_fear_awful"
            if self._has_persistent_worry_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"

        if last_item == "gad_q3_excessive_worry":
            if self._has_worry_domain_signal(latest_user_text) and session.asked_items.count("gad_q2_control_worry") >= 1:
                if available("gad_q4_trouble_relaxing"):
                    return "gad_q4_trouble_relaxing"
            if self._has_worry_scope_answer(latest_user_text) and session.asked_items.count("gad_q2_control_worry") >= 1:
                if available("gad_q4_trouble_relaxing"):
                    return "gad_q4_trouble_relaxing"

        if last_item == "gad_q5_restlessness":
            if self._has_timing_or_frequency_answer(latest_user_text):
                return last_item
            if "gad_q4_trouble_relaxing" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"

        if last_item == "gad_q4_trouble_relaxing":
            recent_relax_count = session.asked_items[-3:].count("gad_q4_trouble_relaxing")
            if (
                recent_relax_count >= 2
                and self._has_lingering_tension_signal(latest_user_text)
                and session.asked_items.count("gad_q2_control_worry") >= 1
                and session.asked_items.count("gad_q3_excessive_worry") >= 1
            ):
                return None
            if self._has_worry_scope_answer(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if self._has_worry_domain_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if recent_relax_count >= 2 and self._has_persistent_worry_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if recent_relax_count >= 3 and self._has_timing_or_frequency_answer(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if recent_relax_count >= 2 and not self._has_timing_or_frequency_answer(latest_user_text) and available("gad_q2_control_worry"):
                return "gad_q2_control_worry"

        if last_item == "gad_q7_fear_awful":
            if self._has_worry_domain_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if session.asked_items[-2:].count("gad_q7_fear_awful") >= 1 and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"

        if not self._has_timing_or_frequency_answer(latest_user_text):
            return None

        if last_item == "gad_q2_control_worry" and target_topic == "anxiety":
            if "gad_q5_restlessness" in recent_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if "gad_q4_trouble_relaxing" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if available("gad_q5_restlessness"):
                return "gad_q5_restlessness"

        if last_item == "phq_q3_sleep":
            if (
                "gad_q4_trouble_relaxing" in latest_signal_items
                and not self._has_sleep_pattern_answer(latest_user_text)
                and not self._has_timing_or_frequency_answer(latest_user_text)
                and available("gad_q4_trouble_relaxing")
            ):
                return "gad_q4_trouble_relaxing"
            if self._has_sleep_impact_signal(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if self._has_frequency_answer(latest_user_text) and self._recent_sleep_pattern_known(session):
                if available("phq_q4_fatigue"):
                    return "phq_q4_fatigue"
            if self._has_sleep_pattern_answer(latest_user_text):
                return last_item
            if snapshot.items[last_item].status != "resolved":
                return last_item
            if target_topic == "focus" and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if "phq_q7_concentration" in recent_signal_items and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if available("phq_q4_fatigue"):
                return "phq_q4_fatigue"

        return None

    def _rank_next_items(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> list[str]:
        held_back = set(held_back_items)
        unresolved = [
            item_id
            for item_id, item in snapshot.items.items()
            if item.status in {"unresolved", "partial", "contradicted", "abstained"} and item_id not in held_back
        ]
        unresolved.sort(
            key=lambda item_id: (
                ITEM_TO_TOPIC.get(item_id) != target_topic,
                -self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style),
            )
        )
        return unresolved[:5]

    def _infer_current_topic(self, snapshot: ScreeningSnapshot, session: ChatSession) -> str:
        if session.asked_items:
            last_item = session.asked_items[-1]
            if last_item in ITEM_TO_TOPIC:
                return ITEM_TO_TOPIC[last_item]
        if snapshot.evidence_spans:
            last_span = max(snapshot.evidence_spans, key=lambda span: (span.turn_id, span.span_id))
            return ITEM_TO_TOPIC.get(last_span.item_id, "rapport")
        return "rapport"

    def _select_action(
        self,
        stage: str,
        target_topic: str,
        user_style: UserStyleProfile,
        fatigue: FatigueLevel,
        readiness: ReadinessLevel,
    ) -> str:
        if stage == "safety":
            return "risk_check" if target_topic == "safety" else "handoff"
        if stage == "summary":
            return "summarize"
        if stage == "rapport":
            return "open_question"
        if fatigue == "high" or readiness == "ready_to_close":
            return "clarify"
        if target_topic in {"self_view", "safety"}:
            return "reflect"
        if user_style.steering_preference == "user_led" and target_topic in {"mood", "anxiety", "sleep"}:
            return "open_question"
        return "clarify" if target_topic in {"mood", "anxiety", "sleep"} else "symptom_probe"

    def _build_rationale(
        self,
        snapshot: ScreeningSnapshot,
        target_topic: str,
        topic_states: list[TopicState],
        held_back_items: list[str],
    ) -> str:
        topic_lookup = {topic.topic_id: topic for topic in topic_states}
        if snapshot.safety.level == "urgent":
            return "Safety escalation overrides normal screening."
        if target_topic == "safety":
            return "Safety cues or mood-linked risk signals justify a direct safety check."
        topic = topic_lookup.get(target_topic)
        if topic is None:
            return "Conversation is ready for a brief summary."
        if topic.review_items:
            return f"{topic.label} contains conflicting evidence and needs clarification."
        if topic.touched:
            return f"{topic.label} already has partial evidence, so the next turn should stabilize confidence."
        if held_back_items and target_topic != "safety":
            return f"{topic.label} is the best next branch while sensitive safety questions remain held back."
        return f"{topic.label} is still under-covered and should be explored next."

    def _build_transition_hint(
        self,
        current_topic: str,
        target_topic: str,
        stage: str,
        user_style: UserStyleProfile,
        fatigue: FatigueLevel,
        readiness: ReadinessLevel,
    ) -> str:
        if stage == "rapport":
            return "Acknowledge the opening concern, then narrow gently into the first likely symptom area."
        if stage == "summary":
            return "Reflect briefly, then summarize instead of opening a new branch."
        if readiness == "ready_to_close":
            return "Check whether one last clarification is needed, then start closing the loop."
        if fatigue == "high":
            return "Keep the bridge short and lower the burden with one concrete choice."
        if current_topic == target_topic:
            return f"Stay with {target_topic} and stabilize confidence before moving on."
        if user_style.openness == "guarded":
            return f"Use a gentle bridge from {current_topic} to {target_topic} and offer an easier choice-based answer."
        if user_style.steering_preference == "user_led":
            return f"Bridge from {current_topic} to {target_topic} by following the user's own wording before tightening the question."
        return f"Bridge naturally from {current_topic} to {target_topic} by connecting the last symptom to its daily impact."

    def _topic_coverage_boost(self, snapshot: ScreeningSnapshot, topic_id: str) -> int:
        return sum(UNDERCOVERED_ITEM_BOOSTS.get(item_id, 0) for item_id in TOPIC_GRAPH[topic_id].item_ids if snapshot.items[item_id].status != "resolved")

    def _item_priority_score(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        item_id: str,
        target_topic: Optional[str] = None,
        fatigue: FatigueLevel = "low",
        user_style: Optional[UserStyleProfile] = None,
    ) -> int:
        item = snapshot.items[item_id]
        score = ITEM_INDEX[item_id].priority * 10
        score += UNDERCOVERED_ITEM_BOOSTS.get(item_id, 0) * 6
        score += int((1.0 - item.confidence) * 12)
        latest_signal_items = self._latest_signal_items(session)
        recent_signal_items = self._recent_signal_items(session)

        if item.status == "contradicted":
            score += 28
        elif item.status == "abstained":
            score += 24
        elif item.status == "partial":
            score += 18
        elif item.status == "unresolved":
            score += 12

        if item.evidence_span_ids and item.status != "resolved":
            score += 6
        if item_id in session.asked_items:
            if item.status in {"contradicted", "abstained"}:
                score += 6
            elif item.status == "partial":
                score += 2
            else:
                score -= 8
        recent_repeat_count = session.asked_items[-3:].count(item_id)
        if recent_repeat_count:
            score -= 10 if fatigue == "low" else 16
        if recent_repeat_count >= 2:
            score -= 12
        if session.asked_items[-1:] == [item_id]:
            score -= 8 if item.status in {"partial", "contradicted", "abstained"} else 16
        if target_topic and ITEM_TO_TOPIC.get(item_id) == target_topic:
            score += 12
        if item.review_recommended:
            score += 10
        if user_style and user_style.steering_preference == "user_led" and target_topic and ITEM_TO_TOPIC.get(item_id) != target_topic:
            score -= 4
        if item_id in latest_signal_items:
            score += 18
        elif item_id in recent_signal_items:
            score += 8
        latest_user_text = self._latest_user_text(session)
        if item_id == "gad_q3_excessive_worry" and self._has_worry_domain_signal(latest_user_text):
            score += 14
        if item_id == "gad_q7_fear_awful" and not self._has_awful_outcome_signal(latest_user_text):
            score -= 14
        if session.asked_items[-1:] == [item_id] and self._has_timing_or_frequency_answer(self._latest_user_text(session)):
            prompt_bank = ITEM_FOLLOW_UPS.get(item_id, {})
            has_distinct_variant = (
                "frequency_known" in prompt_bank
                or "timing_known" in prompt_bank
            )
            if not has_distinct_variant or item_id == "gad_q2_control_worry":
                score -= 18
        return score

    def _held_back_items(self, snapshot: ScreeningSnapshot, session: ChatSession) -> list[str]:
        held_back: list[str] = []
        for item_id in SENSITIVE_ITEM_IDS:
            if self._hold_back_sensitive_item(item_id, snapshot, session):
                held_back.append(item_id)
        return held_back

    def _hold_back_sensitive_item(self, item_id: str, snapshot: ScreeningSnapshot, session: ChatSession) -> bool:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        latest_user_text = self._latest_user_text(session)
        if snapshot.safety.level == "urgent":
            return False
        if item_id == "phq_q9_self_harm" and snapshot.safety.level == "review" and (
            self._has_explicit_safety_signal(snapshot) or self._has_disappearance_safety_signal(snapshot)
        ):
            return False
        mood_signal = any(
            snapshot.items[key].value is not None and snapshot.items[key].value >= 2
            for key in ("phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness")
        )
        self_view_signal = self._has_self_view_signal(latest_user_text)
        if item_id == "phq_q9_self_harm":
            return len(user_turns) < 3 and not mood_signal
        if item_id == "phq_q6_worthlessness":
            return len(user_turns) < 2 and not (mood_signal or self_view_signal or snapshot.safety.level == "review")
        if item_id == "gad_q7_fear_awful":
            return len(user_turns) < 2 and snapshot.coverage.touched_items < 3
        return False

    def _has_explicit_safety_signal(self, snapshot: ScreeningSnapshot) -> bool:
        safety_text = " ".join(snapshot.safety.cues + ([snapshot.safety.rationale] if snapshot.safety.rationale else []))
        normalized = safety_text.lower()
        direct_markers = (
            "self-harm",
            "hurt yourself",
            "hurt myself",
            "kill myself",
            "suicide",
            "not wanting to be alive",
            "not be alive",
            "end my life",
            "end it all",
        )
        return any(marker in normalized for marker in direct_markers)

    def _has_disappearance_safety_signal(self, snapshot: ScreeningSnapshot) -> bool:
        normalized = " ".join(snapshot.safety.cues).lower()
        markers = (
            "disappear",
            "vanish",
            "not being here",
            "gayab",
            "गायब",
        )
        return any(marker in normalized for marker in markers)

    def _compose_prompt(
        self,
        language: str,
        base_prompt: str,
        plan: DialoguePlan,
        session: Optional[ChatSession] = None,
    ) -> str:
        prefix = REFLECTION_PREFIXES[language][plan.user_style.empathy_level]
        specific_reflection = self._build_specific_reflection(language, plan, session)
        suffix = self._style_suffix(language, plan)
        last_assistant_text = self._last_assistant_text(session)
        contextual_bridge = self._is_contextual_bridge_prompt(base_prompt)
        repeated_topic_probe = (
            plan.user_turns >= 2
            and plan.stage in {"clarification", "exploration"}
            and plan.current_topic == plan.target_topic
        )
        parts = []
        support_line = ""
        continuity_ready = bool(
            plan.continuity_note
            and plan.user_turns >= 2
            and plan.stage != "rapport"
            and plan.target_topic not in {"rapport", "safety"}
            and plan.current_topic == plan.target_topic
        )
        if continuity_ready and plan.user_style.steering_preference != "guided":
            support_line = plan.continuity_note
        elif plan.reflective_anchor and plan.stage != "rapport":
            support_line = plan.reflective_anchor
        elif continuity_ready:
            support_line = plan.continuity_note
        if support_line == plan.continuity_note and self._assistant_history_contains(session, plan.continuity_note):
            support_line = ""
        latest_user_text = self._latest_user_text(session) if session else ""
        if repeated_topic_probe and self._has_timing_or_frequency_answer(latest_user_text):
            support_line = ""
        if contextual_bridge:
            support_line = ""
        if self._already_used_segment(last_assistant_text, support_line):
            support_line = ""
        if (
            specific_reflection
            and not repeated_topic_probe
            and not self._already_used_segment(last_assistant_text, specific_reflection)
            and (plan.stage == "rapport" or not support_line)
            and not contextual_bridge
        ):
            prefix = specific_reflection
        use_prefix = (
            prefix
            and not repeated_topic_probe
            and not self._already_used_segment(last_assistant_text, prefix)
            and (not support_line or plan.stage == "rapport")
            and not contextual_bridge
        )
        if contextual_bridge or repeated_topic_probe:
            suffix = ""
        if self._already_used_segment(last_assistant_text, suffix):
            suffix = ""
        if use_prefix:
            parts.append(prefix)
        if support_line:
            parts.append(support_line)
        parts.append(base_prompt)
        if suffix:
            parts.append(suffix)
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _build_specific_reflection(
        self,
        language: str,
        plan: DialoguePlan,
        session: Optional[ChatSession],
    ) -> str:
        if session is None:
            return ""
        latest_user_text = self._latest_user_text(session)
        contextual_reflection = self._build_contextual_reflection(language, plan.target_item, latest_user_text)
        if contextual_reflection:
            return contextual_reflection
        latest_signal_items = self._latest_signal_items(session)
        if plan.target_item in ITEM_REFLECTIONS:
            return ITEM_REFLECTIONS[plan.target_item][language]
        for item_id in latest_signal_items:
            if item_id in ITEM_REFLECTIONS:
                return ITEM_REFLECTIONS[item_id][language]
        if plan.target_topic in TOPIC_REFLECTIONS:
            return TOPIC_REFLECTIONS[plan.target_topic][language]
        return ""

    def _build_prompt_for_target(self, language: str, plan: DialoguePlan, session: ChatSession) -> Optional[str]:
        item_prompt = self._build_item_prompt(language, plan, session)
        if item_prompt:
            return item_prompt
        return TOPIC_PROMPTS.get(plan.target_topic, {}).get(language)

    def _build_item_prompt(self, language: str, plan: DialoguePlan, session: ChatSession) -> Optional[str]:
        if not plan.target_item:
            return None
        prompt_bank = ITEM_FOLLOW_UPS.get(plan.target_item)
        if not prompt_bank:
            return None

        latest_user_text = self._latest_user_text(session)
        recent_repeat = session.asked_items[-1:] == [plan.target_item]
        recent_repeat_window = plan.target_item in session.asked_items[-3:]
        repeat_count = session.asked_items[-4:].count(plan.target_item)
        has_timing = self._has_timing_answer(latest_user_text)
        has_frequency = self._has_frequency_answer(latest_user_text)
        last_item = session.asked_items[-1] if session.asked_items else None
        if plan.target_item == "gad_q4_trouble_relaxing" and last_item in {"gad_q2_control_worry", "gad_q3_excessive_worry"}:
            if self._has_single_issue_scope_answer(latest_user_text) and "single_issue_known" in prompt_bank:
                return prompt_bank["single_issue_known"][language]
            if self._has_worry_domain_signal(latest_user_text) and "domain_known" in prompt_bank:
                return prompt_bank["domain_known"][language]
        if plan.target_item == "phq_q2_low_mood":
            if repeat_count >= 1 and self._has_flat_functioning_signal(latest_user_text) and "functional_impact" in prompt_bank:
                return prompt_bank["functional_impact"][language]
        if plan.target_item == "phq_q3_sleep":
            if recent_repeat_window and self._has_sleep_pattern_answer(latest_user_text) and "pattern_known" in prompt_bank:
                return prompt_bank["pattern_known"][language]
            if recent_repeat_window and has_frequency and self._recent_sleep_pattern_known(session) and "pattern_and_frequency_known" in prompt_bank:
                return prompt_bank["pattern_and_frequency_known"][language]

        if recent_repeat and has_timing and "timing_known" in prompt_bank:
            return prompt_bank["timing_known"][language]
        if recent_repeat and has_frequency and "frequency_known" in prompt_bank:
            return prompt_bank["frequency_known"][language]
        if repeat_count >= 2 and not (has_timing or has_frequency) and "deepening_probe" in prompt_bank:
            return prompt_bank["deepening_probe"][language]
        if recent_repeat_window and not (has_timing or has_frequency) and "repeat_probe" in prompt_bank:
            return prompt_bank["repeat_probe"][language]
        return prompt_bank.get("default", {}).get(language)

    def _latest_user_text(self, session: ChatSession) -> str:
        for turn in reversed(session.turns):
            if turn.speaker == "user":
                return self._normalize(turn.text)
        return ""

    def _latest_signal_topics(self, session: ChatSession) -> set[str]:
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return set()
        topics = {
            topic_id
            for topic_id, markers in TOPIC_SIGNAL_MARKERS.items()
            if any(marker in latest_user_text for marker in markers)
        }
        return topics

    def _recent_signal_topics(self, session: ChatSession, lookback: int = 3) -> set[str]:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        if not user_turns:
            return set()
        joined = " ".join(user_turns)
        return {
            topic_id
            for topic_id, markers in TOPIC_SIGNAL_MARKERS.items()
            if any(marker in joined for marker in markers)
        }

    def _latest_signal_items(self, session: ChatSession) -> set[str]:
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return set()
        return {
            item_id
            for item_id, markers in ITEM_SIGNAL_MARKERS.items()
            if any(marker in latest_user_text for marker in markers)
        }

    def _recent_signal_items(self, session: ChatSession, lookback: int = 3) -> set[str]:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        if not user_turns:
            return set()
        joined = " ".join(user_turns)
        return {
            item_id
            for item_id, markers in ITEM_SIGNAL_MARKERS.items()
            if any(marker in joined for marker in markers)
        }

    def _last_assistant_text(self, session: Optional[ChatSession]) -> str:
        if session is None:
            return ""
        for turn in reversed(session.turns):
            if turn.speaker == "assistant":
                return self._normalize(turn.text)
        return ""

    def _assistant_history_contains(
        self,
        session: Optional[ChatSession],
        segment: str,
        *,
        exclude_latest: bool = False,
    ) -> bool:
        if session is None or not segment:
            return False
        normalized_segment = self._normalize(segment)
        if not normalized_segment:
            return False
        assistant_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "assistant"]
        if exclude_latest and assistant_turns:
            assistant_turns = assistant_turns[:-1]
        return any(normalized_segment in turn for turn in assistant_turns)

    def _already_used_segment(self, normalized_last_assistant: str, segment: str) -> bool:
        if not normalized_last_assistant or not segment:
            return False
        normalized_segment = self._normalize(segment)
        if not normalized_segment:
            return False
        return normalized_segment in normalized_last_assistant

    def _is_contextual_bridge_prompt(self, prompt: str) -> bool:
        normalized = self._normalize(prompt)
        return normalized.startswith(("so ", "on days when", "to ", "तो ", "जिन दिनों"))

    def _build_contextual_reflection(self, language: str, target_item: Optional[str], normalized_text: str) -> str:
        if not normalized_text or not target_item:
            return ""
        if target_item in {"gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}:
            if self._has_single_issue_scope_answer(normalized_text):
                return CONTEXTUAL_REFLECTIONS["worry_single_issue"][language]
            if self._has_worry_domain_signal(normalized_text):
                return CONTEXTUAL_REFLECTIONS["worry_domain_focus"][language]
        if target_item == "phq_q2_low_mood" and self._has_flat_functioning_signal(normalized_text):
            return CONTEXTUAL_REFLECTIONS["flat_while_functioning"][language]
        return ""

    def _matches_any_segment(self, normalized_text: str, segments: Iterable[str]) -> bool:
        return any(self._already_used_segment(normalized_text, segment) for segment in segments)

    def _post_close_segments(self, language: str) -> Tuple[str, ...]:
        return (
            ANXIETY_LOOP_CLOSE_PROMPTS[language],
            CLOSING_MESSAGES[language],
            POST_CLOSE_CHOOSER_MESSAGES[language],
            FINAL_REST_MESSAGES[language],
            *FINAL_HOLD_VARIANTS[language],
        )

    def _post_close_followup_reply(
        self,
        session: ChatSession,
        latest_user_text: str,
        language: str,
    ) -> Optional[str]:
        last_assistant_text = self._last_assistant_text(session)
        if not self._matches_any_segment(last_assistant_text, self._post_close_segments(language)):
            return None
        if self._has_high_priority_post_close_signal(latest_user_text):
            return None
        if self._should_reopen_after_close(session, latest_user_text):
            return None
        if self._is_post_close_echo(session, latest_user_text, language):
            return FINAL_REST_MESSAGES[language]
        if self._is_close_acknowledgement(latest_user_text):
            if self._already_used_segment(last_assistant_text, FINAL_REST_MESSAGES[language]):
                return FINAL_REST_MESSAGES[language]
            return self._select_post_close_hold_message(session, language)
        if self._is_nonexpansive_followup(latest_user_text):
            if self._already_used_segment(last_assistant_text, FINAL_REST_MESSAGES[language]):
                return FINAL_REST_MESSAGES[language]
            if self._already_used_segment(last_assistant_text, POST_CLOSE_CHOOSER_MESSAGES[language]):
                return self._select_post_close_hold_message(session, language)
            return POST_CLOSE_CHOOSER_MESSAGES[language]
        return self._select_post_close_hold_message(session, language)

    def _select_post_close_hold_message(self, session: ChatSession, language: str) -> str:
        variants = FINAL_HOLD_VARIANTS[language]
        recent_assistant_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "assistant"][-3:]
        for variant in variants:
            if self._normalize(variant) not in recent_assistant_turns:
                return variant
        return variants[len(recent_assistant_turns) % len(variants)]

    def _has_timing_or_frequency_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return self._has_timing_answer(normalized_text) or self._has_frequency_answer(normalized_text)

    def _is_nonexpansive_followup(self, normalized_text: str) -> bool:
        if not normalized_text:
            return True
        words = normalized_text.split()
        if len(words) <= 4:
            return True
        if normalized_text in SHORT_FOLLOWUP_MARKERS:
            return True
        if len(words) <= 6 and any(marker in normalized_text for marker in SHORT_FOLLOWUP_MARKERS if len(marker) > 3):
            return True
        if self._has_timing_or_frequency_answer(normalized_text) and len(words) <= 7:
            return True
        return False

    def _is_close_acknowledgement(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if normalized_text in CLOSE_ACK_MARKERS:
            return True
        return any(marker in normalized_text for marker in CLOSE_ACK_MARKERS if len(marker.split()) > 1)

    def _has_high_priority_post_close_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._has_self_view_signal(normalized_text):
            return True
        if self._has_awful_outcome_signal(normalized_text):
            return True
        return False

    def _should_reopen_after_close(self, session: ChatSession, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._is_post_close_echo(session, normalized_text, session.language):
            return False
        if self._is_close_acknowledgement(normalized_text) or self._is_nonexpansive_followup(normalized_text):
            return False
        latest_signal_topics = self._latest_signal_topics(session)
        if not latest_signal_topics:
            return False
        reopenable_topics = (AFFECTIVE_TOPIC_FAMILY | {"sleep"}) - {"anxiety"}
        return bool(latest_signal_topics & reopenable_topics)

    def _is_post_close_echo(self, session: ChatSession, normalized_text: str, language: str) -> bool:
        if not normalized_text:
            return False
        assistant_turns = [
            self._normalize(turn.text)
            for turn in session.turns
            if turn.speaker == "assistant"
        ][-2:]
        if not assistant_turns:
            return False
        post_close_segments = tuple(self._normalize(segment) for segment in self._post_close_segments(language))
        user_tokens = self._meaningful_tokens(normalized_text)
        if len(user_tokens) < 6:
            return False
        for assistant_text in assistant_turns:
            if not assistant_text:
                continue
            if not any(segment in assistant_text for segment in post_close_segments):
                continue
            assistant_tokens = self._meaningful_tokens(assistant_text)
            if len(assistant_tokens) < 6:
                continue
            overlap = user_tokens & assistant_tokens
            shared = len(overlap)
            ratio = shared / max(min(len(user_tokens), len(assistant_tokens)), 1)
            if shared >= 6 and ratio >= 0.45:
                return True
        return False

    def _meaningful_tokens(self, normalized_text: str) -> set[str]:
        if not normalized_text:
            return set()
        return {
            token
            for token in re.findall(r"[\w\u0900-\u097F]+", normalized_text)
            if len(token) >= 3
        }

    def _has_activation_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in ACTIVATION_MARKERS)

    def _has_anhedonia_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in ITEM_SIGNAL_MARKERS["phq_q1_anhedonia"])

    def _has_self_view_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in ITEM_SIGNAL_MARKERS["phq_q6_worthlessness"])

    def _has_sleep_pattern_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in SLEEP_PATTERN_MARKERS)

    def _has_sleep_impact_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in SLEEP_IMPACT_MARKERS)

    def _has_sleep_choice_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "sleep issue",
            "sleep problem",
            "sleep ki dikkat",
            "sleep ki problem",
            "neend ki dikkat",
            "neend ki problem",
            "नींद की दिक्कत",
            "नींद की समस्या",
            "नींद नहीं आना",
        )
        return any(marker in normalized_text for marker in markers)

    def _has_timing_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in TIME_MARKERS)

    def _has_frequency_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in FREQUENCY_MARKERS) or any(
            pattern.search(normalized_text) for pattern in FREQUENCY_PATTERNS
        )

    def _has_worry_domain_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in WORRY_DOMAIN_MARKERS)

    def _has_awful_outcome_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in AWFUL_OUTCOME_MARKERS)

    def _has_persistent_worry_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in PERSISTENT_WORRY_MARKERS)

    def _has_lingering_tension_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in LINGERING_TENSION_MARKERS)

    def _has_worry_scope_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in WORRY_SCOPE_SPREAD_MARKERS) or any(
            marker in normalized_text for marker in WORRY_SCOPE_SINGLE_MARKERS
        )

    def _has_single_issue_scope_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in WORRY_SCOPE_SINGLE_MARKERS)

    def _has_flat_functioning_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        flat_markers = (
            "go through the motions",
            "going through the motions",
            "still get through",
            "still getting through",
            "work days",
            "on work days",
            "flat underneath",
            "motions",
            "motions mein",
            "दिन निकाल",
            "काम करते रहते",
            "बस करते रहते",
            "काम निपटाता रहता",
            "काम निपटाती रहती",
            "काम निपटाते रहते",
            "काम वाले दिनों",
            "और सपाट",
            "go through motions",
            "andar se sab flat",
            "function kar leta",
            "function kar leti",
            "flat lagta hai",
            "flat lagti hai",
            "flat lagti hain",
            "work days par",
        )
        return any(marker in normalized_text for marker in flat_markers)

    def _has_functional_impact_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "work days",
            "on work days",
            "work days par",
            "काम वाले दिनों",
            "still get through",
            "still getting through",
            "function on the outside",
            "bahar se",
            "flat underneath",
            "और सपाट",
            "flat lagta hai",
            "flat lagti hai",
            "flat lagti hain",
        )
        return any(marker in normalized_text for marker in markers)

    def _has_concentration_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "focus slips",
            "attention slips",
            "rereading",
            "rechecking",
            "same line",
            "same thing",
            "focus toot",
            "dobara padhna",
            "bar-bar padhna",
            "बार-बार टूट",
            "बार बार टूट",
            "बार-बार पढ़",
            "ध्यान टूट",
            "ध्यान भटक",
            "वापस लौट",
        )
        return any(marker in normalized_text for marker in markers)

    def _recent_sleep_pattern_known(self, session: ChatSession, lookback: int = 3) -> bool:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        return any(self._has_sleep_pattern_answer(text) for text in user_turns)

    def _has_new_anxiety_branch_detail(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._has_worry_domain_signal(normalized_text):
            return True
        if self._has_awful_outcome_signal(normalized_text):
            return True
        if self._has_worry_scope_answer(normalized_text):
            return False
        if self._has_lingering_tension_signal(normalized_text):
            return False
        if self._has_persistent_worry_signal(normalized_text) and not self._is_nonexpansive_followup(normalized_text):
            return True
        if len(normalized_text.split()) >= 7 and not self._has_timing_or_frequency_answer(normalized_text):
            return True
        return False

    def _continuity_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        held_back_items: list[str],
        fatigue: FatigueLevel,
    ) -> Optional[str]:
        if not session.asked_items:
            return None
        last_item = session.asked_items[-1]
        if last_item in held_back_items or last_item not in snapshot.items:
            return None

        last_user_turn = next((turn for turn in reversed(session.turns) if turn.speaker == "user"), None)
        last_assistant_turn = next((turn for turn in reversed(session.turns) if turn.speaker == "assistant"), None)
        if last_user_turn is None or last_assistant_turn is None or "?" not in last_assistant_turn.text:
            return None

        normalized_text = self._normalize(last_user_turn.text)
        words = len(last_user_turn.text.split())
        short_followup = words <= 6 or any(marker == normalized_text for marker in SHORT_FOLLOWUP_MARKERS)
        latest_signal_items = self._latest_signal_items(session)
        if (
            last_item == "phq_q3_sleep"
            and "gad_q4_trouble_relaxing" in latest_signal_items
            and not self._has_sleep_pattern_answer(normalized_text)
            and not self._has_timing_or_frequency_answer(normalized_text)
        ):
            return None
        if snapshot.items[last_item].status == "resolved":
            prompt_bank = ITEM_FOLLOW_UPS.get(last_item, {})
            has_variant = (
                ("timing_known" in prompt_bank and self._has_timing_answer(normalized_text))
                or ("frequency_known" in prompt_bank and self._has_frequency_answer(normalized_text))
            )
            if not has_variant:
                return None
        if self._has_timing_or_frequency_answer(normalized_text):
            return last_item
        if fatigue == "high" and snapshot.items[last_item].status not in {"contradicted", "abstained"}:
            return None
        if short_followup:
            return last_item
        return None

    def _style_suffix(self, language: str, plan: DialoguePlan) -> str:
        if plan.stage == "rapport":
            return ""
        if plan.next_action == "risk_check" or plan.target_topic == "safety":
            return SAFETY_SHORT_ANSWER_SUFFIXES[language]
        if plan.fatigue == "high":
            return BRIEF_DETAIL_SUFFIXES[language]
        if plan.user_style.openness == "guarded":
            return SOFTENING_SUFFIXES[language]
        if plan.user_style.verbosity == "brief":
            return BRIEF_DETAIL_SUFFIXES[language]
        if plan.user_style.verbosity == "detailed":
            return OPEN_STORY_SUFFIXES[language]
        return ""

    def _build_reflective_anchor(
        self,
        language: str,
        target_topic: str,
        user_style: UserStyleProfile,
        fatigue: FatigueLevel,
    ) -> str:
        anchor = TOPIC_REFLECTIONS.get(target_topic, {}).get(language, "")
        if fatigue == "high":
            return anchor
        if user_style.steering_preference == "user_led" and anchor:
            return anchor
        if user_style.openness == "guarded" and anchor:
            return anchor
        return anchor if target_topic in {"self_view", "safety"} else ""

    def _build_continuity_note(self, language: str, session: ChatSession, target_topic: str) -> str:
        recent = getattr(session.profile, "recent_checkins", None) or []
        if not recent:
            return ""
        latest = recent[0] if isinstance(recent[0], dict) else None
        if not latest:
            return ""
        recent_topic_key = str(latest.get("topic") or "check_in").replace(" ", "_").lower()
        recent_topic = self._topic_label(recent_topic_key, language).lower()
        if recent_topic_key == target_topic:
            continuity = {
                "en": f"If this feels similar to your recent {recent_topic} check-in, tell me what has stayed the same or changed.",
                "hi": f"अगर यह आपकी हाल की {recent_topic} बातचीत से मिलता-जुलता लग रहा है, तो बताइए क्या वैसा रहा और क्या बदला।",
                "hinglish": f"Agar yeh recent {recent_topic} check-in jaisa lag raha hai, to batao kya same raha aur kya change hua.",
            }
            return continuity[language]
        continuity = {
            "en": f"If this feels different from your recent {recent_topic} check-in, you can tell me what changed this time.",
            "hi": f"अगर यह हाल की {recent_topic} बातचीत से अलग लग रहा है, तो बताइए इस बार क्या बदला।",
            "hinglish": f"Agar yeh recent {recent_topic} check-in se different lag raha hai, to batao is baar kya change hua.",
        }
        return continuity[language]

    def _recommend_nudges(
        self,
        session: ChatSession,
        target_topic: str,
        user_style: UserStyleProfile,
        stage: str,
        fatigue: FatigueLevel,
    ) -> list[str]:
        order: list[str] = []
        if stage == "safety" or target_topic == "safety":
            order.append("safety")
        if target_topic in {"mood", "sleep", "anxiety"}:
            order.append(target_topic)

        if fatigue == "high":
            order.extend(["impact", "example"])
        elif user_style.openness == "guarded":
            order.extend(["example", "impact", "timing"])
        elif user_style.verbosity == "brief":
            order.extend(["example", "timing", "impact"])
        elif user_style.steering_preference == "user_led":
            order.extend(["impact", "example", "timing"])
        else:
            order.extend(["example", "impact", "timing"])

        helpful = [event.strategy for event in session.nudge_events[-2:] if event.outcome == "helpful"]
        unhelpful = [event.strategy for event in session.nudge_events[-2:] if event.outcome == "unhelpful"]
        promoted = [strategy for strategy in helpful if strategy in order]
        demoted = [strategy for strategy in unhelpful if strategy in order]

        deduped: list[str] = []
        for key in promoted + order:
            if key not in deduped and key not in demoted:
                deduped.append(key)
        for key in demoted:
            if key not in deduped:
                deduped.append(key)
        return deduped[:3]

    def _distress_trend(self, snapshot: ScreeningSnapshot, session: ChatSession) -> str:
        user_turn_ids = [turn.turn_id for turn in session.turns if turn.speaker == "user"]
        if len(user_turn_ids) < 2:
            return "unclear"

        severity_by_turn = {turn_id: 0 for turn_id in user_turn_ids}
        for span in snapshot.evidence_spans:
            if span.turn_id in severity_by_turn:
                severity_by_turn[span.turn_id] += span.score_hint

        values = [severity_by_turn[turn_id] for turn_id in user_turn_ids[-3:]]
        if len(values) < 2:
            return "unclear"
        if values[-1] >= values[0] + 2:
            return "rising"
        if values[-1] + 2 <= values[0]:
            return "easing"
        return "steady"
