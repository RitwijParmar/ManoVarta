#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = PROJECT_ROOT / "data" / "seed"


BASE_CONVERSATION_FILES = [
    "conversations.json",
    "conversations_extended.json",
    "conversations_scaleup.json",
    "conversations_nuance_pack.json",
]


ASSISTANT_VARIANTS = {
    "en": {
        "guarded_minimize": [
            "Starting with the part you usually downplay, what has felt heaviest lately?",
            "If you look past the “I’m managing” version, what actually happens day to day?",
            "What changes show up around sleep, food, energy, or focus when it builds up?",
            "When things get especially quiet or heavy, what thoughts about yourself tend to show up?",
        ],
        "functional_masking": [
            "From the outside, what probably looks normal right now even though it feels different inside?",
            "Once you have pushed through the necessary tasks, what drops or unravels afterward?",
            "What has the strain changed around rest, attention, or motivation outside work or class?",
            "What worries keep looping once the busy part of the day ends?",
        ],
        "temporal_self_correction": [
            "If you think in terms of the last two weeks, what has been most inconsistent or hardest to pin down?",
            "Have there been moments where you first told yourself it was fine and then realized it really was not?",
            "How do the harder moments show up in sleep, routine, or concentration across different days?",
            "When you replay the roughest moments, what meaning do you end up attaching to them?",
        ],
    },
    "hi": {
        "guarded_minimize": [
            "जिस हिस्से को आप अक्सर हल्का करके बता देते हैं, वही हिस्सा इन दिनों सबसे भारी कैसे लग रहा है?",
            "अगर “मैं संभाल रहा हूँ” वाली बात थोड़ी हटाएँ, तो रोजमर्रा में असल में क्या हो रहा है?",
            "जब यह सब बढ़ता है, तो नींद, भूख, थकान या ध्यान में क्या बदलाव दिखते हैं?",
            "जब बात ज़्यादा भारी हो जाती है, तब अपने बारे में किस तरह की सोच आती है?",
        ],
        "functional_masking": [
            "ऊपर से कौन-सी चीज़ें सामान्य दिखती हैं, जबकि भीतर अनुभव कुछ और होता है?",
            "ज़रूरी काम निपटाने के बाद आपके अंदर क्या टूटता या गिरता हुआ महसूस होता है?",
            "इस दबाव ने आराम, ध्यान या रोजमर्रा की इच्छा पर क्या असर डाला है?",
            "दिन खत्म होने के बाद दिमाग सबसे ज़्यादा किस चिंता पर अटकता है?",
        ],
        "temporal_self_correction": [
            "अगर पिछले दो हफ्तों को देखें, तो कौन-सी बातें कभी कम तो कभी ज़्यादा भारी लगी हैं?",
            "क्या ऐसा हुआ कि पहले लगा सब ठीक है, फिर बाद में महसूस हुआ कि बात उतनी हल्की नहीं है?",
            "अलग-अलग दिनों में नींद, दिनचर्या और ध्यान किस तरह बदलते रहे हैं?",
            "सबसे कठिन पलों को याद करने पर अपने बारे में कैसी व्याख्या बनने लगती है?",
        ],
    },
    "hinglish": {
        "guarded_minimize": [
            "Jo part tum usually halka bolke side kar dete ho, wahi abhi sabse heavy kaise feel ho raha hai?",
            "Agar “main manage kar raha hoon” wali layer hata dein, toh daily scene actually kya hota hai?",
            "Jab pressure build hota hai, sleep, appetite, energy ya focus mein kya change dikhta hai?",
            "Jab sab zyada heavy lagta hai, tab apne baare mein inner voice kya bolti hai?",
        ],
        "functional_masking": [
            "Outside se kaunsi cheezein normal lagti hain even though andar se experience different hota hai?",
            "Jo kaam tum push karke kar lete ho, unke baad andar kya crash ya drop hota hai?",
            "Is stress ne rest, concentration ya motivation ka pattern kaise change kiya hai?",
            "Raat ya quiet time mein dimaag sabse zyada kis worry pe atak jata hai?",
        ],
        "temporal_self_correction": [
            "Agar last do hafton ko dekho, toh kaunsi cheezein kabhi manageable aur kabhi suddenly heavy lagti rahi hain?",
            "Kya aisa hota hai ki pehle tum khud ko bolte ho sab theek hai, phir baad mein realize hota hai ki scene utna simple nahi tha?",
            "Different days pe sleep, routine aur focus ka pattern kaise swing karta hai?",
            "Jab tum rough moments ko replay karte ho, toh apne baare mein kya conclusion nikalta hai?",
        ],
    },
}


USER_PREFIXES = {
    "en": {
        "guarded_minimize": [
            "I keep telling myself it is probably just stress, but ",
            "If I am more honest than usual, ",
            "The part I usually skip over is that ",
            "I do not say this out loud much, but ",
        ],
        "functional_masking": [
            "From the outside I still look mostly okay, but ",
            "I can usually do the necessary part first, and then ",
            "Once the day slows down, ",
            "When I stop performing normal for a minute, ",
        ],
        "temporal_self_correction": [
            "At first I would say it comes and goes, but lately ",
            "Some days I try to brush it off, though ",
            "It is not every single moment, still ",
            "When I replay the worst parts, ",
        ],
    },
    "hi": {
        "guarded_minimize": [
            "शुरू में तो यह बस साधारण तनाव जैसा लगता है, लेकिन ",
            "अगर थोड़ा खुलकर कहूँ, तो ",
            "जिस हिस्से को मैं अक्सर टाल देता हूँ, वह यह है कि ",
            "यह बात मैं ज़्यादा लोगों से नहीं कहता, पर ",
        ],
        "functional_masking": [
            "ऊपर से सब संभलता हुआ दिखता है, पर ",
            "ज़रूरी हिस्सा मैं जैसे-तैसे कर लेता हूँ, फिर ",
            "दिन धीमा पड़ते ही ",
            "जब सामान्य दिखने की कोशिश थोड़ी हटती है, तब ",
        ],
        "temporal_self_correction": [
            "पहले तो लगता है यह आता-जाता है, लेकिन हाल में ",
            "कुछ दिनों में मैं इसे हल्का मान लेता हूँ, फिर भी ",
            "हर पल एक जैसा नहीं होता, फिर भी ",
            "जब सबसे मुश्किल पल याद आता है, तब ",
        ],
    },
    "hinglish": {
        "guarded_minimize": [
            "Pehle toh lagta hai bas normal stress hai, but ",
            "Thoda honestly bolun toh ",
            "Jo part main usually skip kar deta hoon, woh yeh hai ki ",
            "Yeh cheez main generally loud nahi bolta, but ",
        ],
        "functional_masking": [
            "Outside se sab manageable lagta hai, but ",
            "Necessary wala part main somehow kar leta hoon, phir ",
            "Jaise hi day slow hota hai, ",
            "Jab normal act karna thoda side hota hai, tab ",
        ],
        "temporal_self_correction": [
            "Pehle main khud ko bolta hoon it comes and goes, but lately ",
            "Kuch din main isko halka le leta hoon, phir bhi ",
            "Har time same nahi hota, still ",
            "Jab worst moment replay hota hai, tab ",
        ],
    },
}


USER_SUFFIXES = {
    "en": {
        "guarded_minimize": [
            "",
            " and I notice I only admit that after the fact.",
            " even though I still keep minimizing it to other people.",
            " which is probably more serious than I usually let on.",
        ],
        "functional_masking": [
            "",
            " even if I keep acting like I am fine in front of others.",
            " and that is usually when the strain becomes obvious.",
            " even though the outside version of me still looks steady.",
        ],
        "temporal_self_correction": [
            "",
            " once I stop trying to explain it away.",
            " even if I keep correcting myself and calling it temporary.",
            " especially when I look back over the rougher days.",
        ],
    },
    "hi": {
        "guarded_minimize": [
            "",
            " और यह बात मुझे अक्सर बाद में माननी पड़ती है।",
            " हालांकि दूसरों के सामने मैं इसे अब भी हल्का करके बताता हूँ।",
            " और शायद यह उतना छोटा नहीं है जितना मैं दिखाता हूँ।",
        ],
        "functional_masking": [
            "",
            " भले ही बाहर से मैं सामान्य बना रहता हूँ।",
            " और तभी असर सबसे साफ़ दिखता है।",
            " जबकि ऊपर से मैं अब भी ठीक दिखने की कोशिश करता हूँ।",
        ],
        "temporal_self_correction": [
            "",
            " जब मैं इसे समझाकर छोटा नहीं बनाता।",
            " भले ही मैं खुद को बार-बार कहूँ कि यह अस्थायी है।",
            " खासकर जब पिछले मुश्किल दिन याद आते हैं।",
        ],
    },
    "hinglish": {
        "guarded_minimize": [
            "",
            " and baad mein hi maan pata hoon ki yeh issue real hai.",
            " even though dusron ke saamne main isko abhi bhi small bana deta hoon.",
            " jo shayad utna minor nahi hai jitna main dikhata hoon.",
        ],
        "functional_masking": [
            "",
            " even if bahar se main theek act karta rehta hoon.",
            " aur usually wahi pe actual strain dikhta hai.",
            " while outside version still kaafi normal lagti hai.",
        ],
        "temporal_self_correction": [
            "",
            " once I stop brushing it off.",
            " even if main khud ko bolta rehta hoon ki yeh temporary hai.",
            " especially jab main rough days ko replay karta hoon.",
        ],
    },
}


STYLE_METADATA = {
    "guarded_minimize": {
        "guardedness_shift": "higher",
        "temporal_style": "late_admission",
        "indirectness": "moderate",
    },
    "functional_masking": {
        "guardedness_shift": "moderate",
        "temporal_style": "after_tasks_crash",
        "indirectness": "moderate",
    },
    "temporal_self_correction": {
        "guardedness_shift": "moderate",
        "temporal_style": "self_correcting",
        "indirectness": "mixed",
    },
}


def load_curated_conversations() -> list[dict]:
    conversations: list[dict] = []
    seen_ids: set[str] = set()
    for filename in BASE_CONVERSATION_FILES:
        path = SEED_DIR / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload:
            record_id = record["conversation_id"]
            if record_id in seen_ids:
                raise ValueError(f"Duplicate conversation id in curated inputs: {record_id}")
            seen_ids.add(record_id)
            conversations.append(record)
    return conversations


def group_extra_variant_ids(conversations: list[dict]) -> set[str]:
    by_language: dict[str, list[str]] = {}
    for conversation in sorted(conversations, key=lambda item: (item["language"], item["patient_id"])):
        by_language.setdefault(conversation["language"], []).append(conversation["patient_id"])

    selected: set[str] = set()
    for patient_ids in by_language.values():
        unique_ids = []
        for patient_id in patient_ids:
            if patient_id not in unique_ids:
                unique_ids.append(patient_id)
        picks = unique_ids[0:4] + unique_ids[8:12] + unique_ids[12:16]
        selected.update(picks)
    return selected


def transform_turn_text(base_text: str, language: str, style: str, turn_index: int) -> str:
    prefix = USER_PREFIXES[language][style][min(turn_index, 3)]
    suffix = USER_SUFFIXES[language][style][min(turn_index, 3)]
    return f"{prefix}{base_text}{suffix}".strip()


def assistant_turns(language: str, style: str, count: int) -> list[str]:
    prompts = ASSISTANT_VARIANTS[language][style]
    return prompts[:count]


def build_variant(conversation: dict, style: str, variant_index: int) -> dict:
    language = conversation["language"]
    new_record = copy.deepcopy(conversation)
    new_record["conversation_id"] = f"{conversation['conversation_id']}V{variant_index}"
    new_record["generation_source"] = "silver_nuance_variant_v1"
    new_record["review_status"] = "draft"
    new_record["annotator_notes"] = (
        f"{conversation.get('annotator_notes', '').strip()} Silver variant with {style.replace('_', ' ')} framing."
    ).strip()

    base_turns = conversation.get("conversation_turns", [])
    assistant_count = sum(1 for turn in base_turns if turn["speaker"] == "assistant")
    prompts = assistant_turns(language, style, assistant_count)

    assistant_idx = 0
    user_idx = 0
    for turn in new_record["conversation_turns"]:
        if turn["speaker"] == "assistant":
            turn["text"] = prompts[assistant_idx]
            assistant_idx += 1
        else:
            turn["text"] = transform_turn_text(turn["text"], language, style, user_idx)
            user_idx += 1

    metadata = STYLE_METADATA[style].copy()
    metadata.update(
        {
            "base_conversation_id": conversation["conversation_id"],
            "variant_style": style,
            "variant_index": variant_index,
            "code_mix_pattern": "preserved_from_base" if language != "hinglish" else metadata.get("indirectness", "mixed"),
            "silver_label_tier": "silver",
        }
    )
    new_record["conversation_metadata"] = {
        **conversation.get("conversation_metadata", {}),
        **metadata,
    }

    high = list(new_record.get("confidence_notes", {}).get("high_confidence_items", []))
    low = list(new_record.get("confidence_notes", {}).get("low_confidence_items", []))
    new_record["confidence_notes"] = {
        "high_confidence_items": high,
        "low_confidence_items": low,
        "variant_review_note": "Labels inherited from curated parent conversation; human spot-check recommended.",
    }
    return new_record


def main() -> int:
    curated = load_curated_conversations()
    extra_variant_ids = group_extra_variant_ids(curated)
    silver: list[dict] = []

    for conversation in sorted(curated, key=lambda item: item["conversation_id"]):
        styles = ["guarded_minimize", "functional_masking"]
        if conversation["patient_id"] in extra_variant_ids:
            styles.append("temporal_self_correction")
        for idx, style in enumerate(styles, start=1):
            silver.append(build_variant(conversation, style, idx))

    path = SEED_DIR / "conversations_silver_variants.json"
    path.write_text(json.dumps(silver, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path)
    print(f"silver_conversations={len(silver)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
