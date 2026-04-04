from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, Optional, Tuple

from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import (
    ChatSession,
    CoveragePlan,
    DialoguePlan,
    DisclosureMetrics,
    ScreeningSnapshot,
    TopicState,
    UserStyleProfile,
)


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

RAPPORT_PROMPTS = {
    "en": "Thanks for sharing that. Has it been feeling more like low mood, constant worry, poor sleep, or a mix of those?",
    "hi": "Yeh share karne ke liye shukriya. Kya yeh zyada udaasi, lagataar chinta, neend ki dikkat, ya inka mix lag raha hai?",
    "hinglish": "Yeh share karne ke liye thanks. Kya yeh zyada low mood, constant worry, sleep issue, ya in sab ka mix lag raha hai?",
}

REFLECTION_PREFIXES = {
    "en": {
        "moderate": "Thanks for explaining that.",
        "high": "That sounds really hard, and I appreciate you saying it clearly.",
    },
    "hi": {
        "moderate": "Yeh batane ke liye shukriya.",
        "high": "Yeh kaafi mushkil lag raha hai, aur aapne ise itni saaf tarah bataya uske liye shukriya.",
    },
    "hinglish": {
        "moderate": "Yeh share karne ke liye thanks.",
        "high": "Yeh kaafi hard lag raha hai, aur aapne itni clearly bataya uske liye thanks.",
    },
}

SOFTENING_SUFFIXES = {
    "en": "Whichever part feels easier to answer is okay.",
    "hi": "Jo hissa answer karna aasaan lage, usse shuru karna theek hai.",
    "hinglish": "Jo part answer karna easier lage, usse start karna bilkul fine hai.",
}

BRIEF_DETAIL_SUFFIXES = {
    "en": "One recent example or one timing detail is enough.",
    "hi": "Ek recent example ya ek timing detail bhi kaafi hai.",
    "hinglish": "Ek recent example ya ek timing detail bhi enough hai.",
}

OPEN_STORY_SUFFIXES = {
    "en": "You can answer in your own words and stay with the part that feels most important.",
    "hi": "Aap apne shabdon mein jawab de sakte hain aur jo hissa sabse important lage us par tik sakte hain.",
    "hinglish": "Aap apne words mein jawab de sakte ho aur jo part sabse important lage us par reh sakte ho.",
}

SAFETY_SHORT_ANSWER_SUFFIXES = {
    "en": "A short direct answer is okay here.",
    "hi": "Yahan ek chhota seedha jawab bhi theek hai.",
    "hinglish": "Yahan short direct answer bhi bilkul theek hai.",
}

TOPIC_PROMPTS: Dict[str, Dict[str, str]] = {
    "mood": {
        "en": "That sounds heavy. On most days, has it felt more like low mood itself, or more like losing interest in things you usually enjoy?",
        "hi": "Yeh kaafi bhaari lag raha hai. Zyada dinon mein yeh zyada neecha mood jaisa lagta hai, ya pehle jo cheezein achhi lagti thi unmein dil kam lagta hai?",
        "hinglish": "Yeh kaafi heavy lag raha hai. Most days yeh zyada low mood jaisa lagta hai, ya pehle jo cheezein achhi lagti thi unmein mann kam lagta hai?",
    },
    "sleep": {
        "en": "That sounds draining. Has sleep mostly been hard to start, hard to stay asleep, or are you sleeping more than usual?",
        "hi": "Yeh thaka dene wala lag raha hai. Neend mein zyada dikkat sone ki shuruat mein hai, beech beech mein uthne mein, ya zarurat se zyada neend aa rahi hai?",
        "hinglish": "Yeh kaafi draining lag raha hai. Sleep issue zyada sone ki shuruat mein hai, beech beech mein uthne mein, ya usual se zyada sleep ho rahi hai?",
    },
    "energy": {
        "en": "I want to understand the day-to-day impact a bit better. Is it more like low energy through the day, changes in appetite, or both?",
        "hi": "Main roz ke impact ko thoda better samajhna chahta hoon. Kya baat zyada din bhar ki thakan ki hai, bhook ke badlav ki, ya dono ki?",
        "hinglish": "Main day-to-day impact thoda better samajhna chahta hoon. Kya issue zyada low energy ka hai, appetite change ka, ya dono ka?",
    },
    "self_view": {
        "en": "When things feel this heavy, do you also end up blaming yourself or feeling like a burden?",
        "hi": "Jab cheezein itni bhaari lagti hain, kya aap khud ko zyada blame karne lagte hain ya bojh jaisa mehsoos hota hai?",
        "hinglish": "Jab cheezein itni heavy lagti hain, kya aap khud ko zyada blame karte ho ya burden jaisa feel hota hai?",
    },
    "focus": {
        "en": "When you try to study or work, is it more that your focus keeps breaking, or that your body feels slowed down or restless?",
        "hi": "Jab aap padhne ya kaam karne baithte hain, kya zyada dikkat dhyan tootne ki hoti hai, ya sharir dheema ya bechain lagta hai?",
        "hinglish": "Jab aap study ya work karte ho, kya zyada issue focus break hone ka hota hai, ya body slow ya restless lagti hai?",
    },
    "anxiety": {
        "en": "Does this feel more like constant worry in your mind, tension in your body, or both at the same time?",
        "hi": "Kya yeh zyada dimaag ki lagataar chinta jaisa lagta hai, sharir ke tanav jaisa, ya dono saath mein?",
        "hinglish": "Kya yeh zyada constant worry in the mind jaisa lagta hai, body tension jaisa, ya dono ek saath?",
    },
    "safety": {
        "en": "I want to check carefully because your safety matters. Have thoughts of hurting yourself or not wanting to be alive shown up at all?",
        "hi": "Main dhyan se poochna chahta hoon kyunki aapki safety zaruri hai. Kya khud ko nuksan pahunchane ya zinda na rehne ke khayal aaye hain?",
        "hinglish": "Main carefully poochna chahta hoon kyunki aapki safety matter karti hai. Kya khud ko hurt karne ya zinda na rehne wale thoughts aaye hain?",
    },
}


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
    def opening_prompt(self, language: str) -> str:
        return OPENING_PROMPTS[language]

    def next_reply(self, snapshot: ScreeningSnapshot, session: ChatSession) -> Tuple[str, Optional[str]]:
        snapshot.coverage = self.build_plan(snapshot, session)
        plan = snapshot.coverage.dialogue
        language = session.language

        if snapshot.safety.level == "urgent" or plan.next_action == "handoff":
            return SAFETY_MESSAGES[language], plan.target_item
        if plan.next_action == "summarize":
            return CLOSING_MESSAGES[language], None
        if plan.stage == "rapport":
            return self._compose_prompt(language, RAPPORT_PROMPTS[language], plan), plan.target_item

        prompt = TOPIC_PROMPTS.get(plan.target_topic, {}).get(language)
        if prompt:
            return self._compose_prompt(language, prompt, plan), plan.target_item
        return CLOSING_MESSAGES[language], None

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
        stage = self._select_stage(snapshot, topic_states, len(user_turns), held_back_items)
        target_topic = self._select_target_topic(snapshot, topic_states, current_topic, stage, held_back_items)
        target_item = self._select_target_item(snapshot, session, target_topic, held_back_items)
        next_items = self._rank_next_items(snapshot, session, target_topic, held_back_items)
        review_items = [
            item_id
            for item_id, item in snapshot.items.items()
            if item.review_recommended or item.status in {"contradicted", "abstained"}
        ]
        dialogue = DialoguePlan(
            stage=stage,
            next_action=self._select_action(stage, target_topic),
            current_topic=current_topic,
            target_topic=target_topic,
            target_item=target_item,
            rationale=self._build_rationale(snapshot, target_topic, topic_states, held_back_items),
            user_turns=len(user_turns),
            low_confidence_topics=low_confidence_topics,
            covered_topics=covered_topics,
            held_back_items=held_back_items,
            transition_hint=self._build_transition_hint(current_topic, target_topic, stage, user_style),
            user_style=user_style,
            disclosure=disclosure,
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

        word_counts = [len(turn.text.split()) for turn in user_turns]
        avg_words = round(mean(word_counts), 1) if word_counts else 0.0
        if avg_words < 9:
            verbosity = "brief"
        elif avg_words < 20:
            verbosity = "balanced"
        else:
            verbosity = "detailed"

        if session.language == "hinglish":
            code_mix = "high"
        elif any(any(marker in turn.text.lower() for marker in ("yaar", "nahi", "haan", "bahut", "mann")) for turn in user_turns):
            code_mix = "medium"
        else:
            code_mix = "low"

        touched_ratio = snapshot.coverage.touched_items / max(len(user_turns), 1)
        if avg_words < 8 and touched_ratio < 1.0:
            openness = "guarded"
        elif avg_words < 14 or any(topic.status == "review" for topic in topic_states):
            openness = "cautious"
        else:
            openness = "open"

        distress_trend = self._distress_trend(snapshot, session)
        empathy_level = "high" if openness != "open" or distress_trend == "rising" or snapshot.safety.level != "none" else "moderate"
        return UserStyleProfile(
            avg_words_per_turn=avg_words,
            verbosity=verbosity,
            openness=openness,
            code_mix=code_mix,
            distress_trend=distress_trend,
            empathy_level=empathy_level,
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
        )

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
    ) -> str:
        if snapshot.safety.level == "urgent":
            return "safety"
        if snapshot.safety.level == "review" and "phq_q9_self_harm" not in held_back_items:
            return "safety"
        if user_turn_count <= 1 and snapshot.coverage.touched_items < 3:
            return "rapport"
        if any(topic.status in {"review", "probing"} for topic in topic_states if topic.topic_id != "safety"):
            return "clarification"
        stable_topics = [topic for topic in topic_states if topic.status == "stable" and topic.topic_id != "safety"]
        if snapshot.coverage.completion_ratio >= 0.65 or len(stable_topics) >= 4:
            return "summary"
        return "exploration"

    def _select_target_topic(
        self,
        snapshot: ScreeningSnapshot,
        topic_states: list[TopicState],
        current_topic: str,
        stage: str,
        held_back_items: list[str],
    ) -> str:
        if stage == "safety":
            return "safety"
        if stage == "summary":
            return current_topic if current_topic in TOPIC_GRAPH else "mood"

        held_back = set(held_back_items)
        candidates = [
            topic
            for topic in topic_states
            if topic.unresolved_items or topic.review_items
        ]
        if not candidates:
            return current_topic if current_topic in TOPIC_GRAPH else "mood"

        def rank(topic: TopicState) -> tuple[int, float]:
            score = topic.priority * 10
            if topic.status == "review":
                score += 20
            elif topic.status == "probing":
                score += 14
            else:
                score += 8
            if topic.touched:
                score += 8
            if topic.topic_id == current_topic:
                score += 4
            if current_topic in TOPIC_GRAPH and topic.topic_id in TOPIC_GRAPH[current_topic].transitions:
                score += 3
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
    ) -> Optional[str]:
        if target_topic not in TOPIC_GRAPH:
            return None

        held_back = set(held_back_items)
        ranked = sorted(
            (
                item_id
                for item_id in TOPIC_GRAPH[target_topic].item_ids
                if item_id not in held_back and snapshot.items[item_id].status != "resolved"
            ),
            key=lambda item_id: (
                item_id in session.asked_items,
                snapshot.items[item_id].status == "unresolved",
                -ITEM_INDEX[item_id].priority,
                snapshot.items[item_id].confidence,
            ),
        )
        return ranked[0] if ranked else None

    def _rank_next_items(
        self,
        snapshot: ScreeningSnapshot,
        session: ChatSession,
        target_topic: str,
        held_back_items: list[str],
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
                item_id in session.asked_items,
                snapshot.items[item_id].status == "unresolved",
                -ITEM_INDEX[item_id].priority,
                snapshot.items[item_id].confidence,
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

    def _select_action(self, stage: str, target_topic: str) -> str:
        if stage == "safety":
            return "risk_check" if target_topic == "safety" else "handoff"
        if stage == "summary":
            return "summarize"
        if stage == "rapport":
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
    ) -> str:
        if stage == "rapport":
            return "Acknowledge the opening concern, then narrow gently into the first likely symptom area."
        if stage == "summary":
            return "Reflect briefly, then summarize instead of opening a new branch."
        if current_topic == target_topic:
            return f"Stay with {target_topic} and stabilize confidence before moving on."
        if user_style.openness == "guarded":
            return f"Use a gentle bridge from {current_topic} to {target_topic} and offer an easier choice-based answer."
        return f"Bridge naturally from {current_topic} to {target_topic} by connecting the last symptom to its daily impact."

    def _held_back_items(self, snapshot: ScreeningSnapshot, session: ChatSession) -> list[str]:
        held_back: list[str] = []
        if self._hold_back_sensitive_item("phq_q9_self_harm", snapshot, session):
            held_back.append("phq_q9_self_harm")
        return held_back

    def _hold_back_sensitive_item(self, item_id: str, snapshot: ScreeningSnapshot, session: ChatSession) -> bool:
        if item_id != "phq_q9_self_harm":
            return False

        user_turns = [turn for turn in session.turns if turn.speaker == "user"]
        if snapshot.safety.level == "urgent":
            return False
        if snapshot.safety.level == "review" and self._has_explicit_safety_signal(snapshot):
            return False
        mood_signal = any(
            snapshot.items[key].value is not None and snapshot.items[key].value >= 2
            for key in ("phq_q1_anhedonia", "phq_q2_low_mood", "phq_q6_worthlessness")
        )
        return len(user_turns) < 3 and not mood_signal

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

    def _compose_prompt(self, language: str, base_prompt: str, plan: DialoguePlan) -> str:
        prefix = REFLECTION_PREFIXES[language][plan.user_style.empathy_level]
        suffix = self._style_suffix(language, plan)
        if suffix:
            return f"{prefix} {base_prompt} {suffix}"
        return f"{prefix} {base_prompt}"

    def _style_suffix(self, language: str, plan: DialoguePlan) -> str:
        if plan.next_action == "risk_check" or plan.target_topic == "safety":
            return SAFETY_SHORT_ANSWER_SUFFIXES[language]
        if plan.user_style.openness == "guarded":
            return SOFTENING_SUFFIXES[language]
        if plan.user_style.verbosity == "brief":
            return BRIEF_DETAIL_SUFFIXES[language]
        if plan.user_style.verbosity == "detailed":
            return OPEN_STORY_SUFFIXES[language]
        return ""

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
