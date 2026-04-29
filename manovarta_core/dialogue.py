from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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


_MARKER_BOUNDARY_CHARS = r"0-9A-Za-z_\u0900-\u0903\u0904-\u0939\u093c-\u094d\u0950-\u0963\u0966-\u096F\u0970-\u097F"


@lru_cache(maxsize=8192)
def _marker_pattern(marker: str) -> re.Pattern[str]:
    normalized_marker = " ".join(marker.lower().split())
    if not normalized_marker:
        return re.compile(r"(?!x)x")
    escaped = re.escape(normalized_marker).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![{_MARKER_BOUNDARY_CHARS}]){escaped}(?![{_MARKER_BOUNDARY_CHARS}])")


def _contains_marker(normalized_text: str, marker: str) -> bool:
    if not normalized_text or not marker:
        return False
    return bool(_marker_pattern(marker).search(normalized_text))


def _contains_any_marker(normalized_text: str, markers: Iterable[str]) -> bool:
    return any(_contains_marker(normalized_text, marker) for marker in markers)


def _count_markers(normalized_text: str, markers: Iterable[str]) -> int:
    return sum(1 for marker in markers if _contains_marker(normalized_text, marker))


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

WORKING_SUMMARY_PREFIXES = {
    "en": "Here is the working picture so far:",
    "hi": "अभी तक जो तस्वीर बन रही है, उसमें",
    "hinglish": "Ab tak jo picture ban rahi hai, usme",
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

POST_CLOSE_IDLE_MESSAGES = {
    "en": "Understood. We can pause here for now. If you want to continue later, share one concrete detail and we’ll pick it up from there.",
    "hi": "समझ गया। हम अभी यहीं विराम रख सकते हैं। जब आगे बढ़ना चाहें, एक ठोस बात बताइए और हम वहीं से शुरू करेंगे।",
    "hinglish": "Samajh gaya. Hum abhi yahin pause rakh sakte hain. Jab continue karna ho, ek concrete detail bolo aur hum wahin se start karenge.",
}

ANXIETY_LOOP_BREAK_PROMPTS = {
    "en": "Let me pause and reflect what I’m hearing: this anxiety seems to build at certain times and feel heavier on stressful days. If that fits, tell me just one last thing: does it mostly stay around work or responsibilities, or does it spread into other parts of life too?",
    "hi": "मैं थोड़ा रुककर जो समझ आ रहा है उसे पकड़ना चाहता हूँ: यह चिंता कुछ खास समय पर बढ़ती है और तनाव वाले दिनों में ज्यादा लग सकती है। अगर यह सही लग रहा है, तो बस एक आख़िरी बात बताइए: यह ज़्यादा काम या जिम्मेदारियों तक रहती है, या दूसरी बातों में भी फैल जाती है?",
    "hinglish": "Main thoda ruk kar jo samajh aa raha hai use hold karna chahta hoon: yeh anxiety kuch specific times par build hoti hai aur stressful days mein heavier lag sakti hai. Agar yeh sahi lag raha hai, to bas ek last cheez batao: yeh zyada work ya responsibilities tak rehti hai, ya life ke aur parts mein bhi spread ho jaati hai?",
}

ANXIETY_LOOP_CLOSE_PROMPTS = {
    "en": "I have enough to hold onto the main pattern now: this anxiety builds more at certain times and can feel heavier on stressful days. I can treat that as the working summary unless there is one important detail you still want to add.",
    "hi": "अब मेरे पास मुख्य पैटर्न पकड़ने लायक काफ़ी जानकारी है: यह चिंता कुछ खास समय पर बढ़ती है और तनाव वाले दिनों में ज्यादा लग सकती है। अगर कोई बहुत ज़रूरी बात बाकी न हो, तो मैं इसे अभी कामचलाऊ सार मान सकता हूँ।",
    "hinglish": "Ab mere paas main pattern hold karne ke liye enough detail hai: yeh anxiety kuch specific times par build hoti hai aur stressful days mein heavier lag sakti hai. Agar koi bahut important detail baaki nahi hai, to main ise abhi working summary maan sakta hoon.",
}

RAPPORT_PROMPTS = {
    "en": "Has it been feeling more like low mood, constant worry, poor sleep, or a mix of those?",
    "hi": "क्या यह ज़्यादा उदासी, लगातार चिंता, नींद की दिक्कत, या इनका मिश्रण लग रहा है?",
    "hinglish": "Kya yeh zyada low mood, constant worry, sleep issue, ya in sab ka mix lag raha hai?",
}

PHYSICAL_CLARIFIER_PROMPTS = {
    "en": "When you say you are a little under the weather, does it feel more physical, more emotional, or a mix of both today?",
    "hi": "जब आप कहते हैं कि तबीयत कुछ ऑफ लग रही है, क्या यह आज ज़्यादा शारीरिक लग रहा है, भावनात्मक, या दोनों का मिश्रण?",
    "hinglish": "Jab aap kehte ho ki aaj thoda under the weather lag raha hai, kya yeh zyada physical lag raha hai, emotional, ya dono ka mix?",
}

PHYSICAL_BRIDGE_PROMPTS = {
    "en": "Thanks, that helps. Has this mostly stayed a physical off-feeling, or has it also started affecting sleep, energy, appetite, or your day-to-day mood?",
    "hi": "ठीक है, इससे बात साफ़ हुई। क्या यह अभी ज़्यादातर शारीरिक ऑफ-फीलिंग ही है, या इसका असर नींद, ऊर्जा, भूख, या रोज़मर्रा के मूड पर भी पड़ने लगा है?",
    "hinglish": "Theek hai, isse picture clearer hui. Kya yeh abhi mostly physical off-feeling hi hai, ya sleep, energy, appetite, ya day-to-day mood par bhi effect dikh raha hai?",
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
    "en": "Whichever part feels easiest to answer is okay.",
    "hi": "जो हिस्सा जवाब देना सबसे आसान लगे, उसी से शुरू करना ठीक है।",
    "hinglish": "Jo part answer karna sabse easier lage, usse start karna bilkul fine hai.",
}

BRIEF_DETAIL_SUFFIXES = {
    "en": "One recent example, one timing detail, or a quick 0 to 10 is enough.",
    "hi": "एक हाल का उदाहरण, समय का एक संकेत, या 0 से 10 का छोटा अंदाज़ा भी काफ़ी है।",
    "hinglish": "Ek recent example, ek timing detail, ya 0 se 10 ka quick estimate bhi enough hai.",
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

SCENE_PROMPTS: Dict[str, Dict[str, str]] = {
    "mood_selfview": {
        "en": "When the harder days hit, what lands most in the foreground: feeling low, losing interest before you even start, or getting harsher on yourself?",
        "hi": "जब दिन ज़्यादा भारी होता है, सबसे आगे क्या महसूस होता है: उदासी, शुरू करने से पहले ही मन हट जाना, या खुद को बोझ/बहुत कठोर महसूस करना?",
        "hinglish": "Jab harder days hit karte hain, foreground mein kya zyada aata hai: low feel hona, start karne se pehle hi mann hat jana, ya apne aap par zyada harsh ho jana?",
    },
    "sleep_functioning": {
        "en": "After the rough sleep or low-energy days, what slips first for you: getting going, appetite, staying with one task, or your pace feeling noticeably slowed or keyed up?",
        "hi": "खराब नींद या थकान/ऊर्जा की कमी वाले दिनों के बाद सबसे पहले क्या प्रभावित होता है: शुरू होने की ऊर्जा, भूख, एक काम पर टिकना, या शरीर भारी लगना/रफ्तार का धीमा या बेचैन हो जाना?",
        "hinglish": "Rough sleep ya low-energy days ke baad sabse pehle kya slip karta hai: start lene ki energy, appetite, ek task par tikna, ya body heavy lagna / pace ka noticeably slow ya keyed up ho jana?",
    },
    "worry_shape": {
        "en": "When the worry starts, which shape fits it best: a keyed-up feeling in the background, one thought-loop you cannot shake, or several work or future worries piling together?",
        "hi": "जब चिंता शुरू होती है, किस तरह ज़्यादा फिट बैठती है: अंदर-ही-अंदर घबराया-सा एहसास, एक ही विचार की लूप जो छूटती नहीं, या काम/भविष्य की कई चिंताएँ एक साथ जमा होना?",
        "hinglish": "Jab worry start hoti hai, kaunsi shape zyada fit baithti hai: background mein keyed-up feeling, ek thought-loop jo chhootti nahi, ya work aur future ki kai worries saath mein pile hona?",
    },
    "worry_activation": {
        "en": "And when it peaks, what stands out more: hard to quiet the mind, restlessness, irritability, or a sense that something may go wrong next?",
        "hi": "और जब यह सबसे तेज़ होती है, तब क्या ज़्यादा सामने आता है: दिमाग को शांत करना मुश्किल होना, बेचैनी, चिड़चिड़ापन, या यह एहसास कि आगे कुछ गलत हो सकता है?",
        "hinglish": "Aur jab yeh peak karti hai, tab kya zyada stand out karta hai: mind ko quiet karna tough hona, restlessness, irritability, ya yeh feel ki aage kuch galat ho sakta hai?",
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
    "gad_q7_afraid": 3,
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
PHYSICAL_MALAISE_MARKERS = (
    "under the weather",
    "feeling under the weather",
    "feel under the weather",
    "little under the weather",
    "a little under the weather",
    "not feeling well",
    "feeling unwell",
    "physically off",
    "body ache",
    "body aches",
    "feverish",
    "down with a cold",
    "sore throat",
    "cold and cough",
    "thoda beemar",
    "thoda bimaar",
    "tabiyat theek nahi",
    "tabiyat kharab",
    "तबीयत ठीक नहीं",
    "तबीयत खराब",
    "थोड़ा बीमार",
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
CONTINUE_MARKERS = (
    "what else do you want to know",
    "what else do you need to know",
    "what else do you still need to know",
    "what else do you want to ask",
    "what else should i tell you",
    "ask what you need",
    "ask what you still need",
    "if you need to close the gaps",
    "if you need to fill the gaps",
    "if you need to close remaining gaps",
    "close the gaps",
    "fill the gaps",
    "fill the remaining gaps",
    "close the remaining gaps",
    "whatever is still missing ask it",
    "whatever is still missing you can ask",
    "ask more",
    "keep asking",
    "keep going",
    "dont close yet",
    "don't close yet",
    "do not close yet",
    "if one detail is missing",
    "if one important detail is missing",
    "ask it indirectly",
    "ask one missing detail",
    "kya janana hai",
    "kya janna hai",
    "kya jaanna hai",
    "kya poochna hai",
    "kya puchna hai",
    "aur kya poochna hai",
    "aur kya puchna hai",
    "kya aur janana hai",
    "क्या जानना है",
    "क्या और जानना है",
    "क्या पूछना है",
    "और क्या पूछना है",
    "और क्या जानना है",
    "close mat karo",
    "conversation close mat karo",
    "band mat karo",
    "mat roko",
    "aur pucho",
    "aur poochho",
    "agar ek cheez missing hai",
    "agar ek zaroori baat missing hai",
    "agar kuch zaroori chhuta hai",
    "indirect pooch lo",
    "indirect tareeke se pooch lo",
    "puchte raho",
    "पूछते रहो",
    "बंद मत करो",
    "बात बंद मत करो",
    "क्लोज मत करो",
)
SUMMARY_REQUEST_MARKERS = (
    "give me a summary",
    "can you summarize",
    "please summarize",
    "summarize the pattern",
    "summarize this",
    "sum this up",
    "what is the summary",
    "what are you seeing so far",
    "what are you seeing",
    "picture so far",
    "working summary",
    "ab tak jo samjha hai",
    "ab tak jo samjha",
    "ab tak jo samajha hai",
    "ab tak jo samajha",
    "ab tak jo samjhe ho",
    "ab tak jo dekh rahe ho",
    "summary de do",
    "summary de do na",
    "summary de dijiye",
    "summary bata do",
    "summary batao",
    "summary bata dijiye",
    "summary bol do",
    "summary bol dijiye",
    "ek summary de do",
    "saar bata do",
    "saar batao",
    "saar bata dijiye",
    "sar bata do",
    "sar batao",
    "sar bata dijiye",
    "saar de dijiye",
    "sar de dijiye",
    "सार बता दो",
    "सार बताओ",
    "सार बता दीजिए",
    "साफ़ सार बता दीजिए",
    "साफ सार बता दीजिए",
    "एक साफ़ सार बता दीजिए",
    "एक साफ सार बता दीजिए",
    "सार दे दीजिए",
    "समरी दे दीजिए",
    "समरी बता दीजिए",
    "summary दे दो",
    "summary बताओ",
    "summary बता दो",
    "summary दे दीजिए",
    "summary बता दीजिए",
    "working summary chahiye",
    "abhi ka working summary chahiye",
    "abhi tak ka working summary chahiye",
    "abhi tak ka saar chahiye",
    "abhi ka saar chahiye",
    "abhi tak ka sar chahiye",
    "abhi ka sar chahiye",
    "saar chahiye",
    "sar chahiye",
    "abhi saar de sakte hain",
    "abhi sar de sakte hain",
    "abhi summary de sakte hain",
    "सार चाहिए",
    "अभी तक का सार चाहिए",
    "अभी का सार चाहिए",
    "अभी सार दे सकते हैं",
    "अभी सार दे सकते हो",
    "अभी summary दे सकते हैं",
)
MIN_SUMMARY_TOUCHES = 10
ACTIVATION_MARKERS = (
    "low energy",
    "energy down",
    "energy low",
    "energy bhi down",
    "energy bhi low",
    "energy down ho",
    "energy crash",
    "energy crashes",
    "energy crash ho jati",
    "energy crash ho jaati",
    "heavy in the morning",
    "harder to get moving",
    "hard to get moving",
    "hard to get started",
    "harder to get started",
    "taking longer to get started",
    "takes longer to get started",
    "mind taking longer",
    "mind feels slow",
    "mind feels slower",
    "feel heavy and slow",
    "feels heavy and slow",
    "heavy and slow",
    "body feels heavy",
    "body feel heavy",
    "body heavy",
    "brain fog",
    "drag through the day",
    "drag through work",
    "drag through the next day",
    "drag through everything",
    "next day i drag through everything",
    "next day pura system drag karta hai",
    "next day pura system drag karti hai",
    "pura system drag karta hai",
    "pura system drag karti hai",
    "system drag karta hai",
    "system drag karti hai",
    "slow to start",
    "slow to get started",
    "takes extra effort to get moving",
    "take extra effort to get moving",
    "extra effort to get moving",
    "mind slow start hota hai",
    "mind slow start hota",
    "day start karna heavy",
    "routine slip",
    "routine hi slip",
    "body aur routine",
    "body and routine",
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
    "aalas",
    "susti",
    "सुस्ती",
    "सुस्त",
    "आलस",
    "thakan",
    "thakan zyada lagti hai",
    "din bhar thakan rehti hai",
    "subah uthte hi thakan rehti hai",
    "din bhar drained rehti hoon",
    "din bhar drained rehta hoon",
    "drained rehti hoon",
    "drained rehta hoon",
    "शरीर टूटा सा लगता है",
    "सुबह उठकर शरीर टूटा सा लगता है",
    "more like low energy than worry",
    "feels more like low energy than worry",
    "body thodi down lag rahi hai",
    "body thodi down lag raha hai",
    "slow ho gaya hoon",
    "slow ho gayi hoon",
)
SLEEP_PATTERN_MARKERS = (
    "sleep is broken",
    "sleep broken",
    "broken sleep",
    "sleep has shifted later",
    "sleep shifted later",
    "sleep has shifted",
    "sleep shifted",
    "sleep has been patchy",
    "sleep been patchy",
    "sleep patchy",
    "patchy sleep",
    "sleep thodi messy",
    "sleep messy",
    "messy sleep",
    "sleep ka pattern off hai",
    "sleep pattern off hai",
    "neend der se aati hai",
    "neend der se aati",
    "neend late aati hai",
    "नींद बिगड़ गई है",
    "नींद बिगड़ गई",
    "नींद देर से आती है",
    "नींद देर से आती",
    "late soti hoon",
    "late sota hoon",
    "hard to fall asleep",
    "cannot fall asleep",
    "can't fall asleep",
    "trouble falling asleep",
    "wake up around",
    "wake up at",
    "wake around",
    "sleep has been taking forever",
    "taking forever to fall asleep",
    "takes forever to fall asleep",
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
    "उठ जाता",
    "उठ जाती",
    "तीन-चार बजे",
    "तीन चार बजे",
    "3 या 4 बजे",
    "3 बजे",
    "4 बजे",
    "raat ko 3 baje",
    "raat ko 4 baje",
    "3 ya 4 baje",
    "aankh khul",
)
SLEEP_IMPACT_MARKERS = (
    "tired the next morning",
    "tired next morning",
    "next morning",
    "morning tired",
    "afternoon I feel heavy",
    "afternoon feels heavy",
    "by afternoon i feel heavy",
    "not fresh",
    "not rested",
    "सुबह थक",
    "सुबह थकान",
    "थकान रहती",
    "शरीर टूटा सा लगता है",
    "सुबह उठकर शरीर टूटा सा लगता है",
    "din bhar drained rehti hoon",
    "din bhar drained rehta hoon",
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
    "दिन भर",
    "पूरे दिन",
    "पूरा दिन",
    "poore din",
    "poora din",
    "din bhar",
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
    "comes back",
    "come back",
    "chalta rehta",
    "chalta rehti",
    "chalte rehta",
    "chalte rehti",
    "background mein chalta rehta",
    "चलती रहती",
    "चलता रहता",
    "चलाते रहती",
    "चलाते रहता",
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
    "many areas",
    "many parts",
    "many issues",
    "other things too",
    "more than one thing",
    "kai baat",
    "kai baaton",
    "kai cheez",
    "kai cheezon",
    "kai issues",
    "kai jagah",
    "spread ho",
    "spread hota",
    "spread hoti",
    "spread ho ja",
    "spread ho jata",
    "spread ho jaati",
    "कई बात",
    "कई बातों",
    "कई चीज",
    "कई चीजों",
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
    "gad_q7_afraid",
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
    "phq_q8_psychomotor": {
        "en": "It sounds like the day's pace itself may be feeling off.",
        "hi": "लगता है दिन की रफ्तार या चाल-ढाल भी कुछ बदली हुई लग रही है।",
        "hinglish": "Lag raha hai din ki pace ya body ka flow bhi thoda off lag raha hai.",
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
    "gad_q7_afraid": {
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
            "en": "That helps me understand how often it happens. When the energy drops, does it feel more like body heaviness, a slow-starting mind, or both together?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या ज़्यादा शरीर भारी लगता है, दिमाग शुरू होने में धीमा पड़ता है, या दोनों साथ में?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab yeh hota hai, kya zyada body heavy lagti hai, mind slow start hota hai, ya dono saath mein?",
        },
    },
    "phq_q5_appetite": {
        "default": {
            "en": "Has appetite mostly been lower than usual, higher than usual, or more irregular because meals get skipped or delayed?",
            "hi": "क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?",
            "hinglish": "Kya appetite zyada kam hui hai, zyada badhi hai, ya meals skip ya delay hone ki wajah se zyada irregular ho gayi hai?",
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
    "phq_q8_psychomotor": {
        "default": {
            "en": "When the day gets heavier, does your pace feel more slowed down than usual, or do you feel more keyed up and unable to stay still?",
            "hi": "जब दिन भारी हो जाता है, क्या आपकी रफ्तार ज़्यादा धीमी पड़ती लगती है, या उल्टा भीतर ऐसी बेचैनी होती है कि एक जगह टिकना मुश्किल हो जाता है?",
            "hinglish": "Jab din heavy ho jata hai, kya aapki pace zyada slow padti lagti hai, ya ulta andar aisi restlessness hoti hai ki ek jagah tikna mushkil ho jata hai?",
        },
        "timing_known": {
            "en": "That timing helps. Around then, does your pace feel more slowed down than usual, or do you feel more keyed up and unable to stay still?",
            "hi": "यह समय-सूचना मददगार है। उस समय के आसपास, क्या आपकी रफ्तार ज़्यादा धीमी लगती है, या उल्टा भीतर बेचैनी बढ़ जाती है और टिकना मुश्किल हो जाता है?",
            "hinglish": "Yeh timing helpful hai. Din ke end ya us waqt, kya pace ka noticeably slow padna zyada feel hota hai, ya restlessness badh jaati hai aur still rehna mushkil hota hai?",
        },
        "frequency_known": {
            "en": "That helps me understand how often it happens. When it does, does your pace feel more slowed down than usual, or do you feel more keyed up and unable to stay still?",
            "hi": "इससे मुझे समझ आ रहा है कि यह कितनी बार होता है। जब ऐसा होता है, क्या आपकी रफ्तार ज़्यादा धीमी लगती है, या भीतर बेचैनी बढ़ जाती है और टिकना मुश्किल हो जाता है?",
            "hinglish": "Isse samajh aa raha hai ki yeh kitni baar hota hai. Jab aisa hota hai, kya pace zyada slow lagti hai, ya restlessness badh jaati hai aur still rehna mushkil hota hai?",
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
        "mind_known": {
            "en": "When you try to settle down, is the harder part stopping the thought-loop, shifting your mind to something else, or getting the mind to go quiet again?",
            "hi": "जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल विचारों की लूप को रोकना होता है, दिमाग को कहीं और ले जाना, या दिमाग को फिर से शांत करना?",
            "hinglish": "Jab aap settle hone ki koshish karte ho, kya zyada mushkil thought-loop ko rokna hota hai, mind ko kahin aur shift karna, ya mind ko phir se quiet karna?",
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
    "gad_q7_afraid": {
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
    "phq_q1_anhedonia": ("not interested", "no interest", "disconnected", "nothing feels good", "used to enjoy", "less interest in things", "interest has gone down", "things i usually care about feel flat", "things i usually care about feel flat before i even start them", "interest bhi kam ho gaya", "रुचि कम हो गई", "pulling away from people", "distance bana leta", "motivation low", "feel flat", "feels flat", "flat now", "flat lagta", "flat lagti", "flat lagti hai", "flat lagti hain", "flat feel hoti hai", "flat feel hoti hain", "flat underneath", "everything feels flat underneath", "numb", "disconnected feel ho raha hai", "disconnected feel ho rahi hai", "feel very little from them", "get much from them", "do not get much from them", "don't get much from them", "feel nahi hota", "kuch feel nahi hota", "unse kuch feel nahi hota", "go through the motions", "go through motions", "motions mein chalta rehta", "motions mein chalta rehti", "mann nahi lagta", "मन नहीं लगता", "दिल नहीं करता", "फीका लगता", "बहुत कम महसूस", "बहुत कम महसूस होता है", "जो चीज़ें पहले अच्छी लगती थीं", "पहले अच्छी लगती थीं", "काम शुरू करने से पहले ही मन हट जाता है", "काम शुरू करने का मन हट जाता है", "काम शुरू करने का मन जल्दी हट जाता है", "काम शुरू करने का मन नहीं करता", "कोई काम शुरू करने का मन नहीं करता", "काम करने की इच्छा नहीं होती", "काम करने की इच्छा ही नहीं होती", "कोई काम करने की इच्छा नहीं होती", "कोई काम करने की इच्छा ही नहीं होती", "कोई काम करने की इच्छा करती ही नहीं है", "काम करने की इच्छा करती ही नहीं है", "मन जल्दी हट जाता है", "किसी काम से मन हट जाता है", "किसी काम से मन हट जाना", "मन हट जाता है", "मन हट जाना", "मन पहले से ही हट जाता है", "jo cheezein pehle achhi lagti thi", "jo cheezen pehle achhi lagti thi", "start karne se pehle hi mann hat jata hai", "start karne se pehle mann hat jata hai", "delay starting things", "keep delaying starting things", "put off starting things", "kaam start karne ka mann nahi karta", "work start karne ka mann nahi karta", "mann hat jata hai", "mann hat jana", "kisi kaam se mann hat jata hai", "kisi kaam se mann hat jana", "kaam mein mann nahi lagta", "kaam me mann nahi lagta", "sab flat sa lagta hai", "flat sa lagta hai", "kisi cheez mein mann nahi lagta", "kisi cheez me mann nahi lagta", "ignore their texts", "ignore texts", "ignore messages", "reply talta rehta hoon", "reply talti rehti hoon", "कटा-कटा", "कटा कटा"),
    "phq_q2_low_mood": ("low mood", "sad", "feel down", "feel low", "feel low through most of the day", "low through most of the day", "empty", "days feel heavy", "day feels heavy", "heavy mood", "flat and heavy", "heavy and blank", "heavy aur thoda blank", "flat aur low lagta hai", "flat aur low lagti hai", "zyada flat aur low lagta hai", "zyada flat aur low lagti hai", "low aur disconnected feel ho raha hai", "low aur disconnected feel ho rahi hai", "kaafi time se low aur disconnected feel ho raha hai", "kaafi time se low aur disconnected feel ho rahi hai", "खालीपन", "खालीपन है", "मन भारी", "भारी", "उदास", "उदासी", "उदासी आती है", "उदासी आ जाती है", "वर्तमान देखता हूं तो उदासी आती है", "वर्तमान देखता हूं तो मन भारी लगता है", "वर्तमान देखता हूँ तो मन भारी लगता है", "present dekh ke heavy lagta hai", "present dekh ke heavy lagti hai", "present feels heavy", "abhi sab bhaari lagta hai", "अभी सब भारी लगता है", "udasi", "udasi zyada lagti hai", "udaasi aati hai", "ज़्यादा उदासी", "ज्यादा उदासी"),
    "phq_q4_fatigue": ("tired", "drained", "fatigue", "low energy", "energy down", "energy low rehti hai", "din bhar energy low rehti hai", "din bhar drained rehti hoon", "din bhar drained rehta hoon", "drained rehti hoon", "drained rehta hoon", "wiped", "heavy in the morning", "slow to start", "slow to get started", "mind feels slow", "brain fog", "subah heavy", "थक", "थकान", "ऊर्जा", "ऊर्जा कम", "सुबह भारी", "दिमाग धीमा", "शरीर टूटा सा लगता है", "सुबह उठकर शरीर टूटा सा लगता है", "सुबह उठकर शरीर भारी लगता है", "सुबह उठकर शरीर भारी लगती है", "शरीर भारी लगता है", "शरीर भारी लगती है", "शरीर धीमा पड़ जाता है", "aalas", "susti", "सुस्ती", "सुस्त", "आलस", "दिन भर आलस", "दिन में आलस", "next day pura tired", "bed se uthna heavy", "dragging myself through the day", "drag through everything", "body feels heavy", "body feels slow", "body feels slow by evening", "body heavy lagti hai", "body heavy lagta hai", "body slow ho jati hai", "body slow ho jaati hai", "day ke end tak body heavy lagti hai", "mind is slow to get going", "mind slow to get going", "mind slow start hota hai", "mind slow start hota", "सुबह शुरू होने में बहुत समय लगता है", "start lena heavy lagta hai", "thakan", "thakan zyada lagti hai", "din bhar thakan rehti hai", "subah uthte hi thakan rehti hai", "more like low energy than worry", "feels more like low energy than worry", "body thodi down lag rahi hai", "body thodi down lag raha hai", "pura system drag karta hai", "pura system drag karti hai", "system drag karta hai", "system drag karti hai", "extra effort to get moving", "slow ho gaya hoon", "slow ho gayi hoon"),
    "phq_q5_appetite": ("appetite", "appetite is off", "not eating much", "eating too much", "skipping meals", "skip meals", "skip lunch without noticing", "skip meals without noticing", "eat because i have to", "still have not eaten properly", "whatever is quickest", "hunger is off", "hungry hi nahi lagta", "bhook nahi lagti", "bhook kam", "bhook pehle jaisi nahi", "bhook pe dhyan nahi rehta", "bhook ka dhyan nahi rehta", "bhook ka dhyan hi nahi rehta", "khane ka mann nahi", "hunger cues", "lose track of hunger", "lose track of hunger cues", "भूख", "भूख कम", "भूख नहीं", "भूख का ध्यान नहीं रहता", "भूख का ध्यान ही नहीं रहता", "खाना skip", "खाना छोड़", "खाना छोड़ देता हूं", "खाना छोड़ देती हूं", "खाना ठीक से नहीं", "lunch just slips", "lunch slips", "lunch miss", "lunch miss ho jata", "meal slips", "meals just slip", "meals get delayed", "meal gets delayed", "meals delayed", "meal delayed", "meals skip ho jate hain", "meals skip ho jaate hain", "meals skip ho rahe", "meals skip ho rahe hain", "meal skip ho raha", "meal skip ho rahi", "meals bhi slip ho jaate hain", "meals bhi slip ho jate hain", "appetite bhi down", "appetite bhi down ho jati hai", "appetite bhi down ho jaati hai", "bhook bhi kam", "bhook bhi kam ho jati hai", "भूख भी कम", "भूख भी कम हो जाती है", "खाना छूट जाता है", "कई बार खाना छूट जाता है", "दोपहर का खाना छूट जाता है", "दोपहर का खाना छूट जाता", "dopahar ka khana chhut jata hai", "dopahar ka khana chhut jata"),
    "phq_q6_worthlessness": ("burden", "extra burden", "burden hoon", "worthless", "useless", "guilt", "guilty", "feel guilty", "make things heavier", "making things heavier", "ashamed", "shame", "wasting everyone's time", "waste everyone's time", "better off without me", "बोझ", "बोझ हूँ", "सबके लिए बोझ", "बेकार", "मेरी वजह से", "शर्म", "letting people down", "letting everyone down", "feel like i am letting people down", "harsh on myself", "hard on myself", "harder on myself", "frustrated with myself", "frustration with myself", "self talk harsh", "self-talk harsh", "blame myself", "self blame", "judge myself", "judging myself", "i keep judging myself", "everyone else is handling basic life better than i am", "बाकी लोग सामान्य चीज़ें मुझसे बेहतर संभाल रहे हैं", "बाकी लोग सामान्य चीजें मुझसे बेहतर संभाल रहे हैं", "बाकी लोग मुझसे बेहतर संभाल रहे हैं", "खुद को बहुत कोसता", "खुद को कोसता", "सब पर बोझ", "सब पर बोझ बन", "बोझ बन रहा", "burden jaisa feel", "अपने आप पर गुस्सा आता है", "खुद पर गुस्सा आता है", "मैं कुछ कर क्यों नहीं पा रहा", "मैं कुछ कर क्यों नहीं पा रही", "अपने ऊपर झुंझलाहट होती है", "अपने ऊपर झुंझलाहट होने लगती है", "tiny tasks feel bigger than they should", "kyun nahi kar pa raha", "kyun nahi kar pa rahi", "khud par frustration hoti hai", "khud par frustrated feel hota hai", "khud par harsh", "khud par kaafi harsh", "khud par harsh ho jata", "khud par harsh ho jaata", "khud par harsh ho jati", "khud par harsh ho jaati", "apne aap par harsh"),
    "phq_q3_sleep": ("sleep", "asleep", "wake", "waking", "sleep disturb", "neend disturb", "नींद", "रात", "रात में", "उठ जाती", "switch off", "wake around 3 or 4", "wake around 3 or 4 am", "3 or 4 am", "3 ya 4 baje", "aankh khul jaati", "तीन-चार बजे", "तीन चार बजे"),
    "phq_q7_concentration": ("focus", "concentrat", "attention", "cannot focus", "can't focus", "harder to focus", "hard to focus", "taking longer to get started", "takes longer to get started", "mind taking longer", "mind feels slow", "brain fog", "ध्यान", "focus nahi", "focus toot jata", "focus टूट", "ध्यान नहीं टिक", "ध्यान भी टिकता नहीं", "ध्यान भी नहीं टिकता", "ध्यान टिकता नहीं", "ध्यान टूट जाता है", "ध्यान टूटने लगता है", "mind blanks", "screen", "stare at the same screen", "same screen", "same line", "same paragraph", "same paragraph three times", "rereading", "rechecking", "start hone mein time lagta", "start hone me time lagta", "mind ko start hone mein time lagta", "mind ko start hone me time lagta", "दिमाग धीमा", "reread the same line", "reread the same line and", "reread the same line and still zone out", "zone out", "same line dobara", "same line dobara padhni", "same line baar baar padhni padti hai", "एक ही लाइन दोबारा", "एक ही चीज़ दोबारा पढ़नी पड़ती है", "वही लाइन कई बार", "वही लाइन कई बार पढ़नी", "ध्यान बार-बार टूट", "small tasks take forever", "small tasks slow lagte", "long runway before i can start", "push maangte hain"),
    "phq_q8_psychomotor": ("moving slowly", "talking slowly", "pace feels slowed", "pace feeling slowed", "whole body feels dragged", "moves feel slowed", "moves feel slowed down", "pace slow ho jata", "pace slow lagti hai", "chaal dheemi", "रफ्तार धीमी", "रफ्तार धीमी हो गई", "घिसटता हुआ", "घिसटता हुआ सा", "शरीर भी धीमा पड़ जाता है", "धीमा पड़ जाता है", "धीमा पड़ जाती है", "small tasks take forever", "small tasks slow lagte", "so restless i pace", "pace around", "ek jagah tik nahi pata", "idhar udhar chakkar", "बेचैनी में उठता बैठता", "body feels slow by evening", "body slow ho jati hai", "body slow ho jaati hai"),
    "gad_q1_nervous": ("always on edge", "feel anxious", "feeling anxious", "feeling very anxious", "very anxious", "anxious", "anxious today", "little anxious", "a little anxious", "constantly nervous", "mind overloaded", "keyed up", "keyed-up", "ghabrahat", "घबराहट", "andar se ghabrahat", "andar hi andar ghabrahat", "घबराया-सा", "घबराया सा", "दिल तेज", "chest tight", "jaw stays tight"),
    "gad_q2_control_worry": ("worry", "loop", "looping", "replay", "mind won't stop", "mind wont stop", "mind keeps running", "mind keeps circling old conversations", "old conversations replay", "replay old conversations", "worry comes back", "दिमाग चलता रहता", "दिमाग को शांत करना मुश्किल", "दिमाग शांत नहीं होता", "दिमाग पुरानी बातें घुमाता रहता है", "dimaag rukta hi nahi", "background mein chalta rehta", "thoughts rukte nahi", "thoughts slow down", "बस thoughts", "चिंता", "सोच बंद", "replaying work stuff", "replay work stuff", "work wali soch chalti rehti hai", "काम की बातें दिमाग में चलती रहती हैं", "soch chalti rehti hai", "चलाते रहती", "चलाते रहता", "mind ko quiet karna tough", "hard to quiet my mind", "it is hard to quiet my mind"),
    "gad_q3_excessive_worry": ("future", "rent", "family", "money", "what if", "work", "job", "exam", "future and job", "job aur future", "work aur future", "future ke around", "whether i will keep my job", "mess up my future", "job ko lekar worry", "future ko lekar worry", "काम", "काम को लेकर", "परिवार", "पैसे", "भविष्य", "भविष्य और नौकरी", "नौकरी और भविष्य", "हर बात", "work mistakes", "money and what that means for my future", "work mistakes money", "काम पैसों और भविष्य", "काम, पैसों और भविष्य", "paise aur future", "काम, पैसों", "काम पैसों"),
    "gad_q4_trouble_relaxing": ("switch off", "settle down", "quiet your thoughts", "quieting my mind", "quiet my mind", "calming my mind", "calm my mind", "hard to calm down", "mind ko quiet karna", "mind ko calm karna", "mind ko shant karna", "mind ko shaant karna", "mind ko shant karna mushkil", "mind ko quiet karna tough", "dimag ko quiet karna", "dimag ko calm karna", "dimag ko shant karna", "दिमाग को शांत करना मुश्किल", "दिमाग शांत नहीं होता", "तनाव", "शांत", "relax", "off karna", "busy mind", "tense body", "body tense", "tense in my body", "body stays tense", "stay tense in my body", "tense lagti", "hard to quiet my mind", "mind ko quiet karna tough hota hai", "ज़्यादा दिमाग को शांत करना मुश्किल"),
    "gad_q5_restlessness": ("restless", "restlessness", "sit still", "pacing", "बेचैनी", "chain se baith", "move around", "feel restless", "बेचैनी और", "restlessness aur"),
    "gad_q6_irritability": ("irritable", "irritability", "snappy", "snappy even though", "चिड़चिड़ापन", "चिड़चिड़ापन दोनों", "irritation", "snappy for no good reason"),
}

TOPIC_SIGNAL_MARKERS: Dict[str, Tuple[str, ...]] = {
    "mood": ("low mood", "sad", "feel down", "feel low", "feel low through most of the day", "low through most of the day", "empty", "days feel heavy", "day feels heavy", "heavy mood", "disconnected", "low aur disconnected feel", "usually enjoy", "used to enjoy", "things i usually care about feel flat", "things i usually care about feel flat before i even start them", "flat lagta", "flat lagti", "flat lagti hai", "flat lagti hain", "flat feel hoti hai", "flat feel hoti hain", "flat underneath", "बहुत कम महसूस", "उदासी", "उदास", "उदासी आती है", "खाली", "low feel", "भारी", "मन भारी", "मन नहीं लगता", "काम करने की इच्छा", "मन जल्दी हट जाता है", "मन हट जाना", "किसी काम से मन हट जाना", "पहले अच्छी लगती थीं", "jo cheezein pehle achhi lagti thi", "jo cheezen pehle achhi lagti thi", "mann hat jata hai", "start karne se pehle hi mann hat jata hai", "kaam mein mann nahi lagta", "kaam me mann nahi lagta", "flat sa lagta hai", "sab flat sa lagta hai", "कटा-कटा", "कटा कटा"),
    "sleep": ("sleep", "asleep", "wake up", "waking", "neend", "नींद", "सोने", "उठ जाती", "night", "रात"),
    "energy": ("tired", "drained", "fatigue", "wiped", "low energy", "energy down", "energy low rehti hai", "din bhar energy low rehti hai", "energy bhi down", "energy bhi low", "energy down ho", "heavy in the morning", "slow to start", "slow to get started", "mind feels slow", "brain fog", "subah heavy", "din ke end", "day ke end", "दिन के अंत", "body heavy", "body feels heavy", "mind is slow to get going", "mind slow start hota hai", "mind slow start hota", "सुबह शुरू होने में बहुत समय लगता है", "thak", "थक", "थका", "थकान", "ऊर्जा", "सुबह भारी", "दिमाग धीमा", "धीमा लग", "aalas", "susti", "सुस्ती", "सुस्त", "आलस", "दिन में आलस", "appetite", "appetite off", "skip meals", "skipping meals", "not eating much", "meals bhi slip ho jaate hain", "meals bhi slip ho jate hain", "bhook", "भूख", "खाना skip", "खाना छोड़"),
    "self_view": ("burden", "extra burden", "burden hoon", "worthless", "useless", "guilt", "make things heavier", "making things heavier", "ashamed", "shame", "wasting everyone's time", "waste everyone's time", "better off without me", "बोझ", "बोझ हूँ", "सबके लिए बोझ", "बेकार", "गलती मेरी", "शर्म", "worthless", "letting people down", "harsh on myself", "hard on myself", "judge myself", "judging myself", "too hard on myself", "खुद को कोसता", "सब पर बोझ", "अपने आप पर गुस्सा", "खुद पर गुस्सा", "क्यों नहीं कर पा रहा", "क्यों नहीं कर पा रही", "khud par harsh", "khud par kaafi harsh", "apne aap par harsh"),
    "focus": ("focus", "concentrat", "attention", "mind blanks", "cannot focus", "can't focus", "harder to focus", "hard to focus", "focus toot", "get started", "taking longer to get started", "takes longer to get started", "mind taking longer", "mind feels slow", "screen", "same screen", "same line", "rereading", "rechecking", "ध्यान", "focus nahi", "ध्यान नहीं", "ध्यान नहीं टिक", "ध्यान भी टिकता नहीं", "ध्यान भी नहीं टिकता", "ध्यान टिकता नहीं", "start hone mein time lagta", "start hone me time lagta", "mind ko start hone mein time lagta", "mind ko start hone me time lagta", "दिमाग धीमा"),
    "anxiety": ("worry", "anxious", "anxiety", "feeling anxious", "very anxious", "restless", "tense", "panic", "loop", "बेचैनी", "चिंता", "घबराहट", "mind won't stop", "quieting my mind", "quiet my mind", "calming my mind", "calm my mind", "mind ko quiet karna", "mind ko calm karna", "mind ko shant karna", "mind ko shaant karna", "दिमाग शांत नहीं होता", "thoughts rukte nahi"),
    "safety": ("hurt myself", "not wake up", "suicide", "मर", "खुद को नुकसान", "zinda na"),
}

AFFECTIVE_TOPIC_FAMILY = {"mood", "sleep", "energy", "self_view", "focus"}
ANXIETY_CORE_ITEMS = {"gad_q1_nervous", "gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}
PHQ_ITEM_IDS = tuple(
    item_id
    for item_id in (
        "phq_q1_anhedonia",
        "phq_q2_low_mood",
        "phq_q3_sleep",
        "phq_q4_fatigue",
        "phq_q5_appetite",
        "phq_q6_worthlessness",
        "phq_q7_concentration",
        "phq_q8_psychomotor",
    )
)
GAD_ITEM_IDS = tuple(
    item_id
    for item_id in (
        "gad_q1_nervous",
        "gad_q2_control_worry",
        "gad_q3_excessive_worry",
        "gad_q4_trouble_relaxing",
        "gad_q5_restlessness",
        "gad_q6_irritability",
        "gad_q7_afraid",
    )
)
TOPIC_TO_DOMAIN = {
    "mood": "phq",
    "sleep": "phq",
    "energy": "phq",
    "self_view": "phq",
    "focus": "phq",
    "anxiety": "gad",
    "safety": "safety",
    "rapport": "rapport",
    "summary": "rapport",
}
SCENE_TO_DOMAIN = {
    "mood_selfview": "phq",
    "sleep_functioning": "phq",
    "worry_shape": "gad",
    "worry_activation": "gad",
}
DOMAIN_SCENES = {
    "phq": ("mood_selfview", "sleep_functioning"),
    "gad": ("worry_shape", "worry_activation"),
}
DOMAIN_TOPICS = {
    "phq": ("mood", "sleep", "energy", "focus", "self_view"),
    "gad": ("anxiety",),
    "safety": ("safety",),
}


@dataclass(frozen=True)
class TopicNode:
    topic_id: str
    label: str
    item_ids: Tuple[str, ...]
    priority: int
    transitions: Tuple[str, ...]


@dataclass(frozen=True)
class SceneNode:
    scene_id: str
    label: str
    anchor_topic: str
    topic_ids: Tuple[str, ...]
    item_ids: Tuple[str, ...]
    priority: int


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
            "gad_q7_afraid",
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

SCENE_GRAPH: Dict[str, SceneNode] = {
    "mood_selfview": SceneNode(
        scene_id="mood_selfview",
        label="Mood, interest, and self-view",
        anchor_topic="mood",
        topic_ids=("mood", "self_view"),
        item_ids=("phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"),
        priority=5,
    ),
    "sleep_functioning": SceneNode(
        scene_id="sleep_functioning",
        label="Sleep and daytime functioning",
        anchor_topic="energy",
        topic_ids=("sleep", "energy", "focus"),
        item_ids=("phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"),
        priority=4,
    ),
    "worry_shape": SceneNode(
        scene_id="worry_shape",
        label="Worry shape and spread",
        anchor_topic="anxiety",
        topic_ids=("anxiety",),
        item_ids=("gad_q1_nervous", "gad_q2_control_worry", "gad_q3_excessive_worry"),
        priority=5,
    ),
    "worry_activation": SceneNode(
        scene_id="worry_activation",
        label="Anxiety activation and arousal",
        anchor_topic="anxiety",
        topic_ids=("anxiety",),
        item_ids=("gad_q4_trouble_relaxing", "gad_q5_restlessness", "gad_q6_irritability", "gad_q7_afraid"),
        priority=4,
    ),
}

ITEM_TO_TOPIC = {
    item_id: node.topic_id
    for node in TOPIC_GRAPH.values()
    for item_id in node.item_ids
}


class DialoguePlanner:
    def _is_item_closed(self, snapshot: ScreeningSnapshot, item_id: str) -> bool:
        if item_id not in snapshot.items:
            return True
        if item_id == "phq_q9_self_harm" and snapshot.safety.level == "urgent":
            return True
        return snapshot.items[item_id].status in {"resolved", "abstained"}

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
                return "Welcome back. What feels most noticeable today, and what feels different from last time?"
        if language == "hi":
            if preferred_name and occupation:
                return f"नमस्ते {preferred_name}। शुक्रिया। {occupation} के रूप में रोज़मर्रा की ज़िंदगी में पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?"
            if context_note:
                return f"शुक्रिया, आप यहाँ आए। {context_note} को ध्यान में रखते हुए पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?"
            if recent_topic:
                return "फिर से स्वागत है। आज सबसे ज़्यादा क्या महसूस हो रहा है, और पिछली बार से क्या अलग लग रहा है?"
        if language == "hinglish":
            if preferred_name and occupation:
                return f"Hi {preferred_name}. Thanks for being here. {occupation} wali day-to-day life mein pichhle do hafton mein sabse zyada kya heavy laga?"
            if context_note:
                return f"Thanks for joining. {context_note} ko dhyan mein rakhte hue pichhle do hafton mein sabse zyada kya heavy laga?"
            if recent_topic:
                return "Welcome back. Aaj sabse zyada kya noticeable lag raha hai, aur last time se kya different hai?"
        return base

    def next_reply(self, snapshot: ScreeningSnapshot, session: ChatSession) -> Tuple[str, Optional[str]]:
        snapshot.coverage = self.build_plan(snapshot, session)
        plan = snapshot.coverage.dialogue
        language = session.language
        latest_user_text = self._latest_user_text(session)
        fresh_anxiety_branch_detail = self._has_worry_domain_signal(latest_user_text) or self._has_new_anxiety_branch_detail(latest_user_text)
        late_anxiety_activation_detail = bool(
            self._latest_signal_items(session) & {"gad_q5_restlessness", "gad_q6_irritability", "gad_q7_afraid"}
        )

        if snapshot.safety.level == "urgent" or plan.next_action == "handoff":
            return SAFETY_MESSAGES[language], plan.target_item
        if self._has_summary_request(latest_user_text):
            last_assistant_text = self._last_assistant_text(session)
            if self._matches_any_segment(
                last_assistant_text,
                (
                    WORKING_SUMMARY_PREFIXES[language],
                    ANXIETY_LOOP_CLOSE_PROMPTS[language],
                    FINAL_HOLD_MESSAGES[language],
                    *FINAL_HOLD_VARIANTS[language],
                ),
            ):
                return self._select_post_close_hold_message(session, language), None
            if plan.summary_ready:
                return self._build_working_summary(snapshot, session), None
        if self._should_use_physical_clarifier(session, latest_user_text):
            return PHYSICAL_CLARIFIER_PROMPTS[language], None
        physical_clarifier_followup = self._physical_clarifier_followup_prompt(session, latest_user_text)
        if physical_clarifier_followup:
            return physical_clarifier_followup, None
        if plan.reopen_signal and plan.target_topic in AFFECTIVE_TOPIC_FAMILY and plan.target_topic != "anxiety":
            prompt = self._build_prompt_for_target(language, plan, session)
            if prompt:
                return self._compose_prompt(language, prompt, plan, session), plan.target_item
        if self._should_close_after_break_answer(session) and not late_anxiety_activation_detail:
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        post_close_reply = None if late_anxiety_activation_detail else self._post_close_followup_reply(session, latest_user_text, language)
        if post_close_reply is not None:
            return post_close_reply, None
        if self._should_break_after_relax_duration_answer(session) and not fresh_anxiety_branch_detail and not late_anxiety_activation_detail:
            if self._has_recent_break_prompt(session, language):
                return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if self._should_close_anxiety_after_scope_answer(plan, session) and not late_anxiety_activation_detail:
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        if self._should_break_after_anxiety_core_rotation(session) and not fresh_anxiety_branch_detail and not late_anxiety_activation_detail:
            if self._has_recent_break_prompt(session, language):
                return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if self._should_close_after_relax_duration_answer(session) and not late_anxiety_activation_detail:
            return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
        if self._should_use_anxiety_loop_break(plan, session) and not fresh_anxiety_branch_detail and not late_anxiety_activation_detail:
            if self._has_recent_break_prompt(session, language) or self._should_close_anxiety_loop(plan, session):
                return ANXIETY_LOOP_CLOSE_PROMPTS[language], None
            return ANXIETY_LOOP_BREAK_PROMPTS[language], None
        if plan.next_action == "summarize" and plan.summary_ready:
            return self._build_working_summary(snapshot, session), None
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
        latest_user_text = self._latest_user_text(session)
        if not self._has_worry_scope_answer(latest_user_text):
            return False
        if session.asked_items[-1] == "gad_q3_excessive_worry":
            return True
        recent_anxiety_items = [
            item_id
            for item_id in session.asked_items[-5:]
            if ITEM_TO_TOPIC.get(item_id) == "anxiety"
        ]
        if len(set(recent_anxiety_items)) < 2:
            return False
        if session.asked_items[-1] != "gad_q4_trouble_relaxing":
            return False
        return (
            "gad_q3_excessive_worry" in recent_anxiety_items
            or "gad_q2_control_worry" in recent_anxiety_items
        )

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

    def _has_recent_break_prompt(self, session: ChatSession, language: str, lookback: int = 6) -> bool:
        normalized_break = self._normalize(ANXIETY_LOOP_BREAK_PROMPTS[language])
        recent_assistant_turns = [
            self._normalize(turn.text)
            for turn in session.turns
            if turn.speaker == "assistant"
        ][-lookback:]
        return any(normalized_break in turn for turn in recent_assistant_turns)

    def _should_break_after_anxiety_core_rotation(self, session: ChatSession) -> bool:
        if not session.asked_items:
            return False
        last_item = session.asked_items[-1]
        if last_item not in ANXIETY_CORE_ITEMS:
            return False
        recent_core = set(self._recent_anxiety_core_items(session))
        recent_core_items = self._recent_anxiety_core_items(session)
        has_contextual_relax_rotation = (
            last_item == "gad_q4_trouble_relaxing"
            and "gad_q2_control_worry" in recent_core
        )
        has_scope_relax_rotation = (
            last_item == "gad_q4_trouble_relaxing"
            and recent_core_items.count("gad_q3_excessive_worry") >= 2
        )
        latest_user_text = self._latest_user_text(session)
        if (
            last_item == "gad_q3_excessive_worry"
            and "gad_q2_control_worry" in recent_core
            and latest_user_text
            and not self._has_new_anxiety_branch_detail(latest_user_text)
            and not self._has_worry_scope_answer(latest_user_text)
            and not self._has_worry_domain_signal(latest_user_text)
        ):
            return True
        if (
            not self._has_recent_anxiety_core_coverage(session)
            and not has_contextual_relax_rotation
            and not has_scope_relax_rotation
        ):
            return False
        if not latest_user_text:
            return False
        if self._has_high_priority_post_close_signal(latest_user_text):
            return False
        if has_contextual_relax_rotation and self._is_repetitive_persistent_worry_echo(latest_user_text):
            return True
        if self._has_timing_or_frequency_answer(latest_user_text):
            if last_item in {"gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}:
                return True
            return self._recent_post_close_turn_count(session, session.language) >= 1
        if self._has_worry_scope_answer(latest_user_text):
            return True
        if self._has_worry_domain_signal(latest_user_text) and last_item in {"gad_q1_nervous", "gad_q4_trouble_relaxing"}:
            return True
        if self._is_nonexpansive_followup(latest_user_text):
            return True
        if self._has_persistent_worry_signal(latest_user_text) and not self._has_worry_domain_signal(latest_user_text):
            return True
        return False

    def _topic_domain(self, topic_id: Optional[str]) -> str:
        return TOPIC_TO_DOMAIN.get(str(topic_id or "rapport"), "rapport")

    def _domain_queue_items(
        self,
        snapshot: ScreeningSnapshot,
        domain: str,
        held_back_items: Iterable[str],
    ) -> list[str]:
        if domain == "phq":
            domain_items = PHQ_ITEM_IDS
        elif domain == "gad":
            domain_items = GAD_ITEM_IDS
        elif domain == "safety":
            domain_items = ("phq_q9_self_harm",)
        else:
            return []
        held_back = set(held_back_items)
        return [
            item_id
            for item_id in domain_items
            if item_id in snapshot.items
            and item_id not in held_back
            and not self._is_item_closed(snapshot, item_id)
        ]

    def _select_active_domain(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: Iterable[str],
    ) -> tuple[str, bool]:
        if snapshot.safety.level in {"urgent", "review"} and "phq_q9_self_harm" not in set(held_back_items):
            return "safety", True

        latest_user_text = self._latest_user_text(session)
        latest_signal_topics = self._latest_signal_topics(session)
        latest_signal_items = self._latest_signal_items(session)
        recent_signal_topics = self._recent_signal_topics(session)
        phq_queue = self._domain_queue_items(snapshot, "phq", held_back_items)
        gad_queue = self._domain_queue_items(snapshot, "gad", held_back_items)
        last_domain = session.domain_history[-1] if session.domain_history else None
        last_item = session.asked_items[-1] if session.asked_items else None

        anxiety_downplayed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        phq_hits = sum(1 for item_id in latest_signal_items if item_id in PHQ_ITEM_IDS)
        phq_hits += sum(1 for topic_id in latest_signal_topics if topic_id in AFFECTIVE_TOPIC_FAMILY)
        gad_hits = sum(1 for item_id in latest_signal_items if item_id in GAD_ITEM_IDS)
        gad_hits += sum(1 for topic_id in latest_signal_topics if topic_id == "anxiety")

        if (
            self._has_flat_functioning_signal(latest_user_text)
            and not latest_signal_items.intersection(GAD_ITEM_IDS)
            and not self._has_strong_anxiety_domain_signal(latest_user_text)
        ):
            return "phq", True

        if last_item == "phq_q3_sleep" and (
            self._has_sleep_pattern_answer(latest_user_text)
            or self._has_sleep_impact_signal(latest_user_text)
            or "phq_q3_sleep" in latest_signal_items
        ):
            return "phq", True

        if not anxiety_downplayed and (
            self._has_strong_anxiety_domain_signal(latest_user_text)
            or ("anxiety" in latest_signal_topics and phq_hits <= 1)
            or gad_hits >= 2
        ):
            return "gad", True
        if not anxiety_downplayed and latest_signal_items.intersection(GAD_ITEM_IDS) and phq_hits == 0:
            return "gad", True

        if (
            last_domain == "gad"
            and last_item in GAD_ITEM_IDS
            and self._has_timing_or_frequency_answer(latest_user_text)
            and not latest_signal_items.intersection(PHQ_ITEM_IDS)
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_sleep_impact_signal(latest_user_text)
        ):
            return "gad", True

        if phq_hits > 0:
            return "phq", True

        if last_domain in {"phq", "gad"}:
            last_domain_queue = self._domain_queue_items(snapshot, last_domain, held_back_items)
            opposite_domain = "gad" if last_domain == "phq" else "phq"
            opposite_queue = self._domain_queue_items(snapshot, opposite_domain, held_back_items)
            recent_opposite_signal = bool(
                ("anxiety" in recent_signal_topics and opposite_domain == "gad")
                or (recent_signal_topics & AFFECTIVE_TOPIC_FAMILY and opposite_domain == "phq")
                or any(item_id in GAD_ITEM_IDS for item_id in latest_signal_items) and opposite_domain == "gad"
                or any(item_id in PHQ_ITEM_IDS for item_id in latest_signal_items) and opposite_domain == "phq"
            )
            if last_domain_queue and not recent_opposite_signal:
                return last_domain, True
            if last_domain_queue and len(opposite_queue) <= len(last_domain_queue):
                return last_domain, False

        target_domain = self._topic_domain(target_topic)
        if target_domain in {"phq", "gad"}:
            return target_domain, False
        if phq_queue and not gad_queue:
            return "phq", False
        if gad_queue and not phq_queue:
            return "gad", False
        if len(phq_queue) >= len(gad_queue):
            return "phq", False
        if gad_queue:
            return "gad", False
        return "rapport", False

    def _blocked_recent_items(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        domain: str,
    ) -> list[str]:
        domain_items = set(PHQ_ITEM_IDS if domain == "phq" else GAD_ITEM_IDS if domain == "gad" else ())
        blocked: list[str] = []
        for item_id in [*session.blocked_items[-8:], *session.asked_items[-3:]]:
            if item_id not in snapshot.items:
                continue
            if domain_items and item_id not in domain_items:
                continue
            blocked.append(item_id)
            if snapshot.items[item_id].status == "resolved":
                blocked.append(item_id)
        return list(dict.fromkeys(blocked))

    def _select_domain_topic(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        domain: str,
        target_topic: str,
        held_back_items: Iterable[str],
        current_topic: str,
    ) -> str:
        if domain == "gad":
            return "anxiety"
        if domain == "safety":
            return "safety"

        latest_user_text = self._latest_user_text(session)
        latest_signal_topics = self._latest_signal_topics(session)
        latest_signal_items = self._latest_signal_items(session)
        recent_topics = [ITEM_TO_TOPIC.get(item_id) for item_id in session.asked_items[-4:] if ITEM_TO_TOPIC.get(item_id)]
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        if (
            domain == "phq"
            and session.asked_items[-1:] == ["phq_q3_sleep"]
            and self._has_self_view_signal(latest_user_text)
        ):
            return "self_view"
        if (
            domain == "phq"
            and session.asked_items[-1:] == ["phq_q3_sleep"]
            and self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics)
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_sleep_impact_signal(latest_user_text)
        ):
            if self._has_self_view_signal(latest_user_text) or "phq_q6_worthlessness" in latest_signal_items:
                return "self_view"
            focus_signal_items = {"phq_q7_concentration", "phq_q8_psychomotor"} & latest_signal_items
            energy_signal_items = {"phq_q4_fatigue", "phq_q5_appetite"} & latest_signal_items
            if focus_signal_items and not energy_signal_items:
                return "focus"
            return "energy"
        if domain == "phq" and (
            "sleep" in latest_signal_topics or "phq_q3_sleep" in latest_signal_items
        ) and (user_turn_count <= 1 or session.asked_items[-1:] == ["phq_q3_sleep"]):
            return "sleep"
        if domain == "phq" and session.asked_items[-1:] == ["phq_q2_low_mood"] and latest_signal_items == {"phq_q2_low_mood"}:
            return "mood"
        if (
            domain == "phq"
            and session.asked_items[-1:] == ["phq_q2_low_mood"]
            and self._has_flat_functioning_signal(latest_user_text)
            and not self._has_self_view_signal(latest_user_text)
        ):
            if (
                self._has_functional_impact_answer(latest_user_text)
                and snapshot.items["phq_q7_concentration"].status != "resolved"
                and "phq_q7_concentration" not in set(held_back_items)
            ):
                return "focus"
            return "mood"
        candidates = []
        for topic_id in DOMAIN_TOPICS.get(domain, ()):
            unresolved = [
                item_id
                for item_id in TOPIC_GRAPH[topic_id].item_ids
                if item_id not in set(held_back_items) and snapshot.items[item_id].status != "resolved"
            ]
            if not unresolved:
                continue
            score = len(unresolved) * 8 + self._topic_coverage_boost(snapshot, topic_id) * 2
            if topic_id in latest_signal_topics:
                score += 18
            if any(item_id in latest_signal_items for item_id in unresolved):
                score += 14
            if topic_id == target_topic:
                score += 12
            if topic_id == current_topic:
                score += 6
            if recent_topics and topic_id == recent_topics[-1]:
                score += 4
            if recent_topics.count(topic_id) >= 2:
                score -= 10
            if topic_id == "sleep" and "phq_q3_sleep" in latest_signal_items:
                score += 16
            if topic_id == "self_view" and "phq_q6_worthlessness" in latest_signal_items:
                score += 16
            if topic_id == "focus" and "phq_q7_concentration" in latest_signal_items:
                score += 16
            if topic_id == "mood" and (
                "phq_q1_anhedonia" in latest_signal_items or "phq_q2_low_mood" in latest_signal_items
            ):
                score += 16
            candidates.append((score, topic_id))
        if not candidates:
            return target_topic if self._topic_domain(target_topic) == domain else ("mood" if domain == "phq" else "anxiety")
        candidates.sort(reverse=True)
        return candidates[0][1]

    def _select_domain_scene(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        domain: str,
        target_topic: str,
        target_scene: Optional[str],
        held_back_items: Iterable[str],
    ) -> Optional[str]:
        if domain not in DOMAIN_SCENES:
            return None
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        recent_scenes = session.scene_history[-2:]
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)
        last_item = session.asked_items[-1] if session.asked_items else None
        signal_scene_count = 0
        if domain == "phq":
            signal_scene_count = int(bool(latest_signal_topics & {"mood", "self_view"})) + int(bool(latest_signal_topics & {"sleep", "energy", "focus"}))
        elif domain == "gad":
            signal_scene_count = int(bool(latest_signal_topics & {"anxiety"}))
        if not target_scene and user_turn_count < 4 and not recent_scenes and signal_scene_count < 2:
            return None
        if domain == "phq" and target_topic == "mood" and last_item == "phq_q2_low_mood" and latest_signal_items == {"phq_q2_low_mood"}:
            return "mood_selfview"

        def scene_score(scene_id: str) -> Optional[tuple[int, str]]:
            scene = SCENE_GRAPH[scene_id]
            unresolved = self._scene_unresolved_items(snapshot, scene, held_back_items)
            if not unresolved:
                return None
            score = len(unresolved) * 10 + scene.priority * 6
            if target_topic in scene.topic_ids:
                score += 10
            if any(item_id in latest_signal_items for item_id in unresolved):
                score += 18
            if any(topic_id in latest_signal_topics for topic_id in scene.topic_ids):
                score += 12
            if any(snapshot.items[item_id].status in {"partial", "contradicted", "abstained"} for item_id in unresolved):
                score += 8
            if scene_id == target_scene:
                score += 4
            if target_topic in {"mood", "self_view"} and scene_id == "mood_selfview":
                score += 22
            if target_topic in {"sleep", "energy", "focus"} and scene_id == "sleep_functioning":
                score += 22
            if recent_scenes.count(scene_id) >= 2:
                score -= 24
            elif recent_scenes[-1:] == [scene_id]:
                score -= 10
            return score, scene_id

        ranked = [candidate for scene_id in DOMAIN_SCENES[domain] if (candidate := scene_score(scene_id)) is not None]
        if not ranked:
            return None
        ranked.sort(reverse=True)
        return ranked[0][1]

    def _select_domain_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        domain: str,
        target_topic: str,
        target_scene: Optional[str],
        target_item: Optional[str],
        held_back_items: Iterable[str],
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> Optional[str]:
        blocked = set(self._blocked_recent_items(snapshot, session, domain))
        latest_user_text = self._latest_user_text(session)
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)
        hold_current = self._should_hold_current_answer(
            session.asked_items[-1] if session.asked_items else None,
            latest_user_text,
            latest_signal_items,
            latest_signal_topics,
        )
        last_item = session.asked_items[-1] if session.asked_items else None
        prior_user_turns = [turn for turn in session.turns if turn.speaker == "user"][:-1]
        prior_anhedonia_signal = any(self._has_anhedonia_signal(self._normalize(turn.text)) for turn in prior_user_turns)
        prior_low_mood_signal = any(self._has_low_mood_signal(self._normalize(turn.text)) for turn in prior_user_turns)
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        if domain == "phq" and target_topic == "sleep" and not session.asked_items and (
            self._has_sleep_pattern_answer(latest_user_text)
            or self._has_sleep_impact_signal(latest_user_text)
            or "phq_q3_sleep" in latest_signal_items
            or user_turn_count <= 1
        ):
            if snapshot.items["phq_q3_sleep"].status == "resolved":
                return None
            return "phq_q3_sleep"
        if domain == "gad":
            if (
                last_item == "gad_q2_control_worry"
                and self._has_worry_domain_signal(latest_user_text)
            ):
                if (
                    session.asked_items.count("gad_q4_trouble_relaxing") >= 1
                    and "gad_q3_excessive_worry" in snapshot.items
                    and snapshot.items["gad_q3_excessive_worry"].status != "abstained"
                ):
                    return "gad_q3_excessive_worry"
                if (
                    "gad_q4_trouble_relaxing" in snapshot.items
                    and snapshot.items["gad_q4_trouble_relaxing"].status != "abstained"
                ):
                    return "gad_q4_trouble_relaxing"
            relax_branch_detail = self._has_lingering_tension_signal(latest_user_text) or (
                "body" in latest_user_text and "tense" in latest_user_text
            )
            if relax_branch_detail and "gad_q4_trouble_relaxing" in snapshot.items:
                if snapshot.items["gad_q4_trouble_relaxing"].status != "abstained":
                    return "gad_q4_trouble_relaxing"
            if (
                self._has_worry_domain_signal(latest_user_text)
                and session.asked_items.count("gad_q3_excessive_worry") >= 2
                and "gad_q4_trouble_relaxing" in snapshot.items
                and snapshot.items["gad_q4_trouble_relaxing"].status != "abstained"
            ):
                return "gad_q4_trouble_relaxing"
            if self._has_worry_domain_signal(latest_user_text) and "gad_q3_excessive_worry" in snapshot.items:
                if snapshot.items["gad_q3_excessive_worry"].status != "abstained":
                    return "gad_q3_excessive_worry"
        if domain == "phq" and last_item == "phq_q2_low_mood":
            if (
                self._has_flat_functioning_signal(latest_user_text)
                and self._has_functional_impact_answer(latest_user_text)
                and "phq_q7_concentration" in snapshot.items
                and snapshot.items["phq_q7_concentration"].status != "resolved"
                and "phq_q7_concentration" not in held_back_items
            ):
                return "phq_q7_concentration"
            if self._has_flat_functioning_signal(latest_user_text):
                return "phq_q2_low_mood"
            if (
                self._has_anhedonia_signal(latest_user_text)
                and snapshot.items["phq_q2_low_mood"].status != "resolved"
                and session.asked_items.count("phq_q1_anhedonia") >= 1
            ):
                return "phq_q2_low_mood"
            if (
                self._has_anhedonia_signal(latest_user_text)
                and not self._has_low_mood_signal(latest_user_text)
                and snapshot.items["phq_q1_anhedonia"].status == "resolved"
                and prior_anhedonia_signal
                and not prior_low_mood_signal
            ):
                for preferred_item in ("phq_q6_worthlessness", "phq_q7_concentration", "phq_q5_appetite"):
                    if (
                        preferred_item in snapshot.items
                        and snapshot.items[preferred_item].status != "resolved"
                        and preferred_item not in held_back_items
                    ):
                        return preferred_item
        if (
            domain == "phq"
            and target_scene == "sleep_functioning"
            and last_item == "phq_q3_sleep"
        ):
            energy_signal_items = {"phq_q4_fatigue", "phq_q5_appetite"} & latest_signal_items
            focus_signal_items = {"phq_q7_concentration", "phq_q8_psychomotor"} & latest_signal_items
            if energy_signal_items and not focus_signal_items:
                for preferred_item in ("phq_q5_appetite", "phq_q4_fatigue"):
                    if (
                        preferred_item in energy_signal_items
                        and preferred_item in snapshot.items
                        and snapshot.items[preferred_item].status != "resolved"
                        and preferred_item not in held_back_items
                    ):
                        return preferred_item
                return None
        if (
            domain == "phq"
            and last_item == "phq_q3_sleep"
            and self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_frequency_answer(latest_user_text)
            and "phq_q3_sleep" in snapshot.items
        ):
            return "phq_q3_sleep"
        if (
            domain == "phq"
            and last_item == "phq_q3_sleep"
            and self._has_self_view_signal(latest_user_text)
            and "phq_q6_worthlessness" in snapshot.items
            and snapshot.items["phq_q6_worthlessness"].status != "abstained"
            and "phq_q6_worthlessness" not in held_back_items
        ):
            return "phq_q6_worthlessness"
        if (
            domain == "gad"
            and last_item == "gad_q5_restlessness"
            and self._has_timing_or_frequency_answer(latest_user_text)
        ):
            if "gad_q5_restlessness" in snapshot.items and snapshot.items["gad_q5_restlessness"].status != "abstained":
                return "gad_q5_restlessness"
        if domain == "gad" and last_item == "gad_q4_trouble_relaxing":
            if (
                "gad_q6_irritability" in latest_signal_items
                and "gad_q6_irritability" in snapshot.items
                and snapshot.items["gad_q6_irritability"].status != "abstained"
                and "gad_q6_irritability" not in held_back_items
            ):
                return "gad_q6_irritability"
            if (
                "gad_q5_restlessness" in latest_signal_items
                and "gad_q5_restlessness" in snapshot.items
                and snapshot.items["gad_q5_restlessness"].status != "abstained"
                and "gad_q5_restlessness" not in held_back_items
            ):
                return "gad_q5_restlessness"
        if target_item and target_item in snapshot.items and snapshot.items[target_item].status != "resolved":
            target_item_topic = ITEM_TO_TOPIC.get(target_item)
            target_item_allowed = (
                target_item_topic == target_topic
                or (target_scene and target_item in SCENE_GRAPH[target_scene].item_ids)
                or target_item in latest_signal_items
            )
            if self._topic_domain(target_item_topic) == domain and target_item_allowed and (hold_current or target_item not in blocked):
                return target_item

        candidates: list[str] = []
        if target_scene and target_scene in SCENE_GRAPH:
            candidates = [
                item_id
                for item_id in self._scene_unresolved_items(snapshot, SCENE_GRAPH[target_scene], held_back_items)
                if self._topic_domain(ITEM_TO_TOPIC.get(item_id)) == domain
            ]
            if not candidates and target_scene == "mood_selfview":
                return None
        if not candidates:
            candidates = [
                item_id
                for item_id in self._domain_queue_items(snapshot, domain, held_back_items)
                if ITEM_TO_TOPIC.get(item_id) == target_topic or target_topic == "anxiety"
            ]
        if not candidates:
            candidates = self._domain_queue_items(snapshot, domain, held_back_items)
        if not candidates:
            return None

        def rank(item_id: str) -> tuple[int, int]:
            score = self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style)
            if item_id in blocked and not (hold_current and item_id == last_item):
                score -= 28
            if item_id == last_item:
                score -= 18
            if item_id in latest_signal_items:
                score += 12
            if snapshot.items[item_id].status in {"partial", "contradicted", "abstained"}:
                score += 10
            if domain == "gad":
                if item_id in {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}:
                    score += 18
                if item_id == "gad_q1_nervous" and session.asked_items:
                    score -= 20
            return score, ITEM_INDEX[item_id].priority

        unblocked = [item_id for item_id in candidates if item_id not in blocked]
        pool = unblocked or candidates
        pool.sort(key=rank, reverse=True)
        return pool[0]

    def _should_force_closure_mode(
        self,
        session: ChatSession,
        active_domain: str,
        phq_queue: list[str],
        gad_queue: list[str],
        target_scene: Optional[str],
    ) -> bool:
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        active_queue = phq_queue if active_domain == "phq" else gad_queue if active_domain == "gad" else []
        if user_turn_count < 4 or not active_queue:
            return False
        if len(set(session.asked_items[-3:])) < len(session.asked_items[-3:]):
            return True
        if target_scene and session.scene_history[-2:].count(target_scene) >= 1:
            return True
        if len(active_queue) <= 4:
            return True
        return user_turn_count >= 5

    def build_plan(self, snapshot: ScreeningSnapshot, session: ChatSession) -> CoveragePlan:
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        held_back_items = self._held_back_items(snapshot, session)
        phq_queue = self._domain_queue_items(snapshot, "phq", held_back_items)
        gad_queue = self._domain_queue_items(snapshot, "gad", held_back_items)
        remaining_closeout = len(phq_queue) + len(gad_queue)
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
        latest_user_text = self._latest_user_text(session)
        continue_intent = self._has_continue_signal(latest_user_text)
        summary_request = self._has_summary_request(latest_user_text)
        anxiety_downplayed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        strong_anxiety_domain_signal = self._has_strong_anxiety_domain_signal(latest_user_text)
        reopen_signal = self._should_reopen_after_close(session, latest_user_text)
        readiness = self._infer_readiness(snapshot, session, topic_states, user_style)
        fatigue = self._infer_fatigue(snapshot, session)
        stage = self._select_stage(
            snapshot,
            session,
            topic_states,
            len(user_turns),
            held_back_items,
            phq_queue,
            gad_queue,
            readiness,
            fatigue,
            continue_intent,
            reopen_signal,
            summary_request,
        )
        continuity_item = self._continuity_item(snapshot, session, held_back_items, fatigue)
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
        coverage_debt = self._coverage_debt_topics(topic_states, session)
        closure_mode = self._should_enter_closure_mode(
            snapshot,
            session,
            topic_states,
            stage,
            coverage_debt,
            phq_queue,
            gad_queue,
            disclosure,
            readiness,
            fatigue,
            continue_intent,
            reopen_signal,
            summary_request,
        )
        target_scene = self._select_bridge_scene(
            snapshot,
            session,
            target_topic,
            held_back_items,
        )
        if not target_scene:
            target_scene = self._select_target_scene(
                snapshot,
                session,
                target_topic,
                topic_states,
                held_back_items,
                closure_mode,
                fatigue,
                user_style,
            )
        scene_item_ids = list(SCENE_GRAPH[target_scene].item_ids) if target_scene else []
        if target_scene:
            target_topic = SCENE_GRAPH[target_scene].anchor_topic
        if (
            strong_anxiety_domain_signal
            and not anxiety_downplayed
            and target_topic != "anxiety"
            and not (
                session.asked_items
                and session.asked_items[-1] == "phq_q3_sleep"
                and self._has_sleep_pattern_answer(latest_user_text)
            )
        ):
            target_scene = None
            scene_item_ids = []
            target_topic = "anxiety"
        target_item = self._select_scene_target_item(
            snapshot,
            session,
            target_scene,
            target_topic,
            held_back_items,
            fatigue,
            user_style,
        )
        if target_topic == "anxiety":
            directed_anxiety_item = self._directed_followup_item(snapshot, session, target_topic, held_back_items)
            if directed_anxiety_item is not None:
                target_item = directed_anxiety_item
        if target_item is None:
            target_item = self._select_target_item(snapshot, session, target_topic, held_back_items, fatigue, user_style)
        latest_resolved_signal = any(
            item_id in snapshot.items and snapshot.items[item_id].status == "resolved"
            for item_id in self._latest_signal_items(session)
        )
        forced_scene = None
        if (
            target_scene is None
            and not (not session.asked_items and target_topic == "sleep")
            and not continuity_item
            and (
            target_item is None
            or (
                session.asked_items
                and target_item == session.asked_items[-1]
                and latest_resolved_signal
            )
            )
        ):
            forced_scene = self._force_scene_followup(snapshot, session, target_topic, held_back_items)
        if forced_scene:
            rotated_item = self._select_scene_target_item(
                snapshot,
                session,
                forced_scene,
                target_topic,
                held_back_items,
                fatigue,
                user_style,
            )
            if rotated_item and rotated_item != target_item:
                target_scene = forced_scene
                scene_item_ids = list(SCENE_GRAPH[target_scene].item_ids)
                target_topic = SCENE_GRAPH[target_scene].anchor_topic
                target_item = rotated_item
        if (
            target_topic == "anxiety"
            and "gad_q3_excessive_worry" not in held_back_items
            and snapshot.items["gad_q3_excessive_worry"].status != "resolved"
            and (
                self._should_break_after_anxiety_core_rotation(session)
                or self._should_break_after_relax_duration_answer(session)
            )
            and not self._has_worry_domain_signal(latest_user_text)
        ):
            target_item = "gad_q3_excessive_worry"
            target_scene = None
            scene_item_ids = []
        if (
            target_item
            and ITEM_TO_TOPIC.get(target_item)
            and ITEM_TO_TOPIC.get(target_item) != target_topic
            and not (
                target_scene
                and ITEM_TO_TOPIC.get(target_item) in SCENE_GRAPH[target_scene].topic_ids
            )
        ):
            target_topic = ITEM_TO_TOPIC[target_item]

        active_domain, domain_locked = self._select_active_domain(
            snapshot,
            session,
            target_topic,
            held_back_items,
        )
        target_topic = self._select_domain_topic(
            snapshot,
            session,
            active_domain,
            target_topic,
            held_back_items,
            current_topic,
        )
        target_scene = self._select_domain_scene(
            snapshot,
            session,
            active_domain,
            target_topic,
            target_scene,
            held_back_items,
        )
        if target_scene:
            scene_item_ids = list(SCENE_GRAPH[target_scene].item_ids)
            if target_topic not in SCENE_GRAPH[target_scene].topic_ids:
                target_topic = SCENE_GRAPH[target_scene].anchor_topic
        else:
            scene_item_ids = []
        target_item = self._select_domain_item(
            snapshot,
            session,
            active_domain,
            target_topic,
            target_scene,
            target_item,
            held_back_items,
            fatigue,
            user_style,
        )
        if (
            target_item
            and ITEM_TO_TOPIC.get(target_item)
            and not (
                target_scene == "sleep_functioning"
                and target_topic == "energy"
                and target_item == "phq_q8_psychomotor"
            )
        ):
            target_topic = ITEM_TO_TOPIC[target_item]
        if (
            active_domain in DOMAIN_SCENES
            and target_item
            and target_scene
            and target_scene in SCENE_GRAPH
            and target_item not in SCENE_GRAPH[target_scene].item_ids
        ):
            aligned_scene = next(
                (
                    scene_id
                    for scene_id in DOMAIN_SCENES[active_domain]
                    if target_item in SCENE_GRAPH[scene_id].item_ids
                ),
                None,
            )
            if aligned_scene:
                target_scene = aligned_scene
                scene_item_ids = list(SCENE_GRAPH[target_scene].item_ids)
                if target_topic not in SCENE_GRAPH[target_scene].topic_ids:
                    target_topic = SCENE_GRAPH[target_scene].anchor_topic
        blocked_items = self._blocked_recent_items(snapshot, session, active_domain)
        closure_mode = closure_mode or self._should_force_closure_mode(
            session,
            active_domain,
            phq_queue,
            gad_queue,
            target_scene,
        )
        if stage == "summary" and remaining_closeout > 0:
            stage = "clarification" if snapshot.coverage.touched_items >= 2 else "exploration"
            closure_mode = True
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
            target_scene=target_scene,
            scene_item_ids=scene_item_ids,
            closure_mode=closure_mode,
            rationale=self._build_rationale(snapshot, target_topic, topic_states, held_back_items, target_scene),
            user_turns=len(user_turns),
            low_confidence_topics=low_confidence_topics,
            covered_topics=covered_topics,
            held_back_items=held_back_items,
            transition_hint=self._build_transition_hint(current_topic, target_topic, stage, user_style, fatigue, readiness),
            user_style=user_style,
            disclosure=disclosure,
            readiness=readiness,
            fatigue=fatigue,
            coverage_debt=coverage_debt,
            continue_intent=continue_intent,
            reopen_signal=reopen_signal,
            summary_ready=remaining_closeout == 0 and not snapshot.safety.needs_human_review and (
                summary_request
                or stage == "summary"
                or snapshot.coverage.touched_items >= MIN_SUMMARY_TOUCHES
                or snapshot.coverage.completion_ratio >= 0.78
            ),
            reflective_anchor=reflective_anchor,
            continuity_note=continuity_note,
            recommended_nudges=recommended_nudges,
            active_domain=active_domain,
            domain_locked=domain_locked,
            phq_queue=phq_queue,
            gad_queue=gad_queue,
            blocked_items=blocked_items,
            recent_scenes=session.scene_history[-4:],
            recent_items=session.asked_items[-4:],
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

    def _coverage_debt_topics(self, topic_states: list[TopicState], session: ChatSession) -> list[str]:
        priority_topics: list[str] = []
        latest_signal_topics = [topic for topic in self._latest_signal_topics(session) if topic in TOPIC_GRAPH]
        recent_signal_topics = [topic for topic in self._recent_signal_topics(session) if topic in TOPIC_GRAPH]
        for topic_id in latest_signal_topics + recent_signal_topics:
            if topic_id not in priority_topics:
                priority_topics.append(topic_id)

        active_topics = [
            topic.topic_id
            for topic in topic_states
            if topic.topic_id != "safety" and topic.status in {"probing", "review"} and (topic.unresolved_items or topic.review_items)
        ]
        for topic_id in active_topics:
            if topic_id not in priority_topics:
                priority_topics.append(topic_id)

        pending_topics = [
            topic.topic_id
            for topic in topic_states
            if topic.topic_id != "safety" and topic.status == "pending" and topic.priority >= 2
        ]
        for topic_id in pending_topics:
            if topic_id not in priority_topics:
                priority_topics.append(topic_id)
        return priority_topics[:4]

    def _scene_unresolved_items(
        self,
        snapshot: ScreeningSnapshot,
        scene: SceneNode,
        held_back_items: Iterable[str],
    ) -> list[str]:
        held_back = set(held_back_items)
        return [
            item_id
            for item_id in scene.item_ids
            if item_id not in held_back and snapshot.items[item_id].status != "resolved"
        ]

    def _scene_coverage_debt(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        held_back_items: Iterable[str],
    ) -> list[str]:
        latest_signal_topics = self._latest_signal_topics(session)
        recent_signal_topics = self._recent_signal_topics(session)
        latest_signal_items = self._latest_signal_items(session)
        recent_signal_items = self._recent_signal_items(session)
        current_topic = self._infer_current_topic(snapshot, session)
        ranked: list[tuple[int, str]] = []

        for scene_id, scene in SCENE_GRAPH.items():
            unresolved_items = self._scene_unresolved_items(snapshot, scene, held_back_items)
            if not unresolved_items:
                continue
            if (
                len(unresolved_items) < 2
                and not any(item_id in latest_signal_items for item_id in unresolved_items)
                and not any(topic_id in latest_signal_topics for topic_id in scene.topic_ids)
            ):
                continue

            score = scene.priority * 10
            score += len(unresolved_items) * 8
            score += sum(UNDERCOVERED_ITEM_BOOSTS.get(item_id, 0) for item_id in unresolved_items) * 2
            if scene.anchor_topic == current_topic:
                score += 8
            if any(topic_id in latest_signal_topics for topic_id in scene.topic_ids):
                score += 14
            elif any(topic_id in recent_signal_topics for topic_id in scene.topic_ids):
                score += 8
            if any(item_id in latest_signal_items for item_id in unresolved_items):
                score += 16
            elif any(item_id in recent_signal_items for item_id in unresolved_items):
                score += 8
            if any(snapshot.items[item_id].status in {"partial", "contradicted", "abstained"} for item_id in unresolved_items):
                score += 8
            if sum(bool(snapshot.items[item_id].evidence_span_ids) for item_id in unresolved_items) <= 1:
                score += 4
            ranked.append((score, scene_id))

        ranked.sort(reverse=True)
        return [scene_id for _, scene_id in ranked]

    def _should_enter_closure_mode(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        topic_states: list[TopicState],
        stage: str,
        coverage_debt: list[str],
        phq_queue: list[str],
        gad_queue: list[str],
        disclosure: DisclosureMetrics,
        readiness: ReadinessLevel,
        fatigue: FatigueLevel,
        continue_intent: bool,
        reopen_signal: bool,
        summary_request: bool,
    ) -> bool:
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        remaining_closeout = len(phq_queue) + len(gad_queue)
        if stage in {"rapport", "safety"} or remaining_closeout == 0:
            return False

        scene_debt = self._scene_coverage_debt(snapshot, session, [])
        if not scene_debt:
            return user_turn_count >= 4 and remaining_closeout > 0
        if summary_request:
            return True
        if user_turn_count < 4:
            return (
                user_turn_count >= 2
                and remaining_closeout > 0
                and (
                    continue_intent
                    or (
                        user_turn_count >= 3
                        and (
                            disclosure.resolved_per_user_turn >= 2.0
                            or disclosure.items_per_user_turn >= 2.2
                        )
                    )
                )
            )
        if continue_intent or reopen_signal:
            return True
        if remaining_closeout <= 8:
            return True
        if readiness == "ready_to_close" and snapshot.coverage.completion_ratio < 0.8:
            return True

        open_topics = [
            topic
            for topic in topic_states
            if topic.topic_id != "safety" and (topic.unresolved_items or topic.review_items)
        ]
        if fatigue == "high":
            return len(scene_debt) >= 1
        if snapshot.coverage.touched_items < 8 and len(scene_debt) >= 2:
            return True
        if len(coverage_debt) >= 2 and len(open_topics) >= 2:
            return True
        return user_turn_count >= 5 and remaining_closeout > 0

    def _select_target_scene(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        topic_states: list[TopicState],
        held_back_items: list[str],
        closure_mode: bool,
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> Optional[str]:
        if not closure_mode or target_topic in {"rapport", "summary", "safety"}:
            return None
        if self._continuity_item(snapshot, session, held_back_items, fatigue):
            return None
        if self._fresh_signal_preemption_item(snapshot, session, target_topic, held_back_items, fatigue, user_style):
            return None
        if self._directed_followup_item(snapshot, session, target_topic, held_back_items):
            return None

        scene_debt = self._scene_coverage_debt(snapshot, session, held_back_items)
        if not scene_debt:
            return None

        latest_user_text = self._latest_user_text(session)
        latest_signal_topics = self._latest_signal_topics(session)
        recent_signal_topics = self._recent_signal_topics(session)
        latest_affective_signal_active = bool(latest_signal_topics & AFFECTIVE_TOPIC_FAMILY)
        latest_anxiety_signal_active = "anxiety" in latest_signal_topics
        anxiety_signal_active = "anxiety" in (latest_signal_topics | recent_signal_topics)
        anxiety_evidence_active = any(snapshot.items[item_id].evidence_span_ids for item_id in ANXIETY_CORE_ITEMS)
        affective_debt_active = any(
            topic.topic_id in AFFECTIVE_TOPIC_FAMILY and topic.unresolved_items
            for topic in topic_states
        )
        if target_topic in AFFECTIVE_TOPIC_FAMILY and latest_affective_signal_active and not latest_anxiety_signal_active:
            non_anxiety_scene_debt = [
                scene_id
                for scene_id in scene_debt
                if SCENE_GRAPH[scene_id].anchor_topic != "anxiety"
            ]
            if non_anxiety_scene_debt:
                scene_debt = non_anxiety_scene_debt
        if affective_debt_active and not anxiety_signal_active and not anxiety_evidence_active:
            non_anxiety_scene_debt = [
                scene_id
                for scene_id in scene_debt
                if SCENE_GRAPH[scene_id].anchor_topic != "anxiety"
            ]
            if non_anxiety_scene_debt:
                scene_debt = non_anxiety_scene_debt
        if self._has_summary_request(latest_user_text) or self._has_continue_signal(latest_user_text):
            latest_signal_items = self._latest_signal_items(session)
            breadth_exhausted_topics = self._breadth_request_exhausted_topics(
                session,
                latest_user_text,
                latest_signal_items,
                latest_signal_topics,
            )
            if breadth_exhausted_topics:
                widened_scene_debt = [
                    scene_id
                    for scene_id in scene_debt
                    if not set(SCENE_GRAPH[scene_id].topic_ids).issubset(breadth_exhausted_topics)
                ]
                if widened_scene_debt:
                    scene_debt = widened_scene_debt
        if "mood_selfview" in scene_debt:
            mood_scene_unresolved = self._scene_unresolved_items(snapshot, SCENE_GRAPH["mood_selfview"], held_back_items)
            if (
                mood_scene_unresolved == ["phq_q6_worthlessness"]
                and session.asked_items[-2:].count("phq_q6_worthlessness") >= 1
                and not self._has_self_view_signal(latest_user_text)
                and (
                    self._has_low_mood_signal(latest_user_text)
                    or self._has_anhedonia_signal(latest_user_text)
                )
            ):
                alternative_scene_debt = [scene_id for scene_id in scene_debt if scene_id != "mood_selfview"]
                if alternative_scene_debt:
                    scene_debt = alternative_scene_debt

        current_topic = self._infer_current_topic(snapshot, session)
        latest_signal_items = self._latest_signal_items(session)
        direct_signal_topics = {
            topic_id
            for topic_id in (
                latest_signal_topics
                | {ITEM_TO_TOPIC.get(item_id) for item_id in latest_signal_items if ITEM_TO_TOPIC.get(item_id)}
            )
            if topic_id
        }
        target_state = next((topic for topic in topic_states if topic.topic_id == target_topic), None)
        direct_unresolved_hits = [
            item_id
            for item_id in latest_signal_items
            if ITEM_TO_TOPIC.get(item_id) == target_topic
            and target_state is not None
            and item_id in target_state.unresolved_items
        ]
        if direct_signal_topics == {target_topic} and direct_unresolved_hits:
            return None

        def rank(scene_id: str) -> tuple[int, int, int, int, int]:
            scene = SCENE_GRAPH[scene_id]
            unresolved_items = self._scene_unresolved_items(snapshot, scene, held_back_items)
            return (
                target_topic in scene.topic_ids,
                current_topic in scene.topic_ids,
                any(topic_id in latest_signal_topics for topic_id in scene.topic_ids),
                any(item_id in latest_signal_items for item_id in unresolved_items),
                len(unresolved_items),
            )

        preferred = sorted(scene_debt, key=rank, reverse=True)
        if fatigue == "high" and user_style.openness == "guarded":
            return preferred[0]
        return preferred[0]

    def _select_bridge_scene(
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
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)
        if target_topic == "mood" and last_item == "phq_q2_low_mood":
            if not self._should_hold_current_answer(last_item, latest_user_text, latest_signal_items, latest_signal_topics):
                return None
            if self._has_daylong_mood_answer(latest_user_text) or self._has_flat_functioning_signal(latest_user_text):
                return None
            if self._has_self_view_signal(latest_user_text):
                return None
            unresolved_scene_items = self._scene_unresolved_items(snapshot, SCENE_GRAPH["mood_selfview"], held_back_items)
            if unresolved_scene_items or "phq_q6_worthlessness" in held_back_items:
                return "mood_selfview"
            return None
        if (
            target_topic in {"energy", "focus"}
            and last_item == "phq_q3_sleep"
            and self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics)
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_sleep_impact_signal(latest_user_text)
        ):
            unresolved_scene_items = self._scene_unresolved_items(snapshot, SCENE_GRAPH["sleep_functioning"], held_back_items)
            if unresolved_scene_items:
                return "sleep_functioning"
        if (
            target_topic == "mood"
            and last_item in {"phq_q1_anhedonia", "phq_q7_concentration"}
            and "phq_q1_anhedonia" in latest_signal_items
            and not self._has_low_mood_signal(latest_user_text)
            and session.asked_items.count("phq_q2_low_mood") >= 1
            and snapshot.items["phq_q1_anhedonia"].status == "resolved"
        ):
            unresolved_scene_items = self._scene_unresolved_items(snapshot, SCENE_GRAPH["mood_selfview"], held_back_items)
            if "phq_q6_worthlessness" in unresolved_scene_items:
                return "mood_selfview"
        return None

    def _force_scene_followup(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
    ) -> Optional[str]:
        if target_topic in {"rapport", "summary", "safety", "anxiety"}:
            return None

        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)
        last_item = session.asked_items[-1] if session.asked_items else None
        ranked: list[tuple[int, str]] = []

        for scene_id, scene in SCENE_GRAPH.items():
            if target_topic not in scene.topic_ids:
                continue
            unresolved_items = self._scene_unresolved_items(snapshot, scene, held_back_items)
            if len(unresolved_items) < 2:
                continue

            topic_unresolved = [item_id for item_id in unresolved_items if ITEM_TO_TOPIC.get(item_id) == target_topic]
            exhausted_topic = not topic_unresolved
            cross_topic_signal = any(
                ITEM_TO_TOPIC.get(item_id) in scene.topic_ids and ITEM_TO_TOPIC.get(item_id) != target_topic
                for item_id in latest_signal_items
            ) or any(topic_id in scene.topic_ids and topic_id != target_topic for topic_id in latest_signal_topics)
            resolved_scene_signal = [
                item_id
                for item_id in latest_signal_items
                if item_id in scene.item_ids and snapshot.items[item_id].status == "resolved"
            ]
            repeated_last = bool(last_item and last_item in scene.item_ids and session.asked_items[-3:].count(last_item) >= 1)

            if not (exhausted_topic or cross_topic_signal or (repeated_last and resolved_scene_signal)):
                continue

            score = len(unresolved_items) * 10
            if exhausted_topic:
                score += 12
            if cross_topic_signal:
                score += 10
            if repeated_last and resolved_scene_signal:
                score += 8
            score += len(resolved_scene_signal) * 2
            ranked.append((score, scene_id))

        if not ranked:
            return None
        ranked.sort(reverse=True)
        return ranked[0][1]

    def _select_scene_target_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_scene: Optional[str],
        target_topic: str,
        held_back_items: list[str],
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> Optional[str]:
        if not target_scene:
            return None
        scene = SCENE_GRAPH[target_scene]
        unresolved_items = self._scene_unresolved_items(snapshot, scene, held_back_items)
        if not unresolved_items:
            unresolved_items = []

        latest_user_text = self._latest_user_text(session)
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_topics = self._latest_signal_topics(session)
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        last_item = session.asked_items[-1] if session.asked_items else None
        summary_request = self._has_summary_request(latest_user_text)
        fresh_scene_signal_items = [
            item_id
            for item_id in latest_signal_items
            if item_id in scene.item_ids
            and item_id not in session.asked_items[-2:]
            and snapshot.items[item_id].status != "abstained"
        ]
        if target_scene == "sleep_functioning":
            if _contains_any_marker(latest_user_text, ITEM_SIGNAL_MARKERS["phq_q8_psychomotor"]) and "phq_q8_psychomotor" in unresolved_items:
                return "phq_q8_psychomotor"
            if _contains_any_marker(latest_user_text, ITEM_SIGNAL_MARKERS["phq_q4_fatigue"]) and "phq_q4_fatigue" in unresolved_items:
                return "phq_q4_fatigue"
            for preferred_item in ("phq_q8_psychomotor", "phq_q4_fatigue", "phq_q7_concentration", "phq_q5_appetite"):
                if preferred_item in fresh_scene_signal_items and preferred_item in unresolved_items:
                    return preferred_item
            if summary_request:
                recent_scene_items = set(session.asked_items[-4:])
                for preferred_item in ("phq_q4_fatigue", "phq_q7_concentration", "phq_q8_psychomotor", "phq_q3_sleep", "phq_q5_appetite"):
                    if preferred_item in unresolved_items and preferred_item not in recent_scene_items:
                        return preferred_item
        if (
            target_scene == "mood_selfview"
            and self._has_self_view_signal(latest_user_text)
            and "phq_q6_worthlessness" in fresh_scene_signal_items
        ):
            return "phq_q6_worthlessness"
        if (
            target_scene == "mood_selfview"
            and self._has_concentration_answer(latest_user_text)
            and "phq_q7_concentration" in fresh_scene_signal_items
        ):
            return "phq_q7_concentration"
        if (
            target_scene == "mood_selfview"
            and (
                self._has_anhedonia_signal(latest_user_text)
                or "phq_q1_anhedonia" in latest_signal_items
            )
            and last_item in {"phq_q2_low_mood", "phq_q7_concentration"}
            and "phq_q6_worthlessness" in unresolved_items
        ):
            return "phq_q6_worthlessness"
        if (
            target_scene == "mood_selfview"
            and self._has_anhedonia_signal(latest_user_text)
            and "phq_q1_anhedonia" in fresh_scene_signal_items
        ):
            return "phq_q1_anhedonia"
        resolved_scene_signal = [
            item_id
            for item_id in latest_signal_items
            if item_id in scene.item_ids and snapshot.items[item_id].status == "resolved"
        ]
        unresolved_scene_signal = [item_id for item_id in latest_signal_items if item_id in unresolved_items]
        if (
            target_scene == "sleep_functioning"
            and last_item in scene.item_ids
            and session.asked_items[-3:].count(last_item) >= 1
            and resolved_scene_signal
            and not unresolved_scene_signal
        ):
            for preferred_item in ("phq_q7_concentration", "phq_q8_psychomotor", "phq_q3_sleep", "phq_q5_appetite", "phq_q4_fatigue"):
                if preferred_item in unresolved_items and preferred_item != last_item:
                    return preferred_item
        if (
            target_scene == "mood_selfview"
            and self._has_anhedonia_signal(latest_user_text)
            and "phq_q1_anhedonia" in unresolved_items
        ):
            return "phq_q1_anhedonia"
        if (
            target_scene == "mood_selfview"
            and self._has_anhedonia_signal(latest_user_text)
            and snapshot.items["phq_q1_anhedonia"].status == "resolved"
            and "phq_q6_worthlessness" in unresolved_items
        ):
            return "phq_q6_worthlessness"
        if (
            target_scene == "sleep_functioning"
            and "phq_q4_fatigue" in unresolved_items
            and user_turn_count >= 6
            and last_item in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q5_appetite"}
            and not self._has_appetite_signal(latest_user_text)
            and (
                any(
                    (
                        self._has_low_mood_signal(latest_user_text),
                        self._has_anhedonia_signal(latest_user_text),
                        self._has_self_view_signal(latest_user_text),
                    )
                )
                or any(
                    item_id in latest_signal_items
                    for item_id in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"}
                )
            )
        ):
            return "phq_q4_fatigue"
        if (
            target_scene == "sleep_functioning"
            and self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics)
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_sleep_impact_signal(latest_user_text)
        ):
            unresolved_daytime_items = [item_id for item_id in unresolved_items if item_id != "phq_q3_sleep"]
            if self._has_appetite_signal(latest_user_text) and "phq_q5_appetite" in unresolved_items:
                return "phq_q5_appetite"
            if self._has_activation_signal(latest_user_text) and "phq_q4_fatigue" in unresolved_items:
                return "phq_q4_fatigue"
            if (
                (
                    any(
                        (
                            self._has_low_mood_signal(latest_user_text),
                            self._has_anhedonia_signal(latest_user_text),
                            self._has_self_view_signal(latest_user_text),
                        )
                    )
                    or any(
                        item_id in latest_signal_items
                        for item_id in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"}
                    )
                )
                and "phq_q4_fatigue" in unresolved_daytime_items
            ):
                return "phq_q4_fatigue"
            if (
                target_topic == "energy"
                and snapshot.items["phq_q4_fatigue"].status == "resolved"
                and snapshot.items["phq_q5_appetite"].status == "resolved"
                and not any(item_id in unresolved_items for item_id in {"phq_q4_fatigue", "phq_q5_appetite"})
            ):
                return None
            for preferred_item in ("phq_q5_appetite", "phq_q4_fatigue", "phq_q7_concentration", "phq_q8_psychomotor"):
                if preferred_item in latest_signal_items and preferred_item in unresolved_daytime_items:
                    return preferred_item
            for preferred_item in ("phq_q7_concentration", "phq_q8_psychomotor", "phq_q5_appetite", "phq_q4_fatigue"):
                if preferred_item in unresolved_daytime_items:
                    return preferred_item
        if target_scene in {"worry_shape", "worry_activation"}:
            if (
                "gad_q3_excessive_worry" in unresolved_items
                and (
                    self._is_nonexpansive_followup(latest_user_text)
                    or self._has_timing_or_frequency_answer(latest_user_text)
                    or self._has_worry_scope_answer(latest_user_text)
                    or not self._has_new_anxiety_branch_detail(latest_user_text)
                )
            ):
                return "gad_q3_excessive_worry"

        signaled_candidates = [item_id for item_id in unresolved_items if item_id in latest_signal_items]
        if signaled_candidates:
            return max(
                signaled_candidates,
                key=lambda item_id: self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style),
            )
        if not unresolved_items:
            return None
        return max(
            unresolved_items,
            key=lambda item_id: self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style),
        )

    def _summary_fragments(self, snapshot: ScreeningSnapshot, session: ChatSession) -> list[str]:
        language = session.language
        fragments: list[str] = []
        items = snapshot.items
        session_signal_topics = self._session_signal_topics(session)
        session_user_text = " ".join(self._normalize(turn.text) for turn in session.turns if turn.speaker == "user")
        anxiety_downplayed = (
            self._has_anxiety_downplay_signal(session_user_text)
            and self._has_non_anxiety_salient_signal(session_user_text)
        )

        def _active(item_id: str, minimum: int = 1) -> bool:
            item = items.get(item_id)
            return bool(item and item.value is not None and item.value >= minimum and item.status in {"resolved", "partial", "contradicted"})

        if _active("phq_q1_anhedonia"):
            fragments.append(
                {
                    "en": "interest tends to drop before getting started",
                    "hi": "काम शुरू करने से पहले ही मन हटने लगता है",
                    "hinglish": "kaam start karne se pehle hi mann hatne lagta hai",
                }[language]
            )
        if _active("phq_q2_low_mood"):
            fragments.append(
                {
                    "en": "the heaviness seems to stay through much of the day",
                    "hi": "भारीपन दिन के बड़े हिस्से में बना रहता है",
                    "hinglish": "heaviness din ke bade hissa mein bani rehti hai",
                }[language]
            )
        if _active("phq_q3_sleep"):
            fragments.append(
                {
                    "en": "sleep looks disrupted rather than settled",
                    "hi": "नींद ठीक से स्थिर नहीं हो पा रही है",
                    "hinglish": "sleep theek se settle nahi ho pa rahi hai",
                }[language]
            )
        if _active("phq_q4_fatigue") or _active("phq_q7_concentration"):
            fragments.append(
                {
                    "en": "energy and focus both look slower than usual",
                    "hi": "ऊर्जा और ध्यान दोनों सामान्य से धीमे लग रहे हैं",
                    "hinglish": "energy aur focus dono normal se slower lag rahe hain",
                }[language]
            )
        anxiety_fragment = None
        anxiety_active = (
            not anxiety_downplayed
            and (
                _active("gad_q2_control_worry")
                or _active("gad_q3_excessive_worry")
                or _active("gad_q4_trouble_relaxing")
                or "anxiety" in session_signal_topics
            )
        )
        if _active("phq_q6_worthlessness"):
            fragments.append(
                {
                    "en": "self-view is also getting pulled toward burden or self-blame",
                    "hi": "अपने बारे में नज़र भी बोझ या आत्म-दोष की तरफ़ खिंच रही है",
                    "hinglish": "self-view bhi burden ya self-blame ki taraf khinch raha hai",
                }[language]
            )
        if anxiety_active:
            anxiety_fragment = self._anxiety_summary_fragment(session)
            if anxiety_fragment and (
                (session.asked_items and ITEM_TO_TOPIC.get(session.asked_items[-1], "") == "anxiety")
                or "anxiety" in session_signal_topics
            ):
                insert_at = 2 if len(fragments) >= 2 else len(fragments)
                fragments.insert(insert_at, anxiety_fragment)

        if not any("ऊर्जा" in fragment or "energy" in fragment for fragment in fragments) and "energy" in session_signal_topics:
            fragments.append(
                {
                    "en": "energy or startup effort also looks lower than usual",
                    "hi": "ऊर्जा या शुरुआत करने की क्षमता भी सामान्य से कम लग रही है",
                    "hinglish": "energy ya start-up effort bhi normal se lower lag raha hai",
                }[language]
            )
        if not any("भारीपन" in fragment or "heaviness" in fragment for fragment in fragments) and "mood" in session_signal_topics:
            fragments.append(
                {
                    "en": "there is still a day-level low or heavy mood in the background",
                    "hi": "पीछे एक दिन-भर का भारी या नीचे खिंचा हुआ मन बना हुआ है",
                    "hinglish": "background mein day-level low ya heavy mood bana hua hai",
                }[language]
            )
        if anxiety_fragment and anxiety_fragment not in fragments:
            fragments.append(anxiety_fragment)
        if not fragments and not anxiety_downplayed and any(item_id in ANXIETY_CORE_ITEMS for item_id in session.asked_items[-5:]):
            fragments.append(self._anxiety_summary_fragment(session))
        if not fragments and session.asked_items:
            last_topic = ITEM_TO_TOPIC.get(session.asked_items[-1], "mood")
            fragments.append(
                {
                    "en": f"the main pattern still centers on {self._topic_label(last_topic, language)}",
                    "hi": f"मुख्य पैटर्न अभी भी {self._topic_label(last_topic, language)} के इर्द-गिर्द है",
                    "hinglish": f"main pattern abhi bhi {self._topic_label(last_topic, language)} ke around hai",
                }[language]
            )

        return fragments[:4]

    def _anxiety_summary_fragment(self, session: ChatSession) -> str:
        language = session.language
        recent_user_text = " ".join(self._normalize(turn.text) for turn in session.turns if turn.speaker == "user")
        channel = self._infer_anxiety_channel(recent_user_text)
        single_issue = self._has_single_issue_scope_answer(recent_user_text)
        if channel == "mind" and single_issue:
            return {
                "en": "the worry seems to stay mostly around one future or responsibility issue, and the harder part is quieting the mind",
                "hi": "चिंता ज़्यादातर एक ही भविष्य या ज़िम्मेदारी वाली बात के इर्द-गिर्द रहती है, और मुश्किल हिस्सा दिमाग को शांत करना है",
                "hinglish": "worry zyada ek future ya responsibility wali baat ke around rehti hai, aur harder part mind ko quiet karna hai",
            }[language]
        if channel == "mind":
            return {
                "en": "the harder part looks mental rather than bodily: the mind keeps running even when the body is not the main issue",
                "hi": "चिंता का मुश्किल हिस्सा शरीर से ज़्यादा मानसिक लग रहा है: जब शरीर मुख्य समस्या नहीं है तब भी दिमाग चलता रहता है",
                "hinglish": "harder part body se zyada mental lag raha hai: body main issue na ho tab bhi mind chalta rehta hai",
            }[language]
        if channel == "body":
            return {
                "en": "the worry shows up mainly as physical tension rather than racing thoughts",
                "hi": "चिंता ज़्यादातर भागते विचारों से नहीं बल्कि शारीरिक तनाव के रूप में दिख रही है",
                "hinglish": "worry zyada racing thoughts se nahi balki physical tension ke form mein aa rahi hai",
            }[language]
        if channel == "both":
            return {
                "en": "the worry seems to pull both thoughts and body tension together",
                "hi": "चिंता विचारों और शारीरिक तनाव दोनों को साथ में खींच रही है",
                "hinglish": "worry thoughts aur body tension dono ko saath kheench rahi hai",
            }[language]
        return {
            "en": "worry still looks like an active part of the picture",
            "hi": "चिंता अभी भी इस तस्वीर का सक्रिय हिस्सा लग रही है",
            "hinglish": "worry abhi bhi picture ka active hissa lag rahi hai",
        }[language]

    def _infer_anxiety_channel(self, normalized_text: str) -> str:
        if not normalized_text:
            return "unclear"
        mind_markers = (
            "mind",
            "thought",
            "quieting your thoughts",
            "quieting thoughts",
            "quiet my mind",
            "calm my mind",
            "mind ko",
            "दिमाग",
            "dimag",
            "सोच",
        )
        body_markers = (
            "body",
            "body tension",
            "tense body",
            "physical",
            "शरीर",
            "तनाव",
            "body me",
            "body mein",
        )
        body_negations = (
            "no body issue",
            "not body",
            "body is not the main issue",
            "body is not the issue",
            "body tension not the main issue",
            "body tension isn t the main issue",
            "body tension is not the main issue",
            "body tension utni badi baat nahi",
            "body tension is there but smaller",
            "body side is smaller",
            "body part is smaller",
            "body tension hai but smaller",
            "body tension hai but smaller lagti hai",
            "body mein koi problem nahi",
            "body me koi problem nahi",
            "sharir mein koi samasya nahi",
            "शरीर में कोई समस्या नहीं",
            "शरीर में मुझे कोई समस्या नहीं",
            "शरीर में खास समस्या नहीं",
            "शरीर वाला हिस्सा है लेकिन उतना बड़ा नहीं",
            "शरीर से ज्यादा दिमाग",
            "शरीर से ज़्यादा दिमाग",
            "body se zyada mind",
            "body se zyada mental",
            "केवल दिमाग",
            "सिर्फ दिमाग",
            "बस दिमाग",
        )
        has_mind = any(marker in normalized_text for marker in mind_markers)
        has_body = any(marker in normalized_text for marker in body_markers)
        if any(marker in normalized_text for marker in body_negations):
            return "mind"
        if has_mind and has_body:
            return "both"
        if has_body:
            return "body"
        if has_mind:
            return "mind"
        return "unclear"

    def _session_signal_topics(self, session: ChatSession) -> set[str]:
        session_text = " ".join(self._normalize(turn.text) for turn in session.turns if turn.speaker == "user")
        if not session_text:
            return set()
        topics = {
            topic_id
            for topic_id, markers in TOPIC_SIGNAL_MARKERS.items()
            if any(marker in session_text for marker in markers)
        }
        if (
            "anxiety" in topics
            and self._has_anxiety_downplay_signal(session_text)
            and self._has_non_anxiety_salient_signal(session_text)
        ):
            topics.discard("anxiety")
        return topics

    def _build_working_summary(self, snapshot: ScreeningSnapshot, session: ChatSession) -> str:
        language = session.language
        fragments = self._summary_fragments(snapshot, session)
        if not fragments:
            return CLOSING_MESSAGES[language]

        prefix = WORKING_SUMMARY_PREFIXES[language]
        joined = "; ".join(fragments[:3])
        debt_topics = snapshot.coverage.dialogue.coverage_debt if snapshot.coverage.dialogue else []
        if debt_topics:
            preferred_debt = debt_topics
            if snapshot.safety.level == "none":
                filtered = [topic_id for topic_id in debt_topics if topic_id != "safety"]
                preferred_debt = filtered or debt_topics
            top_debt = self._topic_label(preferred_debt[0], language)
            tail = {
                "en": f"If one detail still matters to clarify, {top_debt} is the next best place to tighten.",
                "hi": f"अगर एक बात अभी भी साफ़ करनी हो, तो अगला सबसे उपयोगी हिस्सा {top_debt} रहेगा।",
                "hinglish": f"Agar ek cheez abhi bhi clarify karni ho, to next best jagah {top_debt} rahegi.",
            }[language]
        else:
            tail = {
                "en": "If that fits, I can hold this as the current working summary.",
                "hi": "अगर यह ठीक लग रहा है, तो मैं इसे अभी का कामचलाऊ सार मान सकता हूँ।",
                "hinglish": "Agar yeh fit lag raha hai, to main ise abhi ka working summary maan sakta hoon.",
            }[language]
        if language == "hi":
            return f"{prefix} {joined}। {tail}"
        return f"{prefix} {joined}. {tail}"

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
        probing_topics = len([topic for topic in topic_states if topic.status in {"probing", "review"} and topic.topic_id != "safety"])
        recent_text = " ".join(self._normalize(turn.text) for turn in user_turns[-2:])
        latest_text = self._latest_user_text(session)
        closure_signal = any(marker in recent_text for marker in CLOSURE_MARKERS)
        completion = snapshot.coverage.completion_ratio
        minimum_summary_coverage = snapshot.coverage.touched_items >= MIN_SUMMARY_TOUCHES or completion >= 0.78
        latest_signal_topics = self._latest_signal_topics(session) & AFFECTIVE_TOPIC_FAMILY

        if self._has_continue_signal(latest_text):
            return "steady"
        if latest_signal_topics and completion < 0.85:
            unresolved_latest = any(
                snapshot.items[item_id].status != "resolved"
                for topic_id in latest_signal_topics
                for item_id in TOPIC_GRAPH[topic_id].item_ids
            )
            if unresolved_latest:
                return "steady"

        if probing_topics > 1 and completion < 0.85:
            return "steady"
        if minimum_summary_coverage and completion >= 0.68 and probing_topics <= 1 and (
            closure_signal
            or stable_topics >= 3
            or (user_style.steering_preference == "guided" and stable_topics >= 2)
        ):
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
        if any(item_id in held_back_items for item_id in TOPIC_GRAPH[topic_id].item_ids) and not unresolved_items:
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
        session: ChatSession,
        topic_states: list[TopicState],
        user_turn_count: int,
        held_back_items: list[str],
        phq_queue: list[str],
        gad_queue: list[str],
        readiness: ReadinessLevel,
        fatigue: FatigueLevel,
        continue_intent: bool,
        reopen_signal: bool,
        summary_request: bool,
    ) -> str:
        remaining_closeout = len(phq_queue) + len(gad_queue)
        if snapshot.safety.level == "urgent":
            return "safety"
        if snapshot.safety.level == "review" and "phq_q9_self_harm" not in held_back_items:
            return "safety"
        if summary_request and user_turn_count >= 2:
            if remaining_closeout == 0 and (
                snapshot.coverage.touched_items >= MIN_SUMMARY_TOUCHES
                or snapshot.coverage.completion_ratio >= 0.78
            ):
                return "summary"
            if any(topic.status in {"review", "probing"} for topic in topic_states if topic.topic_id != "safety"):
                return "clarification"
            return "exploration"
        if continue_intent or reopen_signal:
            if any(topic.status in {"review", "probing"} for topic in topic_states if topic.topic_id != "safety"):
                return "clarification"
            return "exploration"
        if user_turn_count == 1 and snapshot.coverage.touched_items >= 1:
            return "clarification"
        if user_turn_count <= 1 and snapshot.coverage.touched_items < 3:
            return "rapport"
        if any(topic.status in {"review", "probing"} for topic in topic_states if topic.topic_id != "safety"):
            return "clarification"
        stable_topics = [topic for topic in topic_states if topic.status == "stable" and topic.topic_id != "safety"]
        active_open_topics = [topic for topic in topic_states if topic.status in {"review", "probing"} and topic.topic_id != "safety"]
        undercovered_scenes = self._scene_coverage_debt(snapshot, session, held_back_items)
        if (
            not summary_request
            and user_turn_count >= 5
            and fatigue != "high"
            and snapshot.coverage.completion_ratio < 0.8
            and (
                len(undercovered_scenes) >= 2
                or (undercovered_scenes and snapshot.coverage.touched_items < 8)
            )
        ):
            return "clarification" if active_open_topics or snapshot.coverage.touched_items >= 3 else "exploration"
        if readiness == "ready_to_close" and len(active_open_topics) <= 1:
            if remaining_closeout == 0 and (
                snapshot.coverage.touched_items >= MIN_SUMMARY_TOUCHES
                or snapshot.coverage.completion_ratio >= 0.78
            ):
                return "summary"
            return "clarification" if active_open_topics or undercovered_scenes else "exploration"
        if fatigue == "high" and snapshot.coverage.completion_ratio >= 0.45:
            return "clarification"
        if snapshot.coverage.completion_ratio >= 0.72 or len(stable_topics) >= 4:
            if remaining_closeout > 0:
                return "clarification" if len(active_open_topics) > 0 or snapshot.coverage.touched_items >= 3 else "exploration"
            if snapshot.coverage.touched_items < MIN_SUMMARY_TOUCHES and undercovered_scenes:
                return "clarification" if len(active_open_topics) > 0 or snapshot.coverage.touched_items >= 3 else "exploration"
            if len(active_open_topics) > 1:
                return "clarification"
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
        latest_user_text = self._latest_user_text(session)
        if self._should_use_physical_clarifier(session, latest_user_text):
            return "mood"
        continuity_item = self._continuity_item(snapshot, session, held_back_items, fatigue)
        if continuity_item:
            return ITEM_TO_TOPIC.get(continuity_item, current_topic)
        if stage == "safety":
            return "safety"
        if stage == "summary":
            return current_topic if current_topic in TOPIC_GRAPH else "mood"
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        latest_signal_topics = self._latest_signal_topics(session)
        latest_signal_items = self._latest_signal_items(session)
        latest_signal_item_topics = {
            ITEM_TO_TOPIC.get(item_id)
            for item_id in latest_signal_items
            if ITEM_TO_TOPIC.get(item_id)
        }
        breadth_request = self._has_summary_request(latest_user_text) or self._has_continue_signal(latest_user_text)
        early_non_sleep_signal_topics = {
            topic_id
            for topic_id in (latest_signal_topics | latest_signal_item_topics)
            if topic_id and topic_id != "sleep"
        }
        anxiety_downplayed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        strong_anxiety_domain_signal = self._has_strong_anxiety_domain_signal(latest_user_text)
        recent_signal_topics = self._recent_signal_topics(session)
        last_item = session.asked_items[-1] if session.asked_items else None
        last_topic = ITEM_TO_TOPIC.get(last_item) if last_item else None
        explicit_anxiety_items = latest_signal_items & {
            "gad_q1_nervous",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        }
        if breadth_request:
            exhausted_topics = self._breadth_request_exhausted_topics(
                session,
                latest_user_text,
                latest_signal_items,
                latest_signal_topics,
            )
            if exhausted_topics:
                recent_topics = [
                    ITEM_TO_TOPIC.get(item_id)
                    for item_id in session.asked_items[-4:]
                    if ITEM_TO_TOPIC.get(item_id)
                ]
                breadth_candidates = [
                    topic
                    for topic in topic_states
                    if topic.topic_id not in {"safety", *exhausted_topics}
                    and topic.unresolved_items
                ]
                if breadth_candidates:
                    return max(
                        breadth_candidates,
                        key=lambda topic: (
                            topic.topic_id not in recent_topics,
                            not topic.touched,
                            topic.status == "pending",
                            self._topic_coverage_boost(snapshot, topic.topic_id),
                            topic.priority,
                        ),
                    ).topic_id
        if self._has_worry_scope_answer(latest_user_text) and (
            current_topic == "anxiety"
            or last_topic == "anxiety"
            or last_item in ANXIETY_CORE_ITEMS
        ):
            return "anxiety"

        if (
            not session.asked_items
            and user_turn_count <= 2
            and "sleep" in latest_signal_topics
            and (
                "phq_q3_sleep" in latest_signal_items
                or self._has_sleep_pattern_answer(latest_user_text)
                or self._has_sleep_impact_signal(latest_user_text)
            )
            and not (
                user_turn_count >= 2
                and snapshot.items["phq_q3_sleep"].status == "resolved"
                and early_non_sleep_signal_topics
            )
        ):
            return "sleep"

        last_assistant_text = self._last_assistant_text(session)
        if self._matches_any_segment(last_assistant_text, self._post_close_segments(session.language)):
            reopenable_signal_topics: list[str] = []
            for item_id in latest_signal_items:
                topic_id = ITEM_TO_TOPIC.get(item_id)
                if topic_id not in AFFECTIVE_TOPIC_FAMILY or topic_id == "anxiety":
                    continue
                if topic_id == "sleep" and not (
                    self._has_sleep_pattern_answer(latest_user_text)
                    or self._has_sleep_impact_signal(latest_user_text)
                ):
                    continue
                if topic_id not in reopenable_signal_topics:
                    reopenable_signal_topics.append(topic_id)
            if reopenable_signal_topics:
                return max(reopenable_signal_topics, key=lambda topic_id: TOPIC_GRAPH[topic_id].priority)
        if (
            "phq_q3_sleep" in latest_signal_items
            and not session.asked_items
            and user_turn_count <= 2
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not (
                user_turn_count >= 2
                and snapshot.items["phq_q3_sleep"].status == "resolved"
                and early_non_sleep_signal_topics
            )
        ):
            return "sleep"
        non_sleep_signal_topics = {
            topic_id
            for topic_id in (latest_signal_topics | latest_signal_item_topics)
            if topic_id and topic_id != "sleep"
        }
        sleep_specific_followup = (
            self._has_sleep_specific_timing_answer(latest_user_text)
            or self._has_frequency_answer(latest_user_text)
        )
        if "phq_q3_sleep" in latest_signal_items and snapshot.items["phq_q3_sleep"].status != "resolved":
            daytime_functioning_signals = (
                {"energy", "focus"} & latest_signal_topics
                or {
                    item_id
                    for item_id in latest_signal_items
                    if item_id in {"phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"}
                }
            )
            if (
                ((not daytime_functioning_signals and not non_sleep_signal_topics) or sleep_specific_followup)
            ) and (not session.asked_items or current_topic == "sleep" or session.asked_items[-1] == "phq_q3_sleep"):
                return "sleep"
        sleep_functioning_shift = bool(
            last_item == "phq_q3_sleep"
            and bool(non_sleep_signal_topics or self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics))
            and not sleep_specific_followup
        )
        if (
            stage in {"rapport", "clarification", "exploration"}
            and last_item
            and last_topic
            and last_topic != "safety"
            and not sleep_functioning_shift
            and self._should_hold_current_answer(last_item, latest_user_text, latest_signal_items, latest_signal_topics)
        ):
            item_state = snapshot.items.get(last_item)
            if (
                last_item == "phq_q3_sleep"
                and item_state is not None
                and item_state.status == "resolved"
                and any(
                    (
                        self._has_anhedonia_signal(latest_user_text),
                        self._has_low_mood_signal(latest_user_text),
                        self._has_self_view_signal(latest_user_text),
                        self._has_activation_signal(latest_user_text),
                        self._has_concentration_answer(latest_user_text),
                        self._has_appetite_signal(latest_user_text),
                    )
                )
            ):
                item_state = None
            if item_state is None or item_state.status != "resolved" or last_topic == current_topic:
                return last_topic
            if last_topic in {"sleep", "energy", "focus", "mood", "self_view"}:
                return last_topic
        latest_affective_topics = [
            topic_id
            for topic_id in (latest_signal_topics | latest_signal_item_topics)
            if topic_id in {"sleep", "energy", "focus", "mood", "self_view"}
        ]
        if last_item == "phq_q3_sleep" and sleep_functioning_shift:
            latest_affective_topics = [topic_id for topic_id in latest_affective_topics if topic_id != "sleep"]
        latest_anxiety_active = bool(
            not anxiety_downplayed
            and (
                explicit_anxiety_items
                or "anxiety" in latest_signal_topics
                or self._has_strong_anxiety_domain_signal(latest_user_text)
            )
        )
        if latest_affective_topics and not latest_anxiety_active:
            return max(
                latest_affective_topics,
                key=lambda topic_id: (
                    topic_id in latest_signal_item_topics,
                    topic_id == last_topic,
                    topic_id == current_topic and last_item is not None,
                    TOPIC_GRAPH[topic_id].priority,
                ),
            )
        if (
            strong_anxiety_domain_signal
            and not anxiety_downplayed
            and not (
                last_item == "phq_q3_sleep"
                and self._has_sleep_pattern_answer(latest_user_text)
            )
        ):
            return "anxiety"
        if anxiety_downplayed:
            fresh_non_anxiety_topics = [
                topic_id
                for topic_id in (latest_signal_topics | latest_signal_item_topics)
                if topic_id in {"sleep", "energy", "focus", "mood", "self_view"}
            ]
            if fresh_non_anxiety_topics:
                return max(
                    fresh_non_anxiety_topics,
                    key=lambda topic_id: (
                        topic_id == current_topic,
                        topic_id in {"energy", "focus"},
                        TOPIC_GRAPH[topic_id].priority,
                    ),
                )
        if explicit_anxiety_items and not anxiety_downplayed:
            if "gad_q3_excessive_worry" in explicit_anxiety_items and self._has_worry_domain_signal(latest_user_text):
                return "anxiety"
            if "gad_q2_control_worry" in explicit_anxiety_items and self._has_persistent_worry_signal(latest_user_text):
                return "anxiety"
            if "gad_q4_trouble_relaxing" in explicit_anxiety_items and (
                self._has_lingering_tension_signal(latest_user_text)
                or any(marker in latest_user_text for marker in ITEM_SIGNAL_MARKERS["gad_q4_trouble_relaxing"])
            ):
                return "anxiety"
        if stage in {"clarification", "exploration"}:
            fresh_non_anxiety_topics = [
                topic_id
                for topic_id in (latest_signal_topics | latest_signal_item_topics)
                if topic_id in {"sleep", "energy", "focus", "mood", "self_view"}
                and topic_id != current_topic
            ]
            if fresh_non_anxiety_topics:
                return max(
                    fresh_non_anxiety_topics,
                    key=lambda topic_id: (
                        topic_id in {"focus", "energy"},
                        TOPIC_GRAPH[topic_id].priority,
                    ),
                )
        if current_topic == "anxiety" and self._has_sleep_choice_signal(latest_user_text):
            return "sleep"
        if current_topic == "sleep" and "gad_q4_trouble_relaxing" in latest_signal_items:
            return "anxiety"
        if "energy" in latest_signal_topics and self._infer_anxiety_channel(latest_user_text) == "mind":
            return "energy"

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
        anxiety_evidence_active = any(snapshot.items[item_id].evidence_span_ids for item_id in ANXIETY_CORE_ITEMS)
        affective_debt_active = any(
            topic.topic_id in AFFECTIVE_TOPIC_FAMILY and topic.unresolved_items
            for topic in topic_states
        )
        if affective_debt_active and not anxiety_signal_active and not self._has_new_anxiety_branch_detail(latest_user_text):
            non_anxiety_candidates = [topic for topic in candidates if topic.topic_id != "anxiety"]
            if non_anxiety_candidates:
                candidates = non_anxiety_candidates

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
            if (
                topic.topic_id == "anxiety"
                and affective_debt_active
                and (
                    anxiety_downplayed
                    or not anxiety_signal_active
                    or not self._has_new_anxiety_branch_detail(latest_user_text)
                )
            ):
                score -= 28
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
        preempt_item = self._fresh_signal_preemption_item(snapshot, session, target_topic, held_back_items, fatigue, user_style)
        if preempt_item:
            return preempt_item
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
        latest_signal_items = self._latest_signal_items(session)
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        recent_item_window = session.asked_items[-2:]
        if self._has_summary_request(latest_user_text):
            recent_item_window = session.asked_items[-4:]

        def can_stabilize(item_id: str) -> bool:
            return (
                item_id not in held_back
                and snapshot.items[item_id].status != "abstained"
                and item_id not in recent_item_window
            )

        has_prior_assistant = any(turn.speaker == "assistant" for turn in session.turns)
        if (
            target_topic == "sleep"
            and has_prior_assistant
            and (
                snapshot.items["phq_q3_sleep"].status != "resolved"
                or session.asked_items
            )
            and (
                self._has_sleep_pattern_answer(latest_user_text)
                or "phq_q3_sleep" in latest_signal_items
                or "sleep" in self._latest_signal_topics(session)
            )
            and can_stabilize("phq_q3_sleep")
        ):
            return "phq_q3_sleep"
        if (
            (self._has_low_mood_signal(latest_user_text) or "phq_q2_low_mood" in latest_signal_items)
            and can_stabilize("phq_q2_low_mood")
        ):
            return "phq_q2_low_mood"
        if (
            self._has_anhedonia_signal(latest_user_text)
            and can_stabilize("phq_q1_anhedonia")
            and not session.asked_items
            and user_turn_count <= 1
            and "phq_q2_low_mood" not in latest_signal_items
        ):
            return "phq_q1_anhedonia"
        if (
            (self._has_self_view_signal(latest_user_text) or "phq_q6_worthlessness" in latest_signal_items)
            and can_stabilize("phq_q6_worthlessness")
        ):
            return "phq_q6_worthlessness"
        if (
            (self._has_concentration_answer(latest_user_text) or "phq_q7_concentration" in latest_signal_items)
            and can_stabilize("phq_q7_concentration")
            and not (
                session.asked_items
                and session.asked_items[-1] == "phq_q7_concentration"
                and snapshot.items["phq_q4_fatigue"].status != "resolved"
            )
        ):
            return "phq_q7_concentration"
        if "phq_q8_psychomotor" in latest_signal_items and can_stabilize("phq_q8_psychomotor"):
            return "phq_q8_psychomotor"
        candidates = [
            item_id
            for item_id in TOPIC_GRAPH[target_topic].item_ids
            if item_id not in held_back and snapshot.items[item_id].status != "resolved"
        ]
        if not candidates:
            return None
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

    def _fresh_signal_preemption_item(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
        fatigue: FatigueLevel,
        user_style: UserStyleProfile,
    ) -> Optional[str]:
        latest_signal_items = self._latest_signal_items(session)
        if not latest_signal_items:
            return None
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        if (
            target_topic == "sleep"
            and "phq_q3_sleep" in latest_signal_items
            and (
                snapshot.items["phq_q3_sleep"].status != "resolved"
                or (
                    not session.asked_items
                    and user_turn_count <= 2
                    and not self._has_sleep_pattern_answer(self._latest_user_text(session))
                )
            )
        ):
            return None
        held_back = set(held_back_items)
        last_item = session.asked_items[-1] if session.asked_items else None
        last_topic = ITEM_TO_TOPIC.get(last_item) if last_item else None
        repeated_last = bool(last_item and session.asked_items[-4:].count(last_item) >= 1)
        latest_user_text = self._latest_user_text(session)
        latest_signal_topics = self._latest_signal_topics(session)
        if self._should_hold_current_answer(last_item, latest_user_text, latest_signal_items, latest_signal_topics):
            return None
        if target_topic == "anxiety" and (
            latest_signal_items & {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}
            or self._has_persistent_worry_signal(latest_user_text)
            or self._has_worry_scope_answer(latest_user_text)
            or self._has_worry_domain_signal(latest_user_text)
            or self._has_lingering_tension_signal(latest_user_text)
        ):
            return None
        preemptible_items = {
            "phq_q1_anhedonia",
            "phq_q2_low_mood",
            "phq_q4_fatigue",
            "phq_q5_appetite",
            "phq_q6_worthlessness",
            "phq_q7_concentration",
            "phq_q8_psychomotor",
        }
        candidates: list[tuple[int, str]] = []
        for item_id in latest_signal_items:
            if item_id not in preemptible_items:
                continue
            if item_id in held_back or item_id not in snapshot.items or snapshot.items[item_id].status == "resolved":
                continue
            item_topic = ITEM_TO_TOPIC.get(item_id)
            if item_topic == "safety" and snapshot.safety.level == "none":
                continue
            score = self._item_priority_score(snapshot, session, item_id, target_topic, fatigue, user_style)
            if item_id != last_item:
                score += 10
            if item_topic and item_topic != target_topic:
                score += 12
            if repeated_last and item_topic and item_topic != last_topic:
                score += 8
            candidates.append((score, item_id))
        if not candidates:
            return None
        _, best_item = max(candidates)
        best_topic = ITEM_TO_TOPIC.get(best_item)
        if best_topic and last_topic and best_topic == last_topic:
            return None
        if best_topic and (best_topic != target_topic or best_item != last_item):
            return best_item
        return None

    def _should_hold_current_answer(
        self,
        last_item: Optional[str],
        latest_user_text: str,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> bool:
        if not last_item or not latest_user_text:
            return False
        anxiety_suppressed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        if last_item in {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"} and anxiety_suppressed:
            return False
        if last_item == "phq_q3_sleep":
            has_sleep_detail = (
                self._has_sleep_pattern_answer(latest_user_text)
                or self._has_sleep_impact_signal(latest_user_text)
                or "phq_q3_sleep" in latest_signal_items
                or "sleep" in latest_signal_topics
            )
            if not has_sleep_detail:
                return False
            return has_sleep_detail and (
                self._has_sleep_pattern_answer(latest_user_text)
                or self._has_sleep_impact_signal(latest_user_text)
                or self._has_sleep_specific_timing_answer(latest_user_text)
                or self._has_frequency_answer(latest_user_text)
            )
        if last_item == "phq_q4_fatigue":
            if any(
                item_id in latest_signal_items
                for item_id in {"phq_q5_appetite", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q8_psychomotor"}
            ) or any(topic_id in latest_signal_topics for topic_id in {"focus", "mood", "self_view"}):
                return False
            return (
                self._has_activation_signal(latest_user_text)
                or self._has_timing_or_frequency_answer(latest_user_text)
                or "phq_q4_fatigue" in latest_signal_items
                or "energy" in latest_signal_topics
                or any(marker in latest_user_text for marker in ("day ke end", "din ke end", "दिन के अंत"))
            )
        if last_item == "phq_q7_concentration":
            if (
                not self._has_concentration_answer(latest_user_text)
                and (
                    self._has_activation_signal(latest_user_text)
                    or self._has_appetite_signal(latest_user_text)
                    or self._has_sleep_pattern_answer(latest_user_text)
                    or self._has_sleep_impact_signal(latest_user_text)
                )
            ):
                return False
            return (
                self._has_concentration_answer(latest_user_text)
                or "phq_q7_concentration" in latest_signal_items
                or "focus" in latest_signal_topics
            )
        if last_item == "phq_q2_low_mood":
            if any(
                item_id in latest_signal_items
                for item_id in {"phq_q1_anhedonia", "phq_q4_fatigue", "phq_q5_appetite", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q8_psychomotor"}
            ) or any(topic_id in latest_signal_topics for topic_id in {"energy", "focus", "self_view"}):
                return False
            return (
                self._has_low_mood_signal(latest_user_text)
                or self._has_daylong_mood_answer(latest_user_text)
                or self._has_flat_functioning_signal(latest_user_text)
            )
        if last_item == "phq_q1_anhedonia":
            if any(
                item_id in latest_signal_items
                for item_id in {"phq_q2_low_mood", "phq_q4_fatigue", "phq_q5_appetite", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q8_psychomotor"}
            ) or any(topic_id in latest_signal_topics for topic_id in {"energy", "focus", "self_view"}):
                return False
            return self._has_anhedonia_signal(latest_user_text)
        if last_item == "phq_q6_worthlessness":
            return self._has_self_view_signal(latest_user_text)
        if last_item == "gad_q2_control_worry":
            return (
                self._has_persistent_worry_signal(latest_user_text)
                or self._has_timing_or_frequency_answer(latest_user_text)
                or "gad_q2_control_worry" in latest_signal_items
            )
        if last_item == "gad_q3_excessive_worry":
            return (
                self._has_worry_scope_answer(latest_user_text)
                or self._has_worry_domain_signal(latest_user_text)
                or "gad_q3_excessive_worry" in latest_signal_items
            )
        if last_item == "gad_q4_trouble_relaxing":
            return (
                self._infer_anxiety_channel(latest_user_text) in {"mind", "body", "both"}
                or self._has_timing_or_frequency_answer(latest_user_text)
                or "gad_q4_trouble_relaxing" in latest_signal_items
            )
        return False

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
        recent_signal_topics = self._recent_signal_topics(session)

        def available(item_id: str) -> bool:
            return (
                item_id not in held_back
                and item_id in snapshot.items
                and snapshot.items[item_id].status != "resolved"
            )

        def discussable(item_id: str) -> bool:
            return item_id not in held_back and item_id in snapshot.items and snapshot.items[item_id].status != "abstained"

        if target_topic == "anxiety" and self._is_repetitive_persistent_worry_echo(latest_user_text):
            if session.asked_items.count("gad_q4_trouble_relaxing") >= 1 and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if session.asked_items.count("gad_q2_control_worry") >= 1 and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
        if target_topic == "anxiety" and self._has_strong_anxiety_domain_signal(latest_user_text):
            if session.asked_items.count("gad_q2_control_worry") == 0:
                if available("gad_q2_control_worry"):
                    return "gad_q2_control_worry"
                if (
                    (
                        "gad_q2_control_worry" in latest_signal_items
                        or "gad_q2_control_worry" in recent_signal_items
                        or self._has_persistent_worry_signal(latest_user_text)
                    )
                    and available("gad_q4_trouble_relaxing")
                ):
                    return "gad_q4_trouble_relaxing"
            if (
                last_item == "gad_q2_control_worry"
                and session.asked_items.count("gad_q4_trouble_relaxing") >= 1
                and discussable("gad_q3_excessive_worry")
            ):
                return "gad_q3_excessive_worry"
            if last_item == "gad_q2_control_worry":
                if self._has_worry_domain_signal(latest_user_text) and available("gad_q4_trouble_relaxing"):
                    return "gad_q4_trouble_relaxing"
                if discussable("gad_q3_excessive_worry"):
                    return "gad_q3_excessive_worry"
            if last_item == "gad_q3_excessive_worry" and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if last_item == "gad_q4_trouble_relaxing" and discussable("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if "gad_q6_irritability" in latest_signal_items and available("gad_q6_irritability"):
                return "gad_q6_irritability"
            if "gad_q5_restlessness" in latest_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if discussable("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"

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
            if self._has_appetite_signal(latest_user_text) and available("phq_q5_appetite"):
                return "phq_q5_appetite"
            if (
                "phq_q7_concentration" in latest_signal_items
                and discussable("phq_q7_concentration")
                and "phq_q7_concentration" not in session.asked_items[-2:]
            ):
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
            if (
                last_item == "phq_q2_low_mood"
                and not self._has_timing_or_frequency_answer(latest_user_text)
                and self._has_anhedonia_signal(latest_user_text)
                and not self._has_low_mood_signal(latest_user_text)
                and snapshot.items["phq_q1_anhedonia"].status == "resolved"
            ):
                if available("phq_q6_worthlessness"):
                    return "phq_q6_worthlessness"
                if available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if available("phq_q5_appetite"):
                    return "phq_q5_appetite"
            if last_item != "phq_q1_anhedonia" and "phq_q1_anhedonia" in latest_signal_items and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"
            if last_item != "phq_q2_low_mood" and "phq_q2_low_mood" in latest_signal_items and available("phq_q2_low_mood"):
                return "phq_q2_low_mood"
            if target_topic == "focus" and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if target_topic == "mood" and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"

        if last_item == "phq_q6_worthlessness":
            if self._has_self_view_signal(latest_user_text) and available("phq_q6_worthlessness"):
                return "phq_q6_worthlessness"
            if self._has_flat_functioning_signal(latest_user_text) or self._has_functional_impact_answer(latest_user_text):
                if available("phq_q2_low_mood"):
                    return "phq_q2_low_mood"
                if available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if available("phq_q4_fatigue"):
                    return "phq_q4_fatigue"
            if self._has_anhedonia_signal(latest_user_text):
                if available("phq_q2_low_mood"):
                    return "phq_q2_low_mood"
                if available("phq_q1_anhedonia"):
                    return "phq_q1_anhedonia"
                if available("phq_q7_concentration"):
                    return "phq_q7_concentration"
            if self._has_concentration_answer(latest_user_text) and available("phq_q7_concentration"):
                return "phq_q7_concentration"

        if last_item == "phq_q7_concentration":
            if (
                "phq_q4_fatigue" not in held_back
                and snapshot.items["phq_q4_fatigue"].status != "resolved"
                and (
                    "phq_q7_concentration" in latest_signal_items
                    or "focus" in latest_signal_topics
                    or self._has_concentration_answer(latest_user_text)
                )
            ):
                return "phq_q4_fatigue"
            if (
                self._has_anhedonia_signal(latest_user_text)
                and snapshot.items["phq_q1_anhedonia"].status == "resolved"
                and available("phq_q6_worthlessness")
            ):
                return "phq_q6_worthlessness"
            if self._has_appetite_signal(latest_user_text) and available("phq_q5_appetite"):
                return "phq_q5_appetite"
            if (
                self._has_concentration_answer(latest_user_text)
                and snapshot.items["phq_q4_fatigue"].status == "partial"
                and snapshot.items["phq_q4_fatigue"].confidence >= 0.8
                and snapshot.items["phq_q5_appetite"].status == "resolved"
            ):
                for preferred_item in ("phq_q8_psychomotor", "phq_q2_low_mood", "phq_q1_anhedonia"):
                    if available(preferred_item):
                        return preferred_item
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
            if (
                (
                    any(marker in latest_user_text for marker in ("day ke end", "din ke end", "दिन के अंत"))
                    or self._has_activation_signal(latest_user_text)
                    or "phq_q4_fatigue" in latest_signal_items
                    or "energy" in latest_signal_topics
                )
                and snapshot.items["phq_q4_fatigue"].status == "resolved"
                and available("phq_q8_psychomotor")
            ):
                return "phq_q8_psychomotor"
            if (
                snapshot.items["phq_q4_fatigue"].status == "partial"
                and snapshot.items["phq_q4_fatigue"].confidence >= 0.8
                and session.asked_items[-2:].count("phq_q4_fatigue") >= 1
                and any(
                    snapshot.items[related_item].status == "resolved"
                    for related_item in ("phq_q3_sleep", "phq_q5_appetite")
                )
            ):
                for preferred_item in ("phq_q7_concentration", "phq_q8_psychomotor", "phq_q2_low_mood"):
                    if available(preferred_item):
                        return preferred_item
            if self._has_appetite_signal(latest_user_text) and available("phq_q5_appetite"):
                return "phq_q5_appetite"
            if self._has_timing_or_frequency_answer(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if any(marker in latest_user_text for marker in ("day ke end", "din ke end", "दिन के अंत")) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if self._has_activation_signal(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "phq_q4_fatigue" in latest_signal_items and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if "energy" in latest_signal_topics and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"

        if last_item == "phq_q5_appetite":
            if self._has_anhedonia_signal(latest_user_text):
                if available("phq_q2_low_mood"):
                    return "phq_q2_low_mood"
                if available("phq_q1_anhedonia"):
                    return "phq_q1_anhedonia"
            if "phq_q1_anhedonia" in latest_signal_items and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"
            if "phq_q6_worthlessness" in latest_signal_items and available("phq_q6_worthlessness"):
                return "phq_q6_worthlessness"
            if "phq_q7_concentration" in latest_signal_items and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if self._has_appetite_signal(latest_user_text):
                if available("phq_q1_anhedonia"):
                    return "phq_q1_anhedonia"
                if available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if available("phq_q6_worthlessness"):
                    return "phq_q6_worthlessness"

        if last_item == "gad_q2_control_worry" and target_topic == "anxiety":
            if self._has_worry_domain_signal(latest_user_text):
                if session.asked_items.count("gad_q4_trouble_relaxing") >= 1 and discussable("gad_q3_excessive_worry"):
                    return "gad_q3_excessive_worry"
                if available("gad_q4_trouble_relaxing"):
                    return "gad_q4_trouble_relaxing"
            if (
                self._infer_anxiety_channel(latest_user_text) == "mind"
                and self._has_persistent_worry_signal(latest_user_text)
                and available("gad_q3_excessive_worry")
            ):
                return "gad_q3_excessive_worry"
            if "phq_q3_sleep" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if "gad_q4_trouble_relaxing" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"
            if "gad_q5_restlessness" in recent_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if self._has_awful_outcome_signal(latest_user_text) and available("gad_q7_afraid"):
                return "gad_q7_afraid"
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
            if self._has_persistent_worry_signal(latest_user_text) and session.asked_items.count("gad_q2_control_worry") >= 1:
                if available("gad_q4_trouble_relaxing"):
                    return "gad_q4_trouble_relaxing"

        if last_item == "gad_q5_restlessness":
            if self._has_timing_or_frequency_answer(latest_user_text):
                return last_item
            if "gad_q4_trouble_relaxing" in recent_signal_items and available("gad_q4_trouble_relaxing"):
                return "gad_q4_trouble_relaxing"

        if last_item == "gad_q4_trouble_relaxing":
            recent_relax_count = session.asked_items[-3:].count("gad_q4_trouble_relaxing")
            if "gad_q6_irritability" in latest_signal_items and available("gad_q6_irritability"):
                return "gad_q6_irritability"
            if "gad_q5_restlessness" in latest_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if self._has_worry_domain_signal(latest_user_text) and not self._has_worry_scope_answer(latest_user_text):
                return "gad_q3_excessive_worry"
            if (
                recent_relax_count >= 2
                and self._has_lingering_tension_signal(latest_user_text)
                and session.asked_items.count("gad_q2_control_worry") >= 1
                and session.asked_items.count("gad_q3_excessive_worry") >= 1
            ):
                return None
            if (
                self._infer_anxiety_channel(latest_user_text) == "mind"
                and (
                    self._has_persistent_worry_signal(latest_user_text)
                    or self._has_worry_domain_signal(latest_user_text)
                    or "gad_q2_control_worry" in latest_signal_items
                )
                and available("gad_q3_excessive_worry")
            ):
                return "gad_q3_excessive_worry"
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

        if last_item == "gad_q7_afraid":
            if "gad_q6_irritability" in latest_signal_items and available("gad_q6_irritability"):
                return "gad_q6_irritability"
            if "gad_q5_restlessness" in latest_signal_items and available("gad_q5_restlessness"):
                return "gad_q5_restlessness"
            if self._has_worry_domain_signal(latest_user_text) and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"
            if session.asked_items[-2:].count("gad_q7_afraid") >= 1 and available("gad_q3_excessive_worry"):
                return "gad_q3_excessive_worry"

        if (
            last_item == "phq_q3_sleep"
            and (self._has_worry_domain_signal(latest_user_text) or "gad_q3_excessive_worry" in latest_signal_items)
            and not self._has_sleep_pattern_answer(latest_user_text)
            and not self._has_timing_or_frequency_answer(latest_user_text)
            and available("gad_q3_excessive_worry")
        ):
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
            daytime_shift = (
                self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics)
                and not self._has_sleep_pattern_answer(latest_user_text)
                and not self._has_sleep_impact_signal(latest_user_text)
            )
            if daytime_shift:
                if "phq_q5_appetite" in latest_signal_items and available("phq_q5_appetite"):
                    return "phq_q5_appetite"
                if "phq_q4_fatigue" in latest_signal_items and available("phq_q4_fatigue"):
                    return "phq_q4_fatigue"
                if "phq_q7_concentration" in latest_signal_items and available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if "focus" in latest_signal_topics and available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if "energy" in latest_signal_topics and available("phq_q4_fatigue"):
                    return "phq_q4_fatigue"
                if "energy" in latest_signal_topics and available("phq_q5_appetite"):
                    return "phq_q5_appetite"
                if "energy" in latest_signal_topics and available("phq_q7_concentration"):
                    return "phq_q7_concentration"
                if "energy" in latest_signal_topics and available("phq_q8_psychomotor"):
                    return "phq_q8_psychomotor"
                return None
            if self._has_sleep_pattern_answer(latest_user_text):
                return last_item
            if self._has_low_mood_signal(latest_user_text) and available("phq_q2_low_mood"):
                return "phq_q2_low_mood"
            if self._has_anhedonia_signal(latest_user_text):
                if available("phq_q1_anhedonia"):
                    return "phq_q1_anhedonia"
                if available("phq_q2_low_mood"):
                    return "phq_q2_low_mood"
            if self._has_self_view_signal(latest_user_text) and available("phq_q6_worthlessness"):
                return "phq_q6_worthlessness"
            if (
                "gad_q4_trouble_relaxing" in latest_signal_items
                and not self._has_sleep_pattern_answer(latest_user_text)
                and not self._has_timing_or_frequency_answer(latest_user_text)
                and available("gad_q4_trouble_relaxing")
            ):
                return "gad_q4_trouble_relaxing"
            if (
                (self._has_worry_domain_signal(latest_user_text) or "gad_q3_excessive_worry" in latest_signal_items)
                and available("gad_q3_excessive_worry")
            ):
                return "gad_q3_excessive_worry"
            if self._has_sleep_impact_signal(latest_user_text) and available("phq_q4_fatigue"):
                return "phq_q4_fatigue"
            if (
                self._has_frequency_answer(latest_user_text)
                and ("energy" in recent_signal_topics or "phq_q4_fatigue" in recent_signal_items)
                and available("phq_q4_fatigue")
            ):
                return "phq_q4_fatigue"
            if self._has_frequency_answer(latest_user_text) and self._recent_sleep_pattern_known(session):
                if available("phq_q4_fatigue"):
                    return "phq_q4_fatigue"
            if snapshot.items[last_item].status != "resolved" and not daytime_shift:
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
        target_scene: Optional[str] = None,
    ) -> str:
        topic_lookup = {topic.topic_id: topic for topic in topic_states}
        if snapshot.safety.level == "urgent":
            return "Safety escalation overrides normal screening."
        if target_topic == "safety":
            return "Safety cues or mood-linked risk signals justify a direct safety check."
        if target_scene and target_scene in SCENE_GRAPH:
            scene = SCENE_GRAPH[target_scene]
            return f"{scene.label} is still under-covered, so the next turn should clarify that cluster naturally rather than staying on one narrow item."
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
        if item_id == "gad_q7_afraid" and not self._has_awful_outcome_signal(latest_user_text):
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
            if self_view_signal or snapshot.safety.level == "review":
                return False
            return len(user_turns) < 4
        if item_id == "gad_q7_afraid":
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
        latest_user_text = self._latest_user_text(session) if session else ""
        continuity_ready = bool(
            plan.continuity_note
            and plan.user_turns >= 2
            and plan.stage != "rapport"
            and plan.target_topic not in {"rapport", "safety"}
            and plan.current_topic == plan.target_topic
            and (session is None or self._has_recent_checkin_reference(latest_user_text))
        )
        if continuity_ready and plan.user_style.steering_preference != "guided":
            support_line = plan.continuity_note
        elif plan.reflective_anchor and plan.stage != "rapport":
            support_line = plan.reflective_anchor
        elif continuity_ready:
            support_line = plan.continuity_note
        if support_line == plan.continuity_note and self._assistant_history_contains(session, plan.continuity_note):
            support_line = ""
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
        def choose(segment: str) -> str:
            if not segment:
                return ""
            if self._assistant_recently_used_segment(session, segment, lookback=3):
                return ""
            return segment
        latest_user_text = self._latest_user_text(session)
        contextual_reflection = self._build_contextual_reflection(language, plan.target_item, latest_user_text)
        if contextual_reflection:
            return choose(contextual_reflection)
        latest_signal_items = self._latest_signal_items(session)
        if plan.target_item in ITEM_REFLECTIONS:
            selected = choose(ITEM_REFLECTIONS[plan.target_item][language])
            if selected:
                return selected
        for item_id in latest_signal_items:
            if item_id in ITEM_REFLECTIONS:
                selected = choose(ITEM_REFLECTIONS[item_id][language])
                if selected:
                    return selected
        if plan.target_topic in TOPIC_REFLECTIONS:
            return choose(TOPIC_REFLECTIONS[plan.target_topic][language])
        return ""

    def _build_prompt_for_target(self, language: str, plan: DialoguePlan, session: ChatSession) -> Optional[str]:
        item_prompt = self._build_item_prompt(language, plan, session)
        if item_prompt:
            prefer_item_prompt = not plan.target_scene or not plan.closure_mode
            if not prefer_item_prompt and session is not None:
                latest_signal_items = self._latest_signal_items(session)
                latest_user_text = self._latest_user_text(session)
                last_item = session.asked_items[-1] if session.asked_items else None
                if plan.target_item in latest_signal_items:
                    prefer_item_prompt = True
                elif plan.target_item == "phq_q7_concentration" and last_item != plan.target_item:
                    prefer_item_prompt = True
                elif (
                    plan.target_item == "phq_q8_psychomotor"
                    and self._has_timing_or_frequency_answer(latest_user_text)
                ):
                    prefer_item_prompt = True
                elif (
                    plan.target_item == "phq_q4_fatigue"
                    and last_item in {"phq_q3_sleep", "phq_q7_concentration", "phq_q8_psychomotor"}
                    and self._has_timing_or_frequency_answer(latest_user_text)
                ):
                    prefer_item_prompt = True
                elif plan.target_item == "phq_q4_fatigue" and last_item == "phq_q7_concentration":
                    prefer_item_prompt = True
            if prefer_item_prompt:
                return item_prompt
        scene_prompt = self._build_scene_prompt(language, plan, session)
        if scene_prompt:
            return scene_prompt
        if item_prompt:
            return item_prompt
        return TOPIC_PROMPTS.get(plan.target_topic, {}).get(language)

    def _build_scene_prompt(self, language: str, plan: DialoguePlan, session: ChatSession) -> Optional[str]:
        if (
            not plan.target_scene
            or plan.stage not in {"exploration", "clarification"}
        ):
            return None
        latest_user_text = self._latest_user_text(session)
        if plan.closure_mode:
            if plan.user_turns < 5 and not self._has_summary_request(latest_user_text):
                return None
        else:
            if plan.target_scene == "mood_selfview" and plan.user_turns >= 3:
                pass
            elif (
                plan.target_scene == "sleep_functioning"
                and plan.user_turns >= 2
                and self._has_daytime_functioning_signal(
                    self._latest_signal_items(session),
                    self._latest_signal_topics(session),
                )
            ):
                pass
            else:
                return None
        if self._has_summary_request(latest_user_text) and not plan.closure_mode:
            return None
        prompt = SCENE_PROMPTS.get(plan.target_scene, {}).get(language)
        if not prompt:
            return None
        if self._assistant_recently_used_segment(session, prompt, lookback=4):
            return None
        return prompt

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
        def candidate(key: str) -> Optional[str]:
            prompt = prompt_bank.get(key, {}).get(language)
            if not prompt:
                return None
            if self._assistant_recently_used_segment(session, prompt, lookback=4):
                return None
            return prompt
        if plan.target_item == "gad_q4_trouble_relaxing":
            if (
                self._infer_anxiety_channel(latest_user_text) in {"body", "both"}
                and ("sleep" in self._latest_signal_topics(session) or "phq_q3_sleep" in self._latest_signal_items(session))
            ):
                prompt = candidate("repeat_probe")
                if prompt:
                    return prompt
        if plan.target_item == "gad_q4_trouble_relaxing" and last_item in {"gad_q2_control_worry", "gad_q3_excessive_worry"}:
            if self._infer_anxiety_channel(latest_user_text) == "mind":
                prompt = candidate("mind_known")
                if prompt:
                    return prompt
            if self._has_single_issue_scope_answer(latest_user_text):
                prompt = candidate("single_issue_known")
                if prompt:
                    return prompt
            if self._has_worry_domain_signal(latest_user_text):
                prompt = candidate("domain_known")
                if prompt:
                    return prompt
            if (
                self._infer_anxiety_channel(latest_user_text) in {"body", "both"}
                and ("sleep" in self._latest_signal_topics(session) or "phq_q3_sleep" in self._latest_signal_items(session))
            ):
                prompt = candidate("repeat_probe")
                if prompt:
                    return prompt
        if plan.target_item == "gad_q4_trouble_relaxing" and last_item == "gad_q4_trouble_relaxing":
            if (
                recent_repeat_window
                and self._infer_anxiety_channel(latest_user_text) in {"body", "both"}
                and ("sleep" in self._latest_signal_topics(session) or "phq_q3_sleep" in self._latest_signal_items(session))
            ):
                prompt = candidate("repeat_probe")
                if prompt:
                    return prompt
        if plan.target_item == "phq_q2_low_mood":
            if recent_repeat_window and self._has_daylong_mood_answer(latest_user_text):
                prompt = candidate("deepening_probe")
                if prompt:
                    return prompt
            if repeat_count >= 1 and self._has_flat_functioning_signal(latest_user_text):
                prompt = candidate("functional_impact")
                if prompt:
                    return prompt
        if plan.target_item == "phq_q3_sleep":
            if recent_repeat_window and self._has_sleep_pattern_answer(latest_user_text):
                prompt = candidate("pattern_known")
                if prompt:
                    return prompt
            if recent_repeat_window and has_frequency and self._recent_sleep_pattern_known(session):
                prompt = candidate("pattern_and_frequency_known")
                if prompt:
                    return prompt
        if (
            plan.target_item == "phq_q4_fatigue"
            and last_item == "phq_q3_sleep"
            and has_frequency
        ):
            prompt = candidate("frequency_known")
            if prompt:
                return prompt
        if (
            plan.target_item == "phq_q4_fatigue"
            and last_item in {"phq_q3_sleep", "phq_q7_concentration", "phq_q8_psychomotor"}
            and has_timing
        ):
            prompt = candidate("timing_known")
            if prompt:
                return prompt
        if (
            plan.target_item == "phq_q8_psychomotor"
            and last_item in {"phq_q4_fatigue", "phq_q8_psychomotor"}
            and has_timing
        ):
            prompt = candidate("timing_known")
            if prompt:
                return prompt
        if (
            plan.target_item == "phq_q3_sleep"
            and recent_repeat_window
            and self._has_sleep_specific_timing_answer(latest_user_text)
        ):
            prompt = candidate("timing_known")
            if prompt:
                return prompt

        if recent_repeat and has_timing:
            prompt = candidate("timing_known")
            if prompt:
                return prompt
        if recent_repeat and has_frequency:
            prompt = candidate("frequency_known")
            if prompt:
                return prompt
        if repeat_count >= 2 and not (has_timing or has_frequency):
            prompt = candidate("deepening_probe")
            if prompt:
                return prompt
        if recent_repeat_window and not (has_timing or has_frequency):
            prompt = candidate("repeat_probe")
            if prompt:
                return prompt
        return candidate("default")

    def _latest_user_text(self, session: ChatSession) -> str:
        for turn in reversed(session.turns):
            if turn.speaker == "user":
                return self._normalize(turn.text)
        return ""

    def _latest_signal_topics(self, session: ChatSession) -> set[str]:
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return set()
        anxiety_suppressed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        topics = {
            topic_id
            for topic_id, markers in TOPIC_SIGNAL_MARKERS.items()
            if _contains_any_marker(latest_user_text, markers)
            and not (
                topic_id == "mood"
                and not (
                    self._has_anhedonia_signal(latest_user_text)
                    or self._has_low_mood_signal(latest_user_text)
                )
            )
            and not (topic_id == "anxiety" and anxiety_suppressed)
        }
        if self._has_anhedonia_signal(latest_user_text) or self._has_low_mood_signal(latest_user_text):
            topics.add("mood")
        if self._has_sleep_pattern_answer(latest_user_text) or self._has_sleep_impact_signal(latest_user_text):
            topics.add("sleep")
        if self._has_activation_signal(latest_user_text) or self._has_appetite_signal(latest_user_text):
            topics.add("energy")
        if self._has_concentration_answer(latest_user_text):
            topics.add("focus")
        if self._has_self_view_signal(latest_user_text):
            topics.add("self_view")
        if (
            not anxiety_suppressed
            and (
                self._has_persistent_worry_signal(latest_user_text)
                or self._has_worry_domain_signal(latest_user_text)
                or self._has_lingering_tension_signal(latest_user_text)
            )
        ):
            topics.add("anxiety")
        return topics

    def _recent_signal_topics(self, session: ChatSession, lookback: int = 3) -> set[str]:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        if not user_turns:
            return set()
        joined = " ".join(user_turns)
        anxiety_suppressed = (
            self._has_anxiety_downplay_signal(joined)
            and self._has_non_anxiety_salient_signal(joined)
        )
        topics = {
            topic_id
            for topic_id, markers in TOPIC_SIGNAL_MARKERS.items()
            if _contains_any_marker(joined, markers)
            and not (
                topic_id == "mood"
                and not (
                    self._has_anhedonia_signal(joined)
                    or self._has_low_mood_signal(joined)
                )
            )
            and not (topic_id == "anxiety" and anxiety_suppressed)
        }
        if self._has_anhedonia_signal(joined) or self._has_low_mood_signal(joined):
            topics.add("mood")
        if self._has_sleep_pattern_answer(joined) or self._has_sleep_impact_signal(joined):
            topics.add("sleep")
        if self._has_activation_signal(joined) or self._has_appetite_signal(joined):
            topics.add("energy")
        if self._has_concentration_answer(joined):
            topics.add("focus")
        if self._has_self_view_signal(joined):
            topics.add("self_view")
        if (
            not anxiety_suppressed
            and (
                self._has_persistent_worry_signal(joined)
                or self._has_worry_domain_signal(joined)
                or self._has_lingering_tension_signal(joined)
            )
        ):
            topics.add("anxiety")
        return topics

    def _latest_signal_items(self, session: ChatSession) -> set[str]:
        latest_user_text = self._latest_user_text(session)
        if not latest_user_text:
            return set()
        anxiety_suppressed = (
            self._has_anxiety_downplay_signal(latest_user_text)
            and self._has_non_anxiety_salient_signal(latest_user_text)
        )
        signaled_items: set[str] = set()
        for item_id, markers in ITEM_SIGNAL_MARKERS.items():
            if not _contains_any_marker(latest_user_text, markers):
                continue
            if anxiety_suppressed and ITEM_TO_TOPIC.get(item_id) == "anxiety":
                continue
            if item_id == "phq_q2_low_mood" and not self._has_low_mood_signal(latest_user_text):
                continue
            if item_id == "gad_q3_excessive_worry" and not self._has_worry_domain_signal(latest_user_text):
                continue
            signaled_items.add(item_id)
        if self._has_anhedonia_signal(latest_user_text):
            signaled_items.add("phq_q1_anhedonia")
        if self._has_low_mood_signal(latest_user_text):
            signaled_items.add("phq_q2_low_mood")
        if self._has_sleep_pattern_answer(latest_user_text) or self._has_sleep_impact_signal(latest_user_text):
            signaled_items.add("phq_q3_sleep")
        if self._has_activation_signal(latest_user_text):
            signaled_items.add("phq_q4_fatigue")
        if self._has_appetite_signal(latest_user_text):
            signaled_items.add("phq_q5_appetite")
        if self._has_self_view_signal(latest_user_text):
            signaled_items.add("phq_q6_worthlessness")
        if self._has_concentration_answer(latest_user_text):
            signaled_items.add("phq_q7_concentration")
        if not anxiety_suppressed and self._has_persistent_worry_signal(latest_user_text):
            signaled_items.add("gad_q2_control_worry")
        if not anxiety_suppressed and self._has_worry_domain_signal(latest_user_text):
            signaled_items.add("gad_q3_excessive_worry")
        if not anxiety_suppressed and self._has_lingering_tension_signal(latest_user_text):
            signaled_items.add("gad_q4_trouble_relaxing")
        return signaled_items

    def _recent_signal_items(self, session: ChatSession, lookback: int = 3) -> set[str]:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        if not user_turns:
            return set()
        joined = " ".join(user_turns)
        anxiety_suppressed = (
            self._has_anxiety_downplay_signal(joined)
            and self._has_non_anxiety_salient_signal(joined)
        )
        signaled_items: set[str] = set()
        for item_id, markers in ITEM_SIGNAL_MARKERS.items():
            if not _contains_any_marker(joined, markers):
                continue
            if anxiety_suppressed and ITEM_TO_TOPIC.get(item_id) == "anxiety":
                continue
            if item_id == "phq_q2_low_mood" and not self._has_low_mood_signal(joined):
                continue
            if item_id == "gad_q3_excessive_worry" and not self._has_worry_domain_signal(joined):
                continue
            signaled_items.add(item_id)
        if self._has_anhedonia_signal(joined):
            signaled_items.add("phq_q1_anhedonia")
        if self._has_low_mood_signal(joined):
            signaled_items.add("phq_q2_low_mood")
        if self._has_sleep_pattern_answer(joined) or self._has_sleep_impact_signal(joined):
            signaled_items.add("phq_q3_sleep")
        if self._has_activation_signal(joined):
            signaled_items.add("phq_q4_fatigue")
        if self._has_appetite_signal(joined):
            signaled_items.add("phq_q5_appetite")
        if self._has_self_view_signal(joined):
            signaled_items.add("phq_q6_worthlessness")
        if self._has_concentration_answer(joined):
            signaled_items.add("phq_q7_concentration")
        if not anxiety_suppressed and self._has_persistent_worry_signal(joined):
            signaled_items.add("gad_q2_control_worry")
        if not anxiety_suppressed and self._has_worry_domain_signal(joined):
            signaled_items.add("gad_q3_excessive_worry")
        if not anxiety_suppressed and self._has_lingering_tension_signal(joined):
            signaled_items.add("gad_q4_trouble_relaxing")
        return signaled_items

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

    def _assistant_recently_used_segment(
        self,
        session: Optional[ChatSession],
        segment: str,
        *,
        lookback: int = 4,
    ) -> bool:
        if session is None or not segment:
            return False
        normalized_segment = self._normalize(segment)
        if not normalized_segment:
            return False
        assistant_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "assistant"]
        if not assistant_turns:
            return False
        return any(normalized_segment in turn for turn in assistant_turns[-lookback:])

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
            WORKING_SUMMARY_PREFIXES[language],
            ANXIETY_LOOP_CLOSE_PROMPTS[language],
            CLOSING_MESSAGES[language],
            POST_CLOSE_CHOOSER_MESSAGES[language],
            FINAL_REST_MESSAGES[language],
            POST_CLOSE_IDLE_MESSAGES[language],
            *FINAL_HOLD_VARIANTS[language],
        )

    def _recent_post_close_turn_count(self, session: ChatSession, language: str, lookback: int = 6) -> int:
        segments = tuple(self._normalize(segment) for segment in self._post_close_segments(language))
        count = 0
        for turn in [turn for turn in session.turns if turn.speaker == "assistant"][-lookback:]:
            normalized_turn = self._normalize(turn.text)
            if any(segment in normalized_turn for segment in segments):
                count += 1
        return count

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
        if (
            self._has_recent_anxiety_core_coverage(session)
            and (
                self._already_used_segment(last_assistant_text, ANXIETY_LOOP_BREAK_PROMPTS[language])
                or self._already_used_segment(last_assistant_text, ANXIETY_LOOP_CLOSE_PROMPTS[language])
            )
            and (
                self._has_worry_scope_answer(latest_user_text)
                or self._has_timing_or_frequency_answer(latest_user_text)
            )
        ):
            return None
        if self._should_reopen_after_close(session, latest_user_text):
            return None
        if self._is_post_close_echo(session, latest_user_text, language):
            return FINAL_REST_MESSAGES[language]
        if self._is_close_acknowledgement(latest_user_text):
            if self._already_used_segment(last_assistant_text, FINAL_REST_MESSAGES[language]) or self._already_used_segment(last_assistant_text, POST_CLOSE_IDLE_MESSAGES[language]):
                return POST_CLOSE_IDLE_MESSAGES[language]
            if self._recent_post_close_turn_count(session, language) >= 2:
                return POST_CLOSE_IDLE_MESSAGES[language]
            return self._select_post_close_hold_message(session, language)
        if self._is_nonexpansive_followup(latest_user_text):
            if self._already_used_segment(last_assistant_text, FINAL_REST_MESSAGES[language]) or self._already_used_segment(last_assistant_text, POST_CLOSE_IDLE_MESSAGES[language]):
                return POST_CLOSE_IDLE_MESSAGES[language]
            if self._recent_post_close_turn_count(session, language) >= 2:
                return POST_CLOSE_IDLE_MESSAGES[language]
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

    def _has_continue_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in CONTINUE_MARKERS)

    def _has_physical_malaise_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in PHYSICAL_MALAISE_MARKERS)

    def _should_use_physical_clarifier(self, session: ChatSession, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if not self._has_physical_malaise_signal(normalized_text):
            return False
        if self._has_summary_request(normalized_text) or self._has_continue_signal(normalized_text):
            return False
        if self._latest_signal_items(session) or self._latest_signal_topics(session):
            return False
        return True

    def _physical_clarifier_followup_prompt(self, session: ChatSession, normalized_text: str) -> Optional[str]:
        if not normalized_text:
            return None
        if self._has_summary_request(normalized_text) or self._has_continue_signal(normalized_text):
            return None
        if not self._recent_physical_clarifier_active(session):
            return None
        if self._latest_signal_items(session) or self._latest_signal_topics(session):
            return None
        channel = self._classify_physical_clarifier_answer(normalized_text)
        if channel in {"physical", "mixed"}:
            return PHYSICAL_BRIDGE_PROMPTS[session.language]
        if channel == "emotional":
            return RAPPORT_PROMPTS[session.language]
        return None

    def _recent_physical_clarifier_active(self, session: ChatSession) -> bool:
        last_assistant_text = self._last_assistant_text(session)
        if not last_assistant_text:
            return False
        return self._already_used_segment(last_assistant_text, PHYSICAL_CLARIFIER_PROMPTS[session.language])

    def _classify_physical_clarifier_answer(self, normalized_text: str) -> Optional[str]:
        if not normalized_text:
            return None
        comparative_physical_markers = (
            "more physical than emotional",
            "physical than emotional",
            "zyada physical emotional se",
            "emotional se zyada physical",
            "भावनात्मक से ज़्यादा शारीरिक",
            "भावनात्मक से ज्यादा शारीरिक",
        )
        comparative_emotional_markers = (
            "more emotional than physical",
            "emotional than physical",
            "zyada emotional physical se",
            "physical se zyada emotional",
            "शारीरिक से ज़्यादा भावनात्मक",
            "शारीरिक से ज्यादा भावनात्मक",
        )
        mixed_markers = (
            "mix",
            "mixed",
            "both",
            "dono",
            "dono ka mix",
            "mixture",
            "both together",
            "both today",
            "dono hi",
            "दोनों",
            "दोनों का मिश्रण",
        )
        physical_markers = (
            "more physical",
            "mostly physical",
            "physical than emotional",
            "physical zyada",
            "zyada physical",
            "physical hi",
            "body side",
            "body wala",
            "sharirik",
            "शारीरिक",
            "जिस्मानी",
            "physical",
        )
        emotional_markers = (
            "more emotional",
            "mostly emotional",
            "emotional than physical",
            "emotional zyada",
            "zyada emotional",
            "भावनात्मक",
            "jazbaati",
            "emotional",
        )
        if any(marker in normalized_text for marker in comparative_physical_markers):
            return "physical"
        if any(marker in normalized_text for marker in comparative_emotional_markers):
            return "emotional"
        if any(marker in normalized_text for marker in mixed_markers):
            return "mixed"
        physical = any(marker in normalized_text for marker in physical_markers)
        emotional = any(marker in normalized_text for marker in emotional_markers)
        if physical and emotional:
            return "mixed"
        if physical:
            return "physical"
        if emotional:
            return "emotional"
        return None

    def _has_summary_request(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in SUMMARY_REQUEST_MARKERS)

    def _has_recent_checkin_reference(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "last time",
            "since last time",
            "like last time",
            "same as last time",
            "similar to last time",
            "last check in",
            "last check-in",
            "recent check in",
            "recent check-in",
            "previous check in",
            "previous check-in",
            "last session",
            "previous session",
            "pichli baar",
            "pichhli baar",
            "pichhle session",
            "pichhle check in",
            "pichhle check-in",
            "pichli baat",
            "jaise pichli baar",
            "jaise pichhli baar",
            "pahle jaisa",
            "pehle jaisa",
            "phir wahi",
            "dobara wahi",
        )
        return any(marker in normalized_text for marker in markers)

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
        if self._has_summary_request(normalized_text):
            return False
        last_assistant_text = self._last_assistant_text(session)
        in_post_close_context = self._matches_any_segment(last_assistant_text, self._post_close_segments(session.language))
        if not in_post_close_context:
            return False
        if self._has_continue_signal(normalized_text):
            return True
        latest_signal_topics = self._latest_signal_topics(session)
        if self._is_close_acknowledgement(normalized_text) or self._is_nonexpansive_followup(normalized_text):
            return False
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
        return _contains_any_marker(normalized_text, ACTIVATION_MARKERS)

    def _has_appetite_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["phq_q5_appetite"])

    def _has_anhedonia_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["phq_q1_anhedonia"])

    def _has_low_mood_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if _contains_any_marker(
            normalized_text,
            (
                "low energy",
                "feel low energy",
                "feel low on energy",
                "energy low",
                "energy down",
                "energy bhi low",
                "energy low rehti",
                "din bhar energy low",
                "low on energy",
            ),
        ):
            explicit_mood_markers = (
                "sad",
                "empty",
                "days feel heavy",
                "day feels heavy",
                "heavy mood",
                "उदास",
                "उदासी",
                "मन भारी",
                "भारी",
            )
            if not _contains_any_marker(normalized_text, explicit_mood_markers):
                return False
        return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["phq_q2_low_mood"])

    def _has_self_view_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["phq_q6_worthlessness"])

    def _has_sleep_pattern_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, SLEEP_PATTERN_MARKERS)

    def _has_sleep_impact_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, SLEEP_IMPACT_MARKERS)

    def _has_sleep_specific_timing_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if not self._has_timing_answer(normalized_text):
            return False
        generic_daylong_markers = (
            "day long",
            "through the day",
            "all day",
            "most of the day",
            "दिन भर",
            "पूरे दिन",
            "पूरा दिन",
            "poore din",
            "poora din",
            "din bhar",
        )
        if _contains_any_marker(normalized_text, generic_daylong_markers):
            sleep_context_markers = (
                "sleep",
                "asleep",
                "neend",
                "नींद",
                "night",
                "nights",
                "raat",
                "रात",
                "morning",
                "mornings",
                "subah",
                "सुबह",
            )
            return _contains_any_marker(normalized_text, sleep_context_markers)
        return True

    def _has_daytime_functioning_signal(
        self,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> bool:
        if {"energy", "focus"} & latest_signal_topics:
            return True
        return bool(
            {
                item_id
                for item_id in latest_signal_items
                if item_id in {"phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"}
            }
        )

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
        return _contains_any_marker(normalized_text, markers)

    def _has_timing_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, TIME_MARKERS)

    def _has_frequency_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, FREQUENCY_MARKERS) or any(
            pattern.search(normalized_text) for pattern in FREQUENCY_PATTERNS
        )

    def _has_worry_domain_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        explicit_markers = (
            "work and future",
            "work aur future",
            "kaam aur future",
            "kaam or future",
            "future and job",
            "job aur future",
            "work ko lekar",
            "kaam ko lekar",
            "naukri ko lekar",
            "job ko लेकर",
            "future ko लेकर",
            "future ke around",
            "job ke around",
            "work ke around",
            "family ko लेकर",
            "money ko लेकर",
            "काम को लेकर",
            "नौकरी को लेकर",
            "भविष्य को लेकर",
            "परिवार को लेकर",
            "पैसों को लेकर",
            "mess up my future",
            "whether i will keep my job",
            "whether i'll keep my job",
            "whether i will get a job",
            "naukri lagegi",
            "job lagegi",
            "नौकरी लगेगी",
            "kya hoga",
            "kya kya hoga",
            "future ka kya hoga",
            "bhavishya ka kya hoga",
            "भविष्य में क्या होगा",
            "क्या क्या होगा",
            "क्या होगा",
            "falling behind",
            "get behind",
            "behind on work",
            "काम पीछे न रह जाए",
            "काम पीछे न रह जाऊं",
            "काम पीछे न रह जाऊँ",
        )
        if _contains_any_marker(normalized_text, explicit_markers):
            return True

        generic_domains = (
            "work",
            "kaam",
            "job",
            "naukri",
            "money",
            "paise",
            "paisa",
            "family",
            "parivar",
            "future",
            "bhavishya",
            "rent",
            "exam",
            "office",
            "studies",
            "mother",
            "mom",
            "father",
            "dad",
            "maa",
            "mummy",
            "papa",
            "काम",
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
        worry_context = (
            "worry",
            "worried",
            "anxiety",
            "anxious",
            "concern",
            "stress",
            "stressed",
            "pressure",
            "loop",
            "looping",
            "mind keeps running",
            "mind won't stop",
            "mind wont stop",
            "keep thinking",
            "keep thinking about",
            "cannot stop thinking about",
            "can't stop thinking about",
            "चिंता",
            "घबराहट",
            "चलती रहती",
            "चलता रहता",
            "रुकती नहीं",
            "रुकता नहीं",
            "rukte nahi",
            "chalta rehta",
            "चलते रहता",
            "बार बार सोच",
            "बार-बार सोच",
            "बार बार दिमाग",
            "बार-बार दिमाग",
            "बार-बार यही",
            "बार बार यही",
            "sochta rehta",
            "sochte rehta",
            "sochte rehti",
            "soch chalti rehti",
            "soch chalti rehti hai",
        )
        domain_hits = _count_markers(normalized_text, generic_domains)
        domain_frame_markers = (
            "ko lekar",
            "को लेकर",
            "about",
            "around",
            "between",
            "is baat",
            "इस बात",
            "के बारे",
            "के बीच",
            "ke beech",
            "ke around",
        )
        if domain_hits >= 2 and _contains_any_marker(normalized_text, worry_context):
            return True
        if domain_hits >= 1 and _contains_any_marker(normalized_text, worry_context):
            return (
                self._has_persistent_worry_signal(normalized_text)
                or _contains_any_marker(normalized_text, domain_frame_markers)
                or self._has_worry_scope_answer(normalized_text)
            )
        return domain_hits >= 2 and _contains_any_marker(normalized_text, domain_frame_markers) and self._has_persistent_worry_signal(normalized_text)

    def _has_awful_outcome_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, AWFUL_OUTCOME_MARKERS)

    def _has_persistent_worry_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._has_flat_functioning_signal(normalized_text) and not _contains_any_marker(
            normalized_text,
            (
                "worry",
                "anxiety",
                "thoughts",
                "mind",
                "soch",
                "dimaag",
                "dimag",
                "चिंता",
                "घबर",
                "दिमाग",
                "सोच",
            ),
        ):
            return False
        return _contains_any_marker(normalized_text, PERSISTENT_WORRY_MARKERS)

    def _has_strong_anxiety_domain_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._has_anxiety_downplay_signal(normalized_text) and self._has_non_anxiety_salient_signal(normalized_text):
            return False
        return self._has_worry_domain_signal(normalized_text) and (
            self._has_persistent_worry_signal(normalized_text)
            or _contains_any_marker(normalized_text, ("चिंता", "घबराहट", "worry", "anxiety"))
        )

    def _is_repetitive_persistent_worry_echo(self, normalized_text: str) -> bool:
        if not normalized_text or not self._has_persistent_worry_signal(normalized_text):
            return False
        if (
            self._has_worry_domain_signal(normalized_text)
            or self._has_worry_scope_answer(normalized_text)
            or self._has_lingering_tension_signal(normalized_text)
            or self._has_timing_or_frequency_answer(normalized_text)
            or self._has_awful_outcome_signal(normalized_text)
        ):
            return False
        repetitive_markers = (
            "no matter how much i try",
            "going no matter",
            "kitni bhi koshish",
            "कितनी भी कोशिश",
            "कितना भी प्रयास",
            "चलती रहती है",
            "चलते रहता है",
            "चले",
            "stays going",
            "still keeps going",
            "keeps going",
            "keep going",
        )
        return _contains_any_marker(normalized_text, repetitive_markers) or len(normalized_text.split()) <= 9

    def _has_anxiety_downplay_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "worry utni nahi",
            "worry itni nahi",
            "anxiety utni nahi",
            "anxiety itni nahi",
            "worry not much",
            "not much worry",
            "not really worry",
            "not really anxious",
            "not very anxious",
            "not really panic",
            "not really panic exactly",
            "not panic exactly",
            "panic is not the main issue",
            "panic is not the main thing",
            "anxiety is not the main issue",
            "worry is not the main issue",
            "worry is not the main thing",
            "anxiety is not the main thing",
            "it is not anxiety",
            "its not anxiety",
            "panic nahi",
            "panic jaisa nahi",
            "panic jaisa nahi hai",
            "panic jaisa exactly nahi hai",
            "panic jaisa nahi hota",
            "panic jaisa nahi lagta",
            "panic jaisa exactly nahi hota",
            "panic jaisa exactly nahi lagta",
            "ghabrahat jaisa nahi",
            "ghabrahat jaisa nahi hai",
            "ghabrahat jaisa nahi hota",
            "ghabrahat jaisa nahi lagta",
            "more like low energy than worry",
            "more low energy than worry",
            "more sadness than worry",
            "more tired than worried",
            "zyada low energy jaisa lagta hai",
            "zyada low energy jaisa lag rahi hai",
            "zyada low energy lagta hai",
            "zyada low energy lag rahi hai",
            "more like low energy jaisa",
            "low energy jaisa lagta hai",
            "low energy jaisa lag rahi hai",
            "worry is smaller",
            "worry is not the main part",
            "worry nahi bas",
            "anxiety nahi bas",
            "bas thakan",
            "bas udasi",
            "चिंता उतनी नहीं",
            "इतनी चिंता नहीं",
            "चिंता मुख्य बात नहीं",
            "चिंता मुख्य मुद्दा नहीं",
            "घबराहट जैसा नहीं है",
            "घबराहट नहीं है",
            "घबराहट जैसा नहीं होता",
            "घबराहट जैसा नहीं लगता",
            "बस थकान",
            "बस उदासी",
            "ज़्यादा थकान",
            "ज्यादा थकान",
            "ज़्यादा उदासी",
            "ज्यादा उदासी",
        )
        return _contains_any_marker(normalized_text, markers)

    def _has_non_anxiety_salient_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(
            (
                self._has_anhedonia_signal(normalized_text),
                self._has_low_mood_signal(normalized_text),
                self._has_sleep_pattern_answer(normalized_text),
                self._has_sleep_impact_signal(normalized_text),
                self._has_activation_signal(normalized_text),
                self._has_appetite_signal(normalized_text),
                self._has_self_view_signal(normalized_text),
                self._has_concentration_answer(normalized_text),
            )
        )

    def _has_lingering_tension_signal(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, LINGERING_TENSION_MARKERS)

    def _has_worry_scope_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, WORRY_SCOPE_SPREAD_MARKERS) or _contains_any_marker(
            normalized_text,
            WORRY_SCOPE_SINGLE_MARKERS,
        )

    def _has_single_issue_scope_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return _contains_any_marker(normalized_text, WORRY_SCOPE_SINGLE_MARKERS)

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
        return _contains_any_marker(normalized_text, flat_markers)

    def _has_daylong_mood_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "day long",
            "through the day",
            "all day",
            "most of the day",
            "din bhar",
            "poora din",
            "poore din",
            "दिन भर",
            "पूरा दिन",
            "पूरे दिन",
        )
        return _contains_any_marker(normalized_text, markers)

    def _has_functional_impact_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "work days",
            "on work days",
            "work day",
            "workday",
            "workdays",
            "work days par",
            "work day par",
            "काम वाले दिन",
            "काम वाले दिनों",
            "काम वाले दिनों में",
            "still get through",
            "still getting through",
            "function on the outside",
            "bahar se",
            "flat underneath",
        )
        return _contains_any_marker(normalized_text, markers)

    def _has_concentration_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        markers = (
            "focus slips",
            "attention slips",
            "harder to focus",
            "hard to focus",
            "cannot focus",
            "can't focus",
            "focus on one thing",
            "attention drifts",
            "mind wanders",
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
            "ध्यान नहीं टिक",
            "ध्यान टिकता नहीं",
            "ध्यान भी टिकता नहीं",
            "ध्यान भी नहीं टिकता",
            "वापस लौट",
        )
        return _contains_any_marker(normalized_text, markers)

    def _has_fresh_item_signal_for_routing(
        self,
        item_id: str,
        normalized_text: str,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> bool:
        if item_id in latest_signal_items:
            return True
        if item_id == "phq_q1_anhedonia":
            return self._has_anhedonia_signal(normalized_text)
        if item_id == "phq_q2_low_mood":
            return self._has_low_mood_signal(normalized_text)
        if item_id == "phq_q3_sleep":
            return self._has_sleep_pattern_answer(normalized_text) or self._has_sleep_impact_signal(normalized_text)
        if item_id == "phq_q4_fatigue":
            return self._has_activation_signal(normalized_text)
        if item_id == "phq_q5_appetite":
            return self._has_appetite_signal(normalized_text)
        if item_id == "phq_q6_worthlessness":
            return self._has_self_view_signal(normalized_text)
        if item_id == "phq_q7_concentration":
            return self._has_concentration_answer(normalized_text)
        if item_id == "phq_q8_psychomotor":
            return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["phq_q8_psychomotor"])
        if item_id == "gad_q1_nervous":
            return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["gad_q1_nervous"])
        if item_id == "gad_q2_control_worry":
            return self._has_persistent_worry_signal(normalized_text)
        if item_id == "gad_q3_excessive_worry":
            return self._has_worry_domain_signal(normalized_text) or self._has_worry_scope_answer(normalized_text)
        if item_id == "gad_q4_trouble_relaxing":
            return self._has_lingering_tension_signal(normalized_text) or _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["gad_q4_trouble_relaxing"])
        if item_id == "gad_q5_restlessness":
            return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["gad_q5_restlessness"])
        if item_id == "gad_q6_irritability":
            return _contains_any_marker(normalized_text, ITEM_SIGNAL_MARKERS["gad_q6_irritability"])
        if item_id == "gad_q7_afraid":
            return self._has_awful_outcome_signal(normalized_text)
        topic_id = ITEM_TO_TOPIC.get(item_id)
        return bool(topic_id and topic_id in latest_signal_topics)

    def _topic_has_fresh_routing_signal(
        self,
        topic_id: str,
        normalized_text: str,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> bool:
        if not topic_id:
            return False
        if topic_id in latest_signal_topics:
            return True
        topic_node = TOPIC_GRAPH.get(topic_id)
        if not topic_node:
            return False
        return any(
            self._has_fresh_item_signal_for_routing(item_id, normalized_text, latest_signal_items, latest_signal_topics)
            for item_id in topic_node.item_ids
        )

    def _scene_has_fresh_routing_signal(
        self,
        scene: SceneNode,
        normalized_text: str,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> bool:
        if any(item_id in latest_signal_items for item_id in scene.item_ids):
            return True
        if any(topic_id in latest_signal_topics for topic_id in scene.topic_ids):
            return True
        return any(
            self._has_fresh_item_signal_for_routing(item_id, normalized_text, latest_signal_items, latest_signal_topics)
            for item_id in scene.item_ids
        )

    def _breadth_request_exhausted_topics(
        self,
        session: ChatSession,
        normalized_text: str,
        latest_signal_items: set[str],
        latest_signal_topics: set[str],
    ) -> set[str]:
        recent_items = session.asked_items[-4:]
        if len(recent_items) < 2:
            return set()

        exhausted_topics: set[str] = set()
        recent_topics = [ITEM_TO_TOPIC.get(item_id) for item_id in recent_items if ITEM_TO_TOPIC.get(item_id)]

        for item_id in set(recent_items):
            topic_id = ITEM_TO_TOPIC.get(item_id)
            if not topic_id or session.asked_items.count(item_id) < 2:
                continue
            if self._has_fresh_item_signal_for_routing(item_id, normalized_text, latest_signal_items, latest_signal_topics):
                continue
            exhausted_topics.add(topic_id)

        for topic_id in set(recent_topics):
            if recent_topics.count(topic_id) < 2:
                continue
            if self._topic_has_fresh_routing_signal(topic_id, normalized_text, latest_signal_items, latest_signal_topics):
                continue
            exhausted_topics.add(topic_id)

        for scene in SCENE_GRAPH.values():
            recent_scene_items = [item_id for item_id in recent_items if item_id in scene.item_ids]
            if len(recent_scene_items) < 3:
                continue
            if self._scene_has_fresh_routing_signal(scene, normalized_text, latest_signal_items, latest_signal_topics):
                continue
            exhausted_topics.update(scene.topic_ids)

        return exhausted_topics

    def _recent_sleep_pattern_known(self, session: ChatSession, lookback: int = 3) -> bool:
        user_turns = [self._normalize(turn.text) for turn in session.turns if turn.speaker == "user"][-lookback:]
        return any(self._has_sleep_pattern_answer(text) for text in user_turns)

    def _has_new_anxiety_branch_detail(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if self._is_repetitive_persistent_worry_echo(normalized_text):
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
        if self._is_nonexpansive_followup(normalized_text):
            return False
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
        latest_signal_topics = self._latest_signal_topics(session)
        if self._has_summary_request(normalized_text):
            return None
        if (
            last_item in {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}
            and self._has_anxiety_downplay_signal(normalized_text)
            and self._has_non_anxiety_salient_signal(normalized_text)
        ):
            return None
        if last_item == "phq_q7_concentration" and self._has_concentration_answer(normalized_text):
            if "phq_q4_fatigue" not in held_back_items and snapshot.items["phq_q4_fatigue"].status != "resolved":
                return None
        if last_item == "phq_q3_sleep":
            if (
                self._has_sleep_specific_timing_answer(normalized_text)
                or (
                    self._has_sleep_pattern_answer(normalized_text)
                    and not any(
                        (
                            self._has_activation_signal(normalized_text),
                            self._has_appetite_signal(normalized_text),
                            self._has_concentration_answer(normalized_text),
                        )
                    )
                )
            ):
                return last_item
            if self._has_frequency_answer(normalized_text):
                if (
                    self._recent_sleep_pattern_known(session)
                    and "phq_q4_fatigue" not in held_back_items
                    and snapshot.items["phq_q4_fatigue"].status != "resolved"
                ):
                    return None
                return last_item
        if (
            last_item == "phq_q4_fatigue"
            and session.asked_items[-2:].count("phq_q4_fatigue") == 1
            and snapshot.items["phq_q4_fatigue"].status != "resolved"
            and not any(
                item_id in latest_signal_items
                for item_id in {"phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"}
            )
            and (
                any(
                    (
                        self._has_low_mood_signal(normalized_text),
                        self._has_anhedonia_signal(normalized_text),
                        self._has_self_view_signal(normalized_text),
                    )
                )
                or any(
                    item_id in latest_signal_items
                    for item_id in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"}
                )
            )
        ):
            return None
        if last_item == "phq_q4_fatigue" and any(
            item_id in latest_signal_items
            for item_id in {"phq_q5_appetite", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q8_psychomotor"}
        ):
            return None
        if last_item in {"phq_q1_anhedonia", "phq_q2_low_mood"} and any(
            item_id in latest_signal_items
            for item_id in {"phq_q4_fatigue", "phq_q5_appetite", "phq_q6_worthlessness", "phq_q7_concentration", "phq_q8_psychomotor"}
        ):
            return None
        if any(ITEM_TO_TOPIC.get(item_id) != ITEM_TO_TOPIC.get(last_item) for item_id in latest_signal_items):
            return None
        if any(topic_id != ITEM_TO_TOPIC.get(last_item) for topic_id in latest_signal_topics if topic_id != "safety"):
            return None
        if (
            last_item == "phq_q3_sleep"
            and self._has_daytime_functioning_signal(latest_signal_items, latest_signal_topics)
            and not self._has_sleep_pattern_answer(normalized_text)
            and not self._has_sleep_impact_signal(normalized_text)
        ):
            return None
        if (
            last_item == "phq_q3_sleep"
            and "gad_q4_trouble_relaxing" in latest_signal_items
            and not self._has_sleep_pattern_answer(normalized_text)
            and not self._has_timing_or_frequency_answer(normalized_text)
        ):
            return None
        if snapshot.items[last_item].status == "resolved":
            has_timing_variant = self._has_timing_answer(normalized_text)
            if last_item == "phq_q3_sleep":
                has_timing_variant = self._has_sleep_specific_timing_answer(normalized_text)
            prompt_bank = ITEM_FOLLOW_UPS.get(last_item, {})
            has_variant = (
                ("timing_known" in prompt_bank and has_timing_variant)
                or ("frequency_known" in prompt_bank and self._has_frequency_answer(normalized_text))
                or (
                    last_item == "phq_q3_sleep"
                    and "pattern_known" in prompt_bank
                    and self._has_sleep_pattern_answer(normalized_text)
                )
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
        if self._should_use_physical_clarifier(session, self._latest_user_text(session)):
            return ""
        latest_user_text = self._latest_user_text(session)
        explicit_reference = self._has_recent_checkin_reference(latest_user_text)
        user_turn_count = len([turn for turn in session.turns if turn.speaker == "user"])
        if user_turn_count > 2:
            return ""
        recent = getattr(session.profile, "recent_checkins", None) or []
        if not recent:
            return ""
        latest = recent[0] if isinstance(recent[0], dict) else None
        if not latest:
            return ""
        recent_topic_key = str(latest.get("topic") or "check_in").replace(" ", "_").lower()
        latest_signal_topics = self._latest_signal_topics(session)
        if not explicit_reference and recent_topic_key != target_topic and recent_topic_key not in latest_signal_topics:
            return ""
        if recent_topic_key != target_topic and recent_topic_key not in latest_signal_topics:
            return ""
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
        has_recent_checkin = bool(getattr(session.profile, "recent_checkins", None))
        if fatigue == "high" or user_style.openness == "guarded" or user_style.verbosity == "brief":
            order.append("choice")
        if stage == "safety" or target_topic == "safety":
            order.extend(["safety", "support", "choice"])
        if target_topic in {"mood", "sleep", "anxiety", "focus", "self_view", "energy"}:
            order.append(target_topic)
        if target_topic == "anxiety":
            order.extend(["body", "scale"])
        elif target_topic == "sleep":
            order.extend(["timing", "sleep", "impact"])
        elif target_topic == "mood":
            order.extend(["impact", "compare", "support"])
        elif target_topic == "self_view":
            order.extend(["compare", "support", "impact"])
        elif target_topic == "focus":
            order.extend(["example", "impact", "coping"])
        elif target_topic == "energy":
            order.extend(["impact", "timing", "example"])
        if has_recent_checkin:
            order.append("compare")

        if fatigue == "high":
            order.extend(["choice", "scale", "impact"])
        elif user_style.openness == "guarded":
            order.extend(["choice", "example", "impact", "support"])
        elif user_style.verbosity == "brief":
            order.extend(["example", "timing", "scale", "impact"])
        elif user_style.verbosity == "detailed":
            order.extend(["compare", "coping", "impact", "example"])
        elif user_style.steering_preference == "user_led":
            order.extend(["compare", "coping", "impact", "example"])
        else:
            order.extend(["example", "impact", "timing", "coping"])

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
