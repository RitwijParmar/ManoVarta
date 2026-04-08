from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import ChatSession, DialoguePlan, DisclosureMetrics, SafetyFlag, Turn, UserStyleProfile


def test_dialogue_planner_prioritizes_appetite_in_energy_topic_when_unresolved():
    planner = DialoguePlanner()
    snapshot = ConversationScorer().analyze([], "en", SafetyFlag(level="none"))
    session = ChatSession(session_id="session-1", language="en")

    target_item = planner._select_target_item(snapshot, session, "energy", [], "low", UserStyleProfile())

    assert target_item == "phq_q5_appetite"


def test_dialogue_planner_prioritizes_control_worry_in_anxiety_topic_when_unresolved():
    planner = DialoguePlanner()
    snapshot = ConversationScorer().analyze([], "en", SafetyFlag(level="none"))
    session = ChatSession(session_id="session-2", language="en")

    target_item = planner._select_target_item(snapshot, session, "anxiety", [], "low", UserStyleProfile())

    assert target_item == "gad_q2_control_worry"


def test_compose_prompt_hides_continuity_note_during_rapport():
    planner = DialoguePlanner()
    plan = DialoguePlan(
        stage="rapport",
        current_topic="sleep",
        target_topic="sleep",
        user_turns=1,
        continuity_note="अगर यह आपकी हाल की नींद बातचीत से मिलता-जुलता लग रहा है, तो बताइए क्या वैसा रहा और क्या बदला।",
        reflective_anchor="लगता है नींद पर असर साफ़ दिख रहा है।",
        user_style=UserStyleProfile(empathy_level="high"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._compose_prompt("hi", "क्या यह ज़्यादा उदासी, लगातार चिंता, नींद की दिक्कत, या इनका मिश्रण लग रहा है?", plan)

    assert "हाल की नींद बातचीत" not in prompt
    assert "लगता है नींद पर असर" not in prompt
    assert "क्या यह ज़्यादा उदासी" in prompt


def test_compose_prompt_uses_only_one_support_line_after_rapport():
    planner = DialoguePlanner()
    plan = DialoguePlan(
        stage="clarification",
        current_topic="sleep",
        target_topic="sleep",
        user_turns=3,
        continuity_note="अगर यह आपकी हाल की नींद बातचीत से मिलता-जुलता लग रहा है, तो बताइए क्या वैसा रहा और क्या बदला।",
        reflective_anchor="लगता है नींद पर असर साफ़ दिख रहा है।",
        user_style=UserStyleProfile(empathy_level="high", steering_preference="balanced"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._compose_prompt("hi", "जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है या बार-बार उठने में?", plan)

    assert "हाल की नींद बातचीत" in prompt
    assert "लगता है नींद पर असर साफ़ दिख रहा है।" not in prompt


def test_compose_prompt_prefers_support_line_over_extra_empathy_after_rapport():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="support-line-over-prefix",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="It has been happening almost every day and I cannot focus properly.", language_tag="en"),
        ],
    )
    plan = DialoguePlan(
        stage="clarification",
        current_topic="focus",
        target_topic="focus",
        user_turns=3,
        reflective_anchor="It sounds like this is getting in the way of staying with tasks.",
        user_style=UserStyleProfile(empathy_level="high"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._compose_prompt(
        "en",
        "When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?",
        plan,
        session,
    )

    assert not prompt.startswith("That sounds hard.")
    assert prompt.startswith("When you try to work or study")


def test_compose_prompt_drops_repeated_same_topic_scaffold():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="repeat-scaffold",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="That sounds really hard, and I appreciate you saying it clearly. It sounds like the worry is staying active even when things are quiet. When the worry starts, can you pull your mind away from it, or does it keep looping even when you try to stop it?",
                language_tag="en",
            ),
            Turn(turn_id=2, speaker="user", text="About four days a week.", language_tag="en"),
        ],
    )
    plan = DialoguePlan(
        stage="clarification",
        current_topic="anxiety",
        target_topic="anxiety",
        user_turns=2,
        reflective_anchor="It sounds like the worry is staying active even when things are quiet.",
        user_style=UserStyleProfile(empathy_level="high"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._compose_prompt(
        "en",
        "When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?",
        plan,
        session,
    )

    assert not prompt.startswith("That sounds really hard")
    assert "It sounds like the worry is staying active" not in prompt
    assert prompt.startswith("When you try to settle down")


def test_english_mood_opening_prefers_mood_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-mood-open",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="I have been feeling low and disconnected from things I usually enjoy.",
                language_tag="en",
            )
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "mood"
    assert asked_item in {"phq_q1_anhedonia", "phq_q2_low_mood"}
    assert "worry starts" not in reply.lower()


def test_substantive_first_turn_gets_targeted_followup():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="first-turn-steering",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="I have been feeling restless lately and it gets worse during the night.",
                language_tag="en",
            )
        ],
    )
    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item in {"gad_q5_restlessness", "gad_q4_trouble_relaxing"}
    assert "mix of those" not in reply.lower()
    assert "settle down" in reply.lower() or "sit still" in reply.lower()


def test_mood_followup_can_pivot_to_focus_without_drifting_to_anxiety():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="mood-to-focus-steering",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="पिछले दो हफ़्तों से मन बहुत भारी रहता है और कई बार लगता है कि मैं सबके लिए बोझ हूँ।",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="assistant",
                text="जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?",
                language_tag="hi",
            ),
            Turn(
                turn_id=3,
                speaker="user",
                text="काम पर ध्यान नहीं टिकता और किसी चीज़ में मन नहीं लगता।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"mood", "focus"}
    assert asked_item in {"phq_q1_anhedonia", "phq_q7_concentration"}
    assert "चिंता शुरू" not in reply


def test_hinglish_tense_body_signal_stays_on_relaxation_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-tense-body",
        language="hinglish",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="Pichhle do hafte se mind bahut overloaded lag raha hai aur raat ko switch off nahi hota.",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=2,
                speaker="assistant",
                text="Jab aap settle hone ki koshish karte ho, kya zyada mushkil thoughts ko quiet karna hota hai, body relax karna, ya dono?",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=3,
                speaker="user",
                text="Phir body bhi tense lagti hai aur neend disturb ho jaati hai.",
                language_tag="hinglish",
            ),
        ],
        asked_items=["gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)

    assert coverage.dialogue.target_topic in {"anxiety", "sleep"}
    assert coverage.dialogue.target_item in {"gad_q4_trouble_relaxing", "phq_q3_sleep"}


def test_repeat_relaxation_probe_uses_fresh_variant_for_recent_repeat():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="repeat-relaxation-variant",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Jab aap settle hone ki koshish karte ho, kya zyada mushkil thoughts ko quiet karna hota hai, body relax karna, ya dono?", language_tag="hinglish"),
            Turn(turn_id=2, speaker="user", text="Mostly jab kaam khatam hota hai tab start hota hai.", language_tag="hinglish"),
            Turn(turn_id=3, speaker="assistant", text="Lag raha hai worry tab bhi active rehti hai jab bahar sab quiet ho. Jab worry start hoti hai, kya aap mind ko usse hata paate ho, ya rokne ki koshish ke baad bhi woh loop hoti rehti hai?", language_tag="hinglish"),
            Turn(turn_id=4, speaker="user", text="Phir body bhi tense lagti hai aur neend disturb ho jaati hai.", language_tag="hinglish"),
        ],
        asked_items=["gad_q4_trouble_relaxing", "gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    prompt = planner._build_prompt_for_target("hinglish", coverage.dialogue, session)

    assert coverage.dialogue.target_item == "gad_q4_trouble_relaxing"
    assert prompt is not None
    assert "body relax karna, ya dono?" not in prompt
    assert "tension kaafi der tak atka rehta hai" in prompt


def test_hindi_timing_answer_uses_sleep_specific_variant():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-sleep-followup",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="ज़्यादातर रात में।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    prompt = planner._build_prompt_for_target("hi", snapshot.coverage.dialogue, session)

    assert snapshot.coverage.dialogue.target_item == "phq_q3_sleep"
    assert prompt is not None
    assert "समय-सूचना मददगार" in prompt
    assert "नींद बनाए रखने" in prompt or "नींद आने" in prompt


def test_target_topic_aligns_with_directed_followup_item():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="topic-item-alignment",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="पिछले कुछ दिनों से रात में नींद टूट जाती है और सुबह ध्यान नहीं लगता।", language_tag="hi"),
            Turn(turn_id=2, speaker="assistant", text="जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="लगभग चार दिन हफ़्ते में।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)

    assert coverage.dialogue.target_item == "phq_q3_sleep"
    assert coverage.dialogue.target_topic == "sleep"


def test_hindi_heavy_burden_opening_prefers_mood_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-mood-open",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="पिछले दो हफ़्तों से मन बहुत भारी रहता है और कई बार लगता है कि मैं सबके लिए बोझ हूँ।",
                language_tag="hi",
            )
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "mood"
    assert asked_item in {"phq_q1_anhedonia", "phq_q2_low_mood"}
    assert "चिंता शुरू होती है" not in reply
