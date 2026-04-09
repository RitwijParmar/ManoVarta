from manovarta_core.dialogue import ANXIETY_LOOP_BREAK_PROMPTS, ANXIETY_LOOP_CLOSE_PROMPTS, FINAL_HOLD_MESSAGES, FINAL_HOLD_VARIANTS, POST_CLOSE_CHOOSER_MESSAGES, DialoguePlanner
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


def test_first_turn_uses_specific_reflection_instead_of_generic_prefix():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="specific-reflection-first-turn",
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
    reply, _ = planner.next_reply(snapshot, session)

    assert reply.startswith("It sounds like things that usually matter to you are feeling flatter right now.")


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


def test_hinglish_worry_domain_detail_beats_old_relaxation_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-domain-over-relaxation",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Jab worry start hoti hai, kya aap mind ko usse hata paate ho, ya rokne ki koshish ke baad bhi woh loop hoti rehti hai?", language_tag="hinglish"),
            Turn(turn_id=2, speaker="user", text="Mostly work aur future ko lekar hota hai.", language_tag="hinglish"),
        ],
        asked_items=["gad_q4_trouble_relaxing", "gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q3_excessive_worry"
    assert asked_item == "gad_q3_excessive_worry"
    assert "spread" in reply.lower() or "one main" in reply.lower()


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


def test_hindi_frequency_answer_uses_sleep_frequency_variant():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-sleep-frequency-followup",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="हफ़्ते में चार-पाँच दिन हो जाता है।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    prompt = planner._build_prompt_for_target("hi", snapshot.coverage.dialogue, session)

    assert snapshot.coverage.dialogue.target_item == "phq_q3_sleep"
    assert prompt is not None
    assert "यह कितनी बार होता है" in prompt
    assert "उन रातों में" in prompt
    assert "नींद बनाए रखने" in prompt or "नींद शुरू" in prompt


def test_single_bad_day_hindi_statement_is_not_mistaken_for_frequency():
    planner = DialoguePlanner()
    normalized = planner._normalize("आप जैसे मेरा दिन अच्छा नहीं रहा तो आज मुझे यह सब काफी ज्यादा लग रहा था")

    assert planner._has_frequency_answer(normalized) is False
    assert planner._has_timing_or_frequency_answer(normalized) is False


def test_energy_frequency_answer_uses_fatigue_frequency_variant():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="energy-frequency-followup",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When the energy drops, is it more like your body feels heavy, your mind feels slow to get going, or both?",
                language_tag="en",
            ),
            Turn(turn_id=2, speaker="user", text="About four days a week.", language_tag="en"),
        ],
        asked_items=["phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    prompt = planner._build_prompt_for_target("en", snapshot.coverage.dialogue, session)

    assert snapshot.coverage.dialogue.target_item == "phq_q4_fatigue"
    assert prompt is not None
    assert "how often it happens" in prompt
    assert "body heaviness" in prompt or "slow-starting mind" in prompt


def test_hindi_anxiety_progression_moves_from_control_to_worry_content():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-anxiety-content-progression",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="जब चिंता शुरू होती है, क्या आप दिमाग को उससे हटा पाते हैं, या रोकने की कोशिश के बाद भी वह चलती रहती है?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="करती है आज तो काफी ज्यादा चले", language_tag="hi"),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q3_excessive_worry"
    assert asked_item == "gad_q3_excessive_worry"
    assert "काम" in reply or "परिवार" in reply or "भविष्य" in reply


def test_hindi_sleep_flavored_anxiety_reply_prefers_relaxation_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-anxiety-sleep-branch",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="जब चिंता शुरू होती है, क्या आप दिमाग को उससे हटा पाते हैं, या रोकने की कोशिश के बाद भी वह चलती रहती है?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="हां लग रहा है खास करके नींद ना आना", language_tag="hi"),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item in {"gad_q4_trouble_relaxing", "phq_q3_sleep"}
    assert asked_item in {"gad_q4_trouble_relaxing", "phq_q3_sleep"}
    assert (
        "दिमाग को शांत" in reply
        or "शरीर को ढीला" in reply
        or "नींद" in reply
    )


def test_repeated_anxiety_loop_break_closes_instead_of_repeating():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-anxiety-loop-close",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_BREAK_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="रात में लगता है", language_tag="hi"),
        ],
        asked_items=[
            "gad_q4_trouble_relaxing",
            "gad_q2_control_worry",
            "gad_q4_trouble_relaxing",
            "gad_q3_excessive_worry",
            "gad_q3_excessive_worry",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply.startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक")


def test_english_persistent_worry_after_core_rotation_uses_break_prompt():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-anxiety-core-break",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?",
                language_tag="en",
            ),
            Turn(turn_id=2, speaker="user", text="It keeps going no matter how much I try.", language_tag="en"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == ANXIETY_LOOP_BREAK_PROMPTS["en"]


def test_english_close_prompt_followed_by_nonpriority_reply_stays_on_final_hold():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-close-holds",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["en"], language_tag="en"),
            Turn(turn_id=2, speaker="user", text="No not like that.", language_tag="en"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == POST_CLOSE_CHOOSER_MESSAGES["en"]


def test_hinglish_close_prompt_followed_by_nonpriority_reply_stays_on_final_hold():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-close-holds",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hinglish"], language_tag="hinglish"),
            Turn(turn_id=2, speaker="user", text="Nahi aisa kuch nahi.", language_tag="hinglish"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == POST_CLOSE_CHOOSER_MESSAGES["hinglish"]


def test_continuity_note_is_not_reused_after_it_already_appeared():
    planner = DialoguePlanner()
    continuity = "अगर यह आपकी हाल की चिंता बातचीत से मिलता-जुलता लग रहा है, तो बताइए क्या वैसा रहा और क्या बदला।"
    session = ChatSession(
        session_id="continuity-once",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=continuity, language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="दोनों दोनों समस्याएं हैं", language_tag="hi"),
        ],
    )
    plan = DialoguePlan(
        stage="exploration",
        current_topic="anxiety",
        target_topic="anxiety",
        target_item="gad_q4_trouble_relaxing",
        user_turns=3,
        continuity_note=continuity,
        user_style=UserStyleProfile(empathy_level="high", steering_preference="balanced"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._compose_prompt(
        "hi",
        "जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल दिमाग को शांत करना होता है, शरीर को ढीला करना, या दोनों?",
        plan,
        session,
    )

    assert continuity not in prompt


def test_close_prompt_followed_by_short_reply_does_not_reopen_anxiety_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="close-does-not-reopen",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="दोनों साथ में", language_tag="hi"),
        ],
        asked_items=[
            "gad_q4_trouble_relaxing",
            "gad_q2_control_worry",
            "gad_q4_trouble_relaxing",
            "gad_q3_excessive_worry",
            "gad_q3_excessive_worry",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == POST_CLOSE_CHOOSER_MESSAGES["hi"]


def test_post_close_nonexpansive_followup_uses_chooser_message():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-post-close-chooser",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["en"], language_tag="en"),
            Turn(turn_id=2, speaker="user", text="No not like that.", language_tag="en"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == POST_CLOSE_CHOOSER_MESSAGES["en"]


def test_post_close_clear_sleep_signal_reopens_specific_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-post-close-reopen-sleep",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["en"], language_tag="en"),
            Turn(turn_id=2, speaker="user", text="The main thing still missing is that my sleep is broken almost every night now.", language_tag="en"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "sleep"
    assert asked_item == "phq_q3_sleep"
    assert reply != FINAL_HOLD_MESSAGES["en"]


def test_structured_summary_acknowledgement_does_not_reopen_with_new_question():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="close-ack-does-not-reopen",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="हां पूछ लो", language_tag="hi"),
        ],
        asked_items=[
            "gad_q4_trouble_relaxing",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply in FINAL_HOLD_VARIANTS["hi"]


def test_break_prompt_followed_by_family_scoped_answer_closes_instead_of_reopening():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="break-family-scope-closes",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_BREAK_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="केवल मां की बात को लेकर", language_tag="hi"),
        ],
        asked_items=[
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == ANXIETY_LOOP_CLOSE_PROMPTS["hi"]


def test_close_prompt_followed_by_long_garbled_followup_stays_on_final_hold():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="close-garbled-followup-holds",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="कमर्शियल मिल जा रही हो तक रहती है", language_tag="hi"),
        ],
        asked_items=[
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply in FINAL_HOLD_VARIANTS["hi"]


def test_relax_duration_answer_triggers_break_prompt_before_reopening():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="relax-duration-break",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल दिमाग को शांत करना होता है, शरीर को ढीला करना, या दोनों?",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="लंबे समय तक अटका रहता है", language_tag="hi"),
        ],
        asked_items=[
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == ANXIETY_LOOP_BREAK_PROMPTS["hi"]


def test_loop_break_is_skipped_when_user_adds_specific_worry_domain_detail():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="break-skipped-on-domain-detail",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="जब यह चलती रहती है, क्या चिंता कई बातों के बीच घूमती रहती है, या ज़्यादातर समय एक ही मुख्य बात पर अटकी रहती है?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="मैं जैसे यह कल रात में मुझे काफी ज्यादा लग रहा था जब मैं परेशान था काम को लेकर के", language_tag="hi"),
        ],
        asked_items=[
            "gad_q4_trouble_relaxing",
            "gad_q2_control_worry",
            "gad_q4_trouble_relaxing",
            "gad_q3_excessive_worry",
            "gad_q3_excessive_worry",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q4_trouble_relaxing"
    assert asked_item == "gad_q4_trouble_relaxing"
    assert "दिमाग को शांत" in reply or "शरीर को ढीला" in reply or "दोनों" in reply


def test_scope_answer_after_worry_spread_question_closes_anxiety_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scope-answer-closes-branch",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब चिंता चलती रहती है, क्या यह ज़्यादा काम, परिवार, पैसों या भविष्य जैसी कई बातों में फैल जाती है, या आम तौर पर किसी एक मुख्य बात पर अटकती है?",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="कई बातों में फैल जाती है", language_tag="hi"),
        ],
        asked_items=["gad_q4_trouble_relaxing", "gad_q2_control_worry", "gad_q3_excessive_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply.startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक")


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


def test_hindi_heavy_burden_opening_prefers_self_view_branch():
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

    assert coverage.dialogue.target_topic == "self_view"
    assert asked_item == "phq_q6_worthlessness"
    assert "चिंता शुरू होती है" not in reply


def test_anhedonia_semantic_answer_advances_past_repeat_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="anhedonia-advance",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="When you try to do things you usually care about, does the interest drop before you start, or do you go through with them but feel very little from them?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Things I used to enjoy feel flat, and even when I do them I mostly go through the motions now.", language_tag="en"),
        ],
        asked_items=["phq_q1_anhedonia"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "phq_q2_low_mood"
    assert asked_item == "phq_q2_low_mood"
    assert "interest drop before you start" not in reply


def test_anhedonia_detail_after_low_mood_does_not_bounce_back_to_same_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="anhedonia-no-bounce-back",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="When this hits, does it sit more like sadness or heaviness through the day, or does it come in waves around certain times?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Even when I do them, I do not get much from them and I mostly go through the motions now.", language_tag="en"),
        ],
        asked_items=["phq_q1_anhedonia", "phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "phq_q2_low_mood"
    assert asked_item == "phq_q2_low_mood"
    assert "interest drop before you start" not in reply
    assert "steady heavy mood" in reply.lower() or "emotional numbness" in reply.lower()


def test_low_mood_repeat_probe_deepens_on_next_turn():
    session = ChatSession(session_id="session-low-mood-repeat", language="en")
    planner = DialoguePlanner()
    scorer = ConversationScorer()

    for text in [
        "I have been feeling numb and disconnected lately.",
        "Things I used to enjoy feel flat.",
        "Even when I do them, I do not get much from them.",
    ]:
        user_turn = Turn(turn_id=len(session.turns) + 1, speaker="user", text=text, language_tag="en")
        session.turns.append(user_turn)
        snapshot = scorer.analyze(session.turns, "en", SafetyFlag(level="none"))
        reply, asked_item = planner.next_reply(snapshot, session)
        assistant_turn = Turn(
            turn_id=len(session.turns) + 1,
            speaker="assistant",
            text=reply,
            language_tag="en",
        )
        session.turns.append(assistant_turn)
        if asked_item:
            session.asked_items.append(asked_item)

    user_turn = Turn(
        turn_id=len(session.turns) + 1,
        speaker="user",
        text="I mostly go through the motions now.",
        language_tag="en",
    )
    session.turns.append(user_turn)
    snapshot = scorer.analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)
    plan = snapshot.coverage.dialogue

    assert plan.target_item == "phq_q2_low_mood"
    assert asked_item == "phq_q2_low_mood"
    assert "steady heavy mood" not in reply.lower()
    assert "small moments still cut through" in reply.lower() or "go through the motions" in reply.lower()


def test_english_low_energy_slow_start_stays_on_focus_or_energy_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-focus-energy-guard",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="Lately I sleep late, feel heavy in the morning, and it is harder to focus at work.",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="assistant",
                text="When this hits, does it sit more like sadness or heaviness through the day, or does it come in waves around certain times?",
                language_tag="en",
            ),
            Turn(
                turn_id=3,
                speaker="user",
                text="Mostly in the mornings and after lunch. It happens around four days a week.",
                language_tag="en",
            ),
            Turn(
                turn_id=4,
                speaker="assistant",
                text="When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?",
                language_tag="en",
            ),
            Turn(
                turn_id=5,
                speaker="user",
                text="It feels like low energy plus my mind taking longer to get started.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q2_low_mood", "phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"focus", "energy"}
    assert asked_item in {"phq_q7_concentration", "phq_q4_fatigue"}
    assert "worry starts" not in reply.lower()
    assert "looping even when you try to stop it" not in reply.lower()


def test_hinglish_low_energy_slow_start_stays_on_focus_or_energy_branch():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-focus-energy-guard",
        language="hinglish",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="Lately meri sleep late ho rahi hai, subah heavy feel hota hai, aur kaam par focus karna harder ho gaya hai.",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=2,
                speaker="assistant",
                text="Jab yeh feel hota hai, kya yeh zyada poore din ki sadness ya heaviness jaisa rehta hai, ya kuch specific times par waves mein aata hai?",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=3,
                speaker="user",
                text="Yeh mostly subah aur lunch ke baad zyada hota hai. Week mein around chaar din hota hai.",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=4,
                speaker="assistant",
                text="Jab aap work ya study par baithte ho, kya zyada aisa hota hai ki attention baar baar slip ho jata hai, ya same line par wapas aate rehte ho lekin woh stick nahi karti?",
                language_tag="hinglish",
            ),
            Turn(
                turn_id=5,
                speaker="user",
                text="Lagta low energy bhi hai aur mind ko start hone mein time lagta hai.",
                language_tag="hinglish",
            ),
        ],
        asked_items=["phq_q2_low_mood", "phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"focus", "energy"}
    assert asked_item in {"phq_q7_concentration", "phq_q4_fatigue"}
    assert "worry start hoti hai" not in reply.lower()
    assert "loop hoti rehti hai" not in reply.lower()


def test_anxiety_body_tension_signal_pivots_from_control_worry_to_relaxation():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="anxiety-to-relaxation",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When the worry starts, can you pull your mind away from it, or does it keep looping even when you try to stop it?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="It loops for hours and I stay tense in my body too.",
                language_tag="en",
            ),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q4_trouble_relaxing"
    assert asked_item == "gad_q4_trouble_relaxing"
    assert "quiet your thoughts" in reply.lower() or "relax your body" in reply.lower()
