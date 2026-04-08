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
    "en": "I have enough detail for a structured summary now. I can still ask one more follow-up if you want to clarify anything.",
    "hi": "मेरे पास अब एक संरचित सार के लिए काफ़ी जानकारी है। अगर आप चाहें तो मैं एक और पूरक सवाल पूछ सकता हूँ।",
    "hinglish": "Ab mere paas structured summary ke liye enough detail hai. Agar aap chaho to ek aur follow-up le sakte hain.",
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
)
FREQUENCY_MARKERS = (
    "every day",
    "daily",
    "days a week",
    "times a week",
    "week",
    "weeks",
    "most days",
    "usually",
    "often",
    "4 days",
    "3 days",
    "roz",
    "har din",
    "hafte",
    "baar",
    "दिन",
    "दिनों",
    "हफ़्ते",
    "हफ्ते",
    "बार",
    "रोज़",
    "रोज",
    "हर दिन",
    "अक्सर",
    "ज़्यादातर",
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
        "timing_known": {
            "en": "That timing helps. When it happens, is it more trouble falling asleep, staying asleep, or waking up too early?",
            "hi": "यह समय-सूचना मददगार है। जब ऐसा होता है, क्या ज़्यादा मुश्किल नींद आने में होती है, नींद बनाए रखने में, या बहुत जल्दी उठ जाने में?",
            "hinglish": "Yeh timing helpful hai. Jab yeh hota hai, kya zyada issue sleep start hone mein hota hai, sleep banaye rakhne mein, ya bahut jaldi uth jaane mein?",
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
    "gad_q4_trouble_relaxing": {
        "default": {
            "en": "When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?",
            "hi": "जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल दिमाग को शांत करना होता है, शरीर को ढीला करना, या दोनों?",
            "hinglish": "Jab aap settle hone ki koshish karte ho, kya zyada mushkil thoughts ko quiet karna hota hai, body relax karna, ya dono?",
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
    "phq_q1_anhedonia": ("not interested", "no interest", "disconnected", "nothing feels good", "usually enjoy", "used to enjoy", "mann nahi lagta", "मन नहीं लगता", "दिल नहीं करता"),
    "phq_q2_low_mood": ("low mood", "sad", "down", "empty", "heavy", "heaviness", "मन भारी", "भारी", "उदास"),
    "phq_q6_worthlessness": ("burden", "worthless", "useless", "बोझ", "बेकार", "मेरी वजह से"),
    "phq_q3_sleep": ("sleep", "asleep", "wake", "waking", "sleep disturb", "neend disturb", "नींद", "रात", "रात में", "उठ जाती", "switch off"),
    "phq_q7_concentration": ("focus", "concentrat", "attention", "cannot focus", "can't focus", "ध्यान", "focus nahi", "ध्यान नहीं टिक", "mind blanks", "screen"),
    "gad_q2_control_worry": ("worry", "loop", "looping", "replay", "mind won't stop", "mind wont stop", "चिंता", "सोच बंद"),
    "gad_q3_excessive_worry": ("future", "rent", "family", "money", "what if", "awful", "सब कुछ", "हर बात"),
    "gad_q4_trouble_relaxing": ("switch off", "settle down", "quiet your thoughts", "तनाव", "शांत", "relax", "off karna", "busy mind", "tense body", "body tense", "tense lagti"),
    "gad_q5_restlessness": ("restless", "restlessness", "sit still", "pacing", "बेचैनी", "chain se baith", "move around"),
}

TOPIC_SIGNAL_MARKERS: Dict[str, Tuple[str, ...]] = {
    "mood": ("low mood", "sad", "down", "empty", "heavy", "heaviness", "disconnected", "usually enjoy", "used to enjoy", "उदासी", "उदास", "खाली", "low feel", "भारी", "मन भारी", "मन नहीं लगता"),
    "sleep": ("sleep", "asleep", "wake up", "waking", "neend", "नींद", "सोने", "उठ जाती", "night", "रात"),
    "energy": ("tired", "drained", "fatigue", "wiped", "थक", "थका", "थकान", "ऊर्जा"),
    "self_view": ("burden", "worthless", "useless", "guilt", "बोझ", "बेकार", "गलती मेरी", "worthless"),
    "focus": ("focus", "concentrat", "attention", "mind blanks", "cannot focus", "can't focus", "ध्यान", "focus nahi", "ध्यान नहीं", "ध्यान नहीं टिक", "screen"),
    "anxiety": ("worry", "restless", "tense", "panic", "loop", "बेचैनी", "चिंता", "घबराहट", "mind won't stop"),
    "safety": ("hurt myself", "not wake up", "suicide", "मर", "खुद को नुकसान", "zinda na"),
}

AFFECTIVE_TOPIC_FAMILY = {"mood", "sleep", "energy", "self_view", "focus"}


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

        if snapshot.safety.level == "urgent" or plan.next_action == "handoff":
            return SAFETY_MESSAGES[language], plan.target_item
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
        recent_signal_topics = self._recent_signal_topics(session)

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
        ]
        if not candidates:
            return current_topic if current_topic in TOPIC_GRAPH else "mood"

        recent_topics = [ITEM_TO_TOPIC.get(item_id) for item_id in session.asked_items[-3:] if ITEM_TO_TOPIC.get(item_id)]
        affective_signal_active = bool(latest_signal_topics & AFFECTIVE_TOPIC_FAMILY)
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

        def available(item_id: str) -> bool:
            return (
                item_id not in held_back
                and item_id in snapshot.items
                and snapshot.items[item_id].status != "resolved"
            )

        if last_item in {"phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness"}:
            if "phq_q7_concentration" in recent_signal_items and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if last_item != "phq_q1_anhedonia" and "phq_q1_anhedonia" in recent_signal_items and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"
            if last_item != "phq_q2_low_mood" and "phq_q2_low_mood" in recent_signal_items and available("phq_q2_low_mood"):
                return "phq_q2_low_mood"
            if target_topic == "focus" and available("phq_q7_concentration"):
                return "phq_q7_concentration"
            if target_topic == "mood" and available("phq_q1_anhedonia"):
                return "phq_q1_anhedonia"

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
        if snapshot.safety.level == "urgent":
            return False
        if item_id == "phq_q9_self_harm" and snapshot.safety.level == "review" and self._has_explicit_safety_signal(snapshot):
            return False
        mood_signal = any(
            snapshot.items[key].value is not None and snapshot.items[key].value >= 2
            for key in ("phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness")
        )
        if item_id == "phq_q9_self_harm":
            return len(user_turns) < 3 and not mood_signal
        if item_id == "phq_q6_worthlessness":
            return len(user_turns) < 2 and not mood_signal
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

    def _compose_prompt(
        self,
        language: str,
        base_prompt: str,
        plan: DialoguePlan,
        session: Optional[ChatSession] = None,
    ) -> str:
        prefix = REFLECTION_PREFIXES[language][plan.user_style.empathy_level]
        suffix = self._style_suffix(language, plan)
        last_assistant_text = self._last_assistant_text(session)
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
        latest_user_text = self._latest_user_text(session) if session else ""
        if repeated_topic_probe and self._has_timing_or_frequency_answer(latest_user_text):
            support_line = ""
        if self._already_used_segment(last_assistant_text, support_line):
            support_line = ""
        use_prefix = (
            prefix
            and not repeated_topic_probe
            and not self._already_used_segment(last_assistant_text, prefix)
            and (not support_line or plan.stage == "rapport")
        )
        if use_prefix:
            parts.append(prefix)
        if support_line:
            parts.append(support_line)
        parts.append(base_prompt)
        if suffix:
            parts.append(suffix)
        return " ".join(part.strip() for part in parts if part and part.strip())

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
        has_timing = self._has_timing_answer(latest_user_text)
        has_frequency = self._has_frequency_answer(latest_user_text)

        if recent_repeat and has_frequency and "frequency_known" in prompt_bank:
            return prompt_bank["frequency_known"][language]
        if recent_repeat and (has_timing or has_frequency) and "timing_known" in prompt_bank:
            return prompt_bank["timing_known"][language]
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

    def _already_used_segment(self, normalized_last_assistant: str, segment: str) -> bool:
        if not normalized_last_assistant or not segment:
            return False
        normalized_segment = self._normalize(segment)
        if not normalized_segment:
            return False
        return normalized_segment in normalized_last_assistant

    def _has_timing_or_frequency_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in TIME_MARKERS + FREQUENCY_MARKERS)

    def _has_timing_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in TIME_MARKERS)

    def _has_frequency_answer(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        return any(marker in normalized_text for marker in FREQUENCY_MARKERS)

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
        if snapshot.items[last_item].status == "resolved":
            return None
        if fatigue == "high" and snapshot.items[last_item].status not in {"contradicted", "abstained"}:
            return None

        last_user_turn = next((turn for turn in reversed(session.turns) if turn.speaker == "user"), None)
        last_assistant_turn = next((turn for turn in reversed(session.turns) if turn.speaker == "assistant"), None)
        if last_user_turn is None or last_assistant_turn is None or "?" not in last_assistant_turn.text:
            return None

        normalized_text = self._normalize(last_user_turn.text)
        words = len(last_user_turn.text.split())
        short_followup = words <= 6 or any(marker == normalized_text for marker in SHORT_FOLLOWUP_MARKERS)
        if self._has_timing_or_frequency_answer(normalized_text):
            return last_item
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
