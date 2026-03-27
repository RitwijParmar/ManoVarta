from typing import Dict, Optional, Tuple

from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import ChatSession, CoveragePlan, ScreeningSnapshot


OPENING_PROMPTS = {
    "en": "Thanks for being here. Over the last couple of weeks, what has felt the heaviest lately?",
    "hi": "Shukriya, aap yahan aaye. Pichhle do hafton mein sabse zyada kya bhaari laga?",
    "hinglish": "Thanks for joining. Pichhle do hafton mein sabse zyada kya heavy laga?",
}

SAFETY_MESSAGES = {
    "en": "I’m concerned by what you just shared. I’m pausing the screening flow and marking this for urgent human review.",
    "hi": "Aapne jo share kiya usse turant chinta ho rahi hai. Main normal screening rok kar isse urgent human review ke liye mark kar raha hoon.",
    "hinglish": "Jo aapne share kiya usse concern ho raha hai. Main normal screening pause karke ise urgent human review ke liye mark kar raha hoon.",
}

CLOSING_MESSAGES = {
    "en": "I have enough detail for a structured summary now. I can still ask one more follow-up if you want to clarify anything.",
    "hi": "Mere paas ab structured summary ke liye kaafi detail hai. Agar aap chahein to ek aur follow-up le sakte hain.",
    "hinglish": "Ab mere paas structured summary ke liye enough detail hai. Agar aap chaho to ek aur follow-up le sakte hain.",
}

FOLLOW_UPS: Dict[str, Dict[str, str]] = {
    "phq_q1_anhedonia": {
        "en": "Have the things you usually enjoy felt less interesting lately, or is it more about energy?",
        "hi": "Jo cheezein pehle theek lagti thi, kya unmein ab dil kam lagta hai, ya zyada problem energy ki hai?",
        "hinglish": "Jo cheezein pehle achhi lagti thi, kya unmein ab mann kam lagta hai, ya issue zyada energy ka hai?",
    },
    "phq_q2_low_mood": {
        "en": "Has your mood itself been low, empty, or heavy on most days, or is it mostly stress?",
        "hi": "Kya aapka mood khud neecha ya udaas raha hai, ya zyada baat stress ki hai?",
        "hinglish": "Kya mood khud low raha hai, ya zyada matter stress ka hai?",
    },
    "phq_q3_sleep": {
        "en": "How has sleep been lately: trouble falling asleep, waking up often, or sleeping too much?",
        "hi": "Neend kaisi rahi: neend aane mein dikkat, baar baar uthna, ya zyada sona?",
        "hinglish": "Sleep kaisi rahi: sone mein dikkat, baar baar uthna, ya zyada sleep?",
    },
    "phq_q4_fatigue": {
        "en": "Are you feeling physically drained most days, even when the day is not that demanding?",
        "hi": "Kya zyada din aise lagte hain jab sharir se hi thakan rehti hai, chahe kaam itna heavy na ho?",
        "hinglish": "Kya most days body level pe drained feel hota hai, even when day itna heavy na ho?",
    },
    "phq_q5_appetite": {
        "en": "Have your appetite or eating patterns changed in a noticeable way?",
        "hi": "Kya bhook ya khane ka pattern noticeably badla hai?",
        "hinglish": "Kya appetite ya khane ka pattern noticeable way mein change hua hai?",
    },
    "phq_q6_worthlessness": {
        "en": "Have you been feeling like a burden, blaming yourself too much, or feeling not good enough?",
        "hi": "Kya aapko bojh jaisa, khud ko zyada blame karne wala, ya khud ko kam samajhne wala ehsaas hua hai?",
        "hinglish": "Kya aisa feel hua ki aap burden ho, ya aap khud ko zyada blame karte ho?",
    },
    "phq_q7_concentration": {
        "en": "When you try to study or work, is focus breaking more than usual?",
        "hi": "Jab padhne ya kaam karne baithte hain, kya dhyan pehle se zyada toot raha hai?",
        "hinglish": "Jab study ya work karte ho, kya focus pehle se zyada break ho raha hai?",
    },
    "phq_q8_psychomotor": {
        "en": "Have you felt unusually slowed down, or the opposite, so restless that it is hard to sit still?",
        "hi": "Kya aap apne aap ko ya to bahut dheema mehsoos karte hain, ya itna bechain ki ek jagah tikna mushkil ho?",
        "hinglish": "Kya aap ya to unusually slow feel karte ho, ya itne restless ki baithna mushkil ho?",
    },
    "phq_q9_self_harm": {
        "en": "I want to check carefully: have thoughts of hurting yourself or not wanting to be alive shown up at all?",
        "hi": "Main dhyan se poochna chahta hoon: kya khud ko nuksan pahunchane ya zinda na rehne ke khayal aaye hain?",
        "hinglish": "Main carefully poochna chahta hoon: kya khud ko hurt karne ya zinda na rehne wale thoughts aaye hain?",
    },
    "gad_q1_nervous": {
        "en": "Do you feel on edge or keyed up even when there is no immediate reason?",
        "hi": "Kya bina turant wajah ke bhi andar se ghabrahat ya tanav bana rehta hai?",
        "hinglish": "Kya bina immediate reason ke bhi on edge ya ghabrahat feel hoti rehti hai?",
    },
    "gad_q2_control_worry": {
        "en": "When worry starts, does it feel hard to stop or slow it down?",
        "hi": "Jab fikr shuru hoti hai, kya use rokna ya dheema karna mushkil lagta hai?",
        "hinglish": "Jab worry start hoti hai, kya usse stop ya slow karna mushkil lagta hai?",
    },
    "gad_q3_excessive_worry": {
        "en": "Is the worry usually about one issue, or does it spread across many things?",
        "hi": "Kya chinta zyada tar ek baat tak simit hoti hai, ya bahut si cheezon tak phail jati hai?",
        "hinglish": "Kya worry ek issue tak rehti hai, ya bahut si cheezon tak spread ho jati hai?",
    },
    "gad_q4_trouble_relaxing": {
        "en": "Have you been able to relax at all, or does your body stay tense most of the time?",
        "hi": "Kya aap relax kar pa rahe hain, ya sharir aksar tanav mein hi rehta hai?",
        "hinglish": "Kya aap relax kar pa rahe ho, ya body mostly tense rehti hai?",
    },
    "gad_q5_restlessness": {
        "en": "Do you get so restless that sitting still becomes hard?",
        "hi": "Kya bechaini itni hoti hai ki ek jagah baithna mushkil ho jata hai?",
        "hinglish": "Kya restlessness itni ho jati hai ki ek jagah baithna mushkil ho jata hai?",
    },
    "gad_q6_irritability": {
        "en": "Have small things been making you unusually irritable or snappy?",
        "hi": "Kya choti choti baatein pehle se zyada chidchida bana rahi hain?",
        "hinglish": "Kya choti choti baatein aapko pehle se zyada irritable bana rahi hain?",
    },
    "gad_q7_fear_awful": {
        "en": "Do you often feel as if something bad is about to happen, even when you cannot explain why?",
        "hi": "Kya aksar aisa lagta hai ki kuch bura hone wala hai, chahe wajah clear na ho?",
        "hinglish": "Kya aksar aisa lagta hai ki kuch bura hone wala hai, even when reason clear na ho?",
    },
}


class DialoguePlanner:
    def opening_prompt(self, language: str) -> str:
        return OPENING_PROMPTS[language]

    def next_reply(self, snapshot: ScreeningSnapshot, session: ChatSession) -> Tuple[str, Optional[str]]:
        language = session.language
        snapshot.coverage = self.build_plan(snapshot, session)
        if snapshot.safety.level == "urgent":
            return SAFETY_MESSAGES[language], None

        for item in snapshot.coverage.next_items:
            if item in FOLLOW_UPS:
                return FOLLOW_UPS[item][language], item

        return CLOSING_MESSAGES[language], None

    def build_plan(self, snapshot: ScreeningSnapshot, session: ChatSession) -> CoveragePlan:
        scored = snapshot.items
        unresolved = [
            item_id
            for item_id, item in scored.items()
            if item.status in {"unresolved", "partial", "contradicted", "abstained"}
        ]
        unresolved = [item_id for item_id in unresolved if not self._hold_back_sensitive_item(item_id, snapshot, session)]
        unresolved.sort(
            key=lambda item_id: (
                item_id in session.asked_items,
                scored[item_id].status == "unresolved",
                -ITEM_INDEX[item_id].priority,
                scored[item_id].confidence,
            )
        )
        return snapshot.coverage.model_copy(
            update={
                "next_items": unresolved[:5],
                "review_items": [
                    item_id for item_id, item in scored.items() if item.review_recommended or item.status in {"contradicted", "abstained"}
                ],
                "review_required": snapshot.safety.needs_human_review
                or any(item.review_recommended or item.status in {"contradicted", "abstained"} for item in scored.values()),
            }
        )

    def _hold_back_sensitive_item(self, item_id: str, snapshot: ScreeningSnapshot, session: ChatSession) -> bool:
        if item_id != "phq_q9_self_harm":
            return False
        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        if snapshot.safety.level in {"review", "urgent"}:
            return False
        mood_signal = any(
            snapshot.items[key].value and snapshot.items[key].value >= 2
            for key in ("phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness")
        )
        return len(user_turns) < 3 and not mood_signal
