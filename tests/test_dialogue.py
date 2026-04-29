from manovarta_core.dialogue import ANXIETY_LOOP_BREAK_PROMPTS, ANXIETY_LOOP_CLOSE_PROMPTS, FINAL_HOLD_MESSAGES, FINAL_HOLD_VARIANTS, FINAL_REST_MESSAGES, POST_CLOSE_CHOOSER_MESSAGES, POST_CLOSE_IDLE_MESSAGES, SCENE_PROMPTS, DialoguePlanner
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import ChatSession, DialoguePlan, DisclosureMetrics, SafetyFlag, Turn, UserStyleProfile


def test_hindi_sleep_opening_registers_sleep_and_energy_signals():
    planner = DialoguePlanner()
    normalized = planner._normalize("नींद बिगड़ गई है, देर से नींद आती है और सुबह उठकर शरीर टूटा सा लगता है")

    assert planner._has_sleep_pattern_answer(normalized) is True
    assert planner._has_sleep_impact_signal(normalized) is True
    assert planner._has_activation_signal(normalized) is True


def test_hinglish_sleep_opening_registers_sleep_and_energy_signals():
    planner = DialoguePlanner()
    normalized = planner._normalize("Sleep ka pattern off hai, late soti hoon aur din bhar drained rehti hoon.")

    assert planner._has_sleep_pattern_answer(normalized) is True
    assert planner._has_sleep_impact_signal(normalized) is True
    assert planner._has_activation_signal(normalized) is True


def test_hindi_ghabrahat_downplay_does_not_count_as_worry_domain():
    planner = DialoguePlanner()
    normalized = planner._normalize("घबराहट जैसा नहीं है, ज्यादा उदासी और खालीपन है, काम शुरू करने का मन नहीं करता")

    assert planner._has_anxiety_downplay_signal(normalized) is True
    assert planner._has_non_anxiety_salient_signal(normalized) is True
    assert planner._has_worry_domain_signal(normalized) is False


def test_explicit_anxious_opening_counts_as_anxiety_signal():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="explicit-anxious-opening",
        language="en",
        turns=[Turn(turn_id=1, speaker="user", text="Hi I am feeling very anxious today", language_tag="en")],
    )

    assert "anxiety" in planner._latest_signal_topics(session)
    assert "gad_q1_nervous" in planner._latest_signal_items(session)


def test_hindi_ghabrahat_downplay_with_no_desire_to_start_work_counts_as_non_anxiety_signal():
    planner = DialoguePlanner()
    normalized = planner._normalize("घबराहट जैसा नहीं है, ज़्यादा ऐसा है कि कोई काम शुरू करने का मन नहीं करता।")

    assert planner._has_anxiety_downplay_signal(normalized) is True
    assert planner._has_anhedonia_signal(normalized) is True
    assert planner._has_non_anxiety_salient_signal(normalized) is True


def test_hindi_marker_matching_still_works_when_sentence_ends_with_danda():
    planner = DialoguePlanner()
    normalized = planner._normalize("कोई काम शुरू करने का मन नहीं करता।")

    assert planner._has_anhedonia_signal(normalized) is True


def test_english_not_really_panic_exactly_with_delay_and_guilt_counts_as_non_anxiety_signal():
    planner = DialoguePlanner()
    normalized = planner._normalize("It's not really panic exactly. More like I delay starting things and then feel guilty.")

    assert planner._has_anxiety_downplay_signal(normalized) is True
    assert planner._has_anhedonia_signal(normalized) is True
    assert planner._has_self_view_signal(normalized) is True
    assert planner._has_non_anxiety_salient_signal(normalized) is True


def test_sleep_functioning_scene_prefers_psychomotor_when_fresh_signal_appears():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="sleep-scene-psychomotor",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="Sleep has been off and food is weird too.", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Some days the whole body feels dragged and moves feel slowed.", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q5_appetite"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))

    target_item = planner._select_scene_target_item(
        snapshot,
        session,
        "sleep_functioning",
        "energy",
        [],
        "low",
        UserStyleProfile(),
    )

    assert target_item in {"phq_q4_fatigue", "phq_q7_concentration", "phq_q8_psychomotor"}
    assert target_item != "phq_q5_appetite"


def test_sleep_functioning_summary_request_rotates_away_from_recent_repeat():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="sleep-scene-summary-rotate",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="नींद बिगड़ गई है और दिन भर थकान रहती है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="भूख भी गड़बड़ है।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="अभी तक की तस्वीर का छोटा सा सार बता सकते हो?", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q5_appetite", "phq_q6_worthlessness", "phq_q5_appetite"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))

    target_item = planner._select_scene_target_item(
        snapshot,
        session,
        "sleep_functioning",
        "energy",
        [],
        "low",
        UserStyleProfile(),
    )

    assert target_item in {"phq_q4_fatigue", "phq_q7_concentration", "phq_q8_psychomotor", "phq_q3_sleep"}
    assert target_item != "phq_q5_appetite"


def test_breadth_request_marks_repeated_sleep_functioning_scene_as_exhausted_without_fresh_signal():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="breadth-scene-exhausted",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="what else do you still need to know?", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration"],
    )
    normalized = planner._normalize("what else do you still need to know?")

    exhausted = planner._breadth_request_exhausted_topics(session, normalized, set(), set())

    assert {"sleep", "energy", "focus"}.issubset(exhausted)


def test_summary_request_rotates_away_from_exhausted_sleep_functioning_scene():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="summary-breadth-rotate-scene",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="Sleep has been broken and I wake up worn out.", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="By afternoon I drag through things and meals get delayed.", language_tag="en"),
            Turn(turn_id=3, speaker="user", text="Focus slips too and I reread the same lines.", language_tag="en"),
            Turn(turn_id=4, speaker="user", text="What else do you still need to know before you summarize?", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.target_scene != "sleep_functioning"
    assert plan.target_topic not in {"sleep", "energy", "focus"}


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


def test_recommend_nudges_prefers_low_pressure_choice_for_brief_guarded_user():
    planner = DialoguePlanner()
    session = ChatSession(session_id="session-2b", language="en")

    nudges = planner._recommend_nudges(
        session,
        "anxiety",
        UserStyleProfile(verbosity="brief", openness="guarded", steering_preference="guided"),
        "exploration",
        "low",
    )

    assert "choice" in nudges
    assert any(key in nudges for key in {"scale", "example", "body"})


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


def test_hindi_merged_opening_fragments_keep_sleep_as_the_first_follow_up():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-merged-opening",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="फिर से स्वागत है। अगर यह आपकी हाल की चिंता बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="नींद का पैटर्न बदल गया है। नींद काफी देर से आती है, कुछ दिनों से कम आती है, और किसी काम में मन नहीं लगता है।",
                language_tag="hi",
            ),
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "sleep"
    assert asked_item == "phq_q3_sleep"
    assert "नींद बिगड़ती है" in reply


def test_hindi_present_vs_future_sadness_answer_moves_forward_without_repeating_low_mood_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-present-vs-future-sadness",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="फिर से स्वागत है। अगर यह आपकी हाल की चिंता बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="नीम का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए", language_tag="hi"),
            Turn(
                turn_id=3,
                speaker="assistant",
                text="लगता है इसका असर नींद पर साफ़ पड़ रहा है। जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?",
                language_tag="hi",
            ),
            Turn(turn_id=4, speaker="user", text="यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है", language_tag="hi"),
            Turn(
                turn_id=5,
                speaker="assistant",
                text="लगता है दिन अपने-आप में ही भारी लग रहे हैं। जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?",
                language_tag="hi",
            ),
            Turn(
                turn_id=6,
                speaker="user",
                text="मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q3_sleep", "phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_scene == "mood_selfview"
    assert coverage.dialogue.target_item is None
    assert asked_item is None
    assert "दिन भर की उदासी" not in reply
    assert "सपाट या भारी एहसास" not in reply
    assert "सबसे आगे क्या महसूस होता है" in reply


def test_hindi_no_interest_rephrase_after_low_mood_prompt_does_not_repeat_same_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-no-interest-reroute",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="फिर से स्वागत है। अगर यह आपकी हाल की चिंता बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="नींद का पैटर्न बदल गया है और किसी काम में मन नहीं लगता है।", language_tag="hi"),
            Turn(
                turn_id=3,
                speaker="assistant",
                text="लगता है दिन अपने-आप में ही भारी लग रहे हैं। जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?",
                language_tag="hi",
            ),
            Turn(
                turn_id=4,
                speaker="user",
                text="मां पहले से ही है जाता है कोई काम करने की इच्छा करती ही नहीं है",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item in {"phq_q6_worthlessness", "phq_q7_concentration", "phq_q5_appetite"}
    assert "दिन भर की उदासी" not in reply
    assert "कुछ खास समय पर लहरों में" not in reply


def test_positive_future_thought_line_is_not_treated_as_worry_domain():
    planner = DialoguePlanner()
    normalized = planner._normalize(
        "मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है"
    )

    assert planner._has_low_mood_signal(normalized) is True
    assert planner._has_worry_domain_signal(normalized) is False


def test_vartamaan_line_does_not_false_trigger_sleep_topic_from_raat_substring():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-vartamaan-no-false-sleep",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है",
                language_tag="hi",
            ),
        ],
    )

    assert planner._latest_signal_topics(session) == {"mood"}
    assert planner._latest_signal_items(session) == {"phq_q2_low_mood"}


def test_noisy_hindi_transcript_avoids_repeating_mood_probe_and_future_anxiety_detour():
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    session = ChatSession(
        session_id="noisy-hindi-repeat-trace",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="फिर से स्वागत है। अगर यह आपकी हाल की चिंता बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।",
                language_tag="hi",
            ),
            Turn(turn_id=2, speaker="user", text="नीम का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="नींद का पैटर्न बदल गया काफी देर से जाता हूं काम में मन नहीं लगता", language_tag="hi"),
        ],
    )

    first_snapshot = scorer.analyze(session.turns, "hi", SafetyFlag(level="none"))
    first_reply, first_item = planner.next_reply(first_snapshot, session)
    session.turns.append(Turn(turn_id=5, speaker="assistant", text=first_reply, language_tag="hi"))
    session.asked_items.append(first_item)
    session.turns.append(
        Turn(
            turn_id=6,
            speaker="user",
            text="मां पहले से ही है जाता है कोई काम करने की इच्छा करती ही नहीं है",
            language_tag="hi",
        )
    )

    second_snapshot = scorer.analyze(session.turns, "hi", SafetyFlag(level="none"))
    second_reply, second_item = planner.next_reply(second_snapshot, session)
    session.turns.append(Turn(turn_id=7, speaker="assistant", text=second_reply, language_tag="hi"))
    if second_item is not None:
        session.asked_items.append(second_item)
    session.turns.append(
        Turn(
            turn_id=8,
            speaker="user",
            text="मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है",
            language_tag="hi",
        )
    )

    third_snapshot = scorer.analyze(session.turns, "hi", SafetyFlag(level="none"))
    third_reply, third_item = planner.next_reply(third_snapshot, session)

    assert first_item == "phq_q2_low_mood"
    assert second_item in {"phq_q6_worthlessness", "phq_q7_concentration", "phq_q5_appetite"}
    assert "दिन भर की उदासी" not in second_reply
    assert third_item in {"phq_q6_worthlessness", "phq_q7_concentration", "phq_q5_appetite", "phq_q1_anhedonia"}
    assert "काम या जिम्मेदारियों" not in third_reply
    assert "भविष्य जैसी कई बातों" not in third_reply


def test_hindi_attention_answer_does_not_repeat_focus_probe_again():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-focus-repeat-stop",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="खराब नींद या थके हुए दिनों के बाद सबसे पहले क्या प्रभावित होता है: शुरू होने की ताकत, भूख, एक काम पर टिकना, या चाल-ढाल/रफ्तार का धीमा या बेचैन हो जाना?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="भूख भी कम हो जाती है और ध्यान भी टिकता नहीं", language_tag="hi"),
        ],
        asked_items=["phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item != "phq_q7_concentration"
    assert "ध्यान बार-बार भटक जाता है" not in reply


def test_english_focus_followup_yields_to_new_sleep_energy_detail():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="en-focus-yields-to-energy",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="Sleep has been patchy and by afternoon I feel heavy and slow.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"sleep", "energy"}
    assert asked_item != "phq_q7_concentration"
    assert "attention slips away" not in reply.lower()


def test_exhausted_energy_topic_rotates_to_focus_instead_of_generic_energy_repeat():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="en-energy-scene-rotation",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="It sounds like the day is taking more effort than it used to. When the energy drops, is it more like your body feels heavy, your mind feels slow to get going, or both?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="I also lose track of hunger cues and meals get delayed.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q4_fatigue", "phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_scene == "sleep_functioning"
    assert asked_item == "phq_q7_concentration"
    assert "changes in appetite, or both" not in reply


def test_hindi_appetite_and_focus_detail_rotates_off_repeated_fatigue_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-fatigue-rotation",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="लगता है जो चीज़ें पहले मायने रखती थीं, उनमें अभी मन कम लग रहा है। जब थकान या ऊर्जा की कमी बढ़ती है, क्या ज़्यादा ऐसा लगता है कि शरीर भारी पड़ रहा है, दिमाग शुरू होने में धीमा है, या दोनों?",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="भूख भी थोड़ी गड़बड़ है और काम पर ध्यान टूटता है।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_scene == "sleep_functioning"
    assert asked_item == "phq_q8_psychomotor"
    assert "थकान की है, भूख के बदलाव की, या दोनों" not in reply


def test_under_the_weather_opening_uses_physical_clarifier_not_anxiety():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="under-weather",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="I am feeling a little under the weather today.",
                language_tag="en",
            ),
        ],
    )
    session.profile.recent_checkins = [
        {"topic": "anxiety", "language": "en", "summary": "Recent anxiety check-in."}
    ]

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "mood"
    assert coverage.dialogue.continuity_note == ""
    assert asked_item is None
    assert reply == "When you say you are a little under the weather, does it feel more physical, more emotional, or a mix of both today?"


def test_build_plan_enters_scene_closure_mode_when_late_session_is_undercovered():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scene-closure-plan",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="Sleep has been broken for the last couple of weeks and I keep waking around 3 or 4 am.", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="By the afternoon my body feels heavy and my mind is slow to get going again.", language_tag="en"),
            Turn(turn_id=3, speaker="user", text="I still get work done but everything feels flat underneath.", language_tag="en"),
            Turn(turn_id=4, speaker="user", text="The worry is mostly about work and whether I will mess up my future.", language_tag="en"),
            Turn(turn_id=5, speaker="user", text="I can keep going if easier, but the thoughts still loop in the background.", language_tag="en"),
        ],
        asked_items=[
            "phq_q3_sleep",
            "phq_q4_fatigue",
            "phq_q1_anhedonia",
            "gad_q3_excessive_worry",
            "gad_q2_control_worry",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.stage == "clarification"
    assert plan.closure_mode is True
    assert plan.target_item in {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing", "gad_q5_restlessness", "gad_q6_irritability", "gad_q7_afraid"}
    assert plan.target_scene in {None, "worry_shape", "worry_activation"}


def test_build_prompt_for_target_prefers_scene_prompt_when_closure_mode_is_active():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scene-prompt",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Thanks for being here. Over the last couple of weeks, what has felt the heaviest lately?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Sleep has been broken and getting through the day takes a lot more effort now.", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue"],
    )
    plan = DialoguePlan(
        stage="clarification",
        current_topic="energy",
        target_topic="energy",
        target_item="phq_q5_appetite",
        target_scene="sleep_functioning",
        scene_item_ids=["phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"],
        closure_mode=True,
        user_turns=5,
        user_style=UserStyleProfile(empathy_level="high"),
        disclosure=DisclosureMetrics(),
    )

    prompt = planner._build_prompt_for_target("en", plan, session)

    assert prompt == SCENE_PROMPTS["sleep_functioning"]["en"]


def test_summary_request_keeps_scene_closure_mode_off():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scene-summary-request",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="पिछले दो हफ्तों से नींद टूटती रहती है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="दिन में आलस रहता है और काम शुरू होने में समय लगता है।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="चिंता नौकरी और भविष्य को लेकर रहती है।", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="बस अब जो समझ आया है उसका सार बता दीजिए।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "gad_q3_excessive_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.stage in {"clarification", "exploration"}
    assert plan.closure_mode is True
    assert plan.target_scene is not None


def test_hindi_summary_request_with_saar_chahiye_enters_summary():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scene-summary-saar-chahiye",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="पिछले दो हफ्तों से नींद टूटती रहती है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="दिन में आलस रहता है और काम शुरू होने में समय लगता है।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="चिंता नौकरी और भविष्य को लेकर रहती है।", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="अभी तक का सार चाहिए।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "gad_q3_excessive_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.stage in {"clarification", "exploration"}
    assert plan.closure_mode is True
    assert plan.target_scene is not None


def test_hindi_summary_request_with_abhi_saar_de_sakte_hain_enters_summary():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="scene-summary-abhi-saar",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="नींद कम आती है और काम में मन नहीं लगता।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="उदासी भी रहती है और ध्यान भी टिकता नहीं।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="अभी सार दे सकते हैं।", language_tag="hi"),
        ],
        asked_items=["phq_q2_low_mood", "phq_q7_concentration"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.stage in {"clarification", "exploration"}
    assert plan.closure_mode is True
    assert plan.target_scene is not None


def test_summary_request_stays_in_closeout_until_phq_gad_queues_are_closed():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="summary-needs-closeout",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="Sleep has been broken for a couple of weeks and I keep waking around 4 am.", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="By afternoon my body feels heavy and I lose steam pretty quickly.", language_tag="en"),
            Turn(turn_id=3, speaker="user", text="Can you summarize what you have so far?", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.stage in {"clarification", "exploration"}
    assert plan.closure_mode is True
    assert plan.summary_ready is False
    assert plan.phq_queue or plan.gad_queue


def test_next_reply_does_not_close_on_summary_request_when_queues_remain_open():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="summary-question-keeps-going",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="Sleep has been broken for a couple of weeks and I keep waking around 4 am.", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="By afternoon my body feels heavy and I lose steam pretty quickly.", language_tag="en"),
            Turn(turn_id=3, speaker="user", text="Can you summarize what you have so far?", language_tag="en"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is not None
    assert reply != planner._build_working_summary(snapshot, session)
    assert "?" in reply


def test_continue_signal_with_close_the_gaps_language_enters_closure_mode():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="close-the-gaps",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="For the last two weeks I have felt anxious and low most days. I lose interest before I even start things, sleep is broken and I wake around 4 am, my energy crashes by afternoon, meals get skipped, my focus slips, my body feels slowed down, I get harsh on myself, I feel restless and irritable, and I keep worrying something bad will happen.",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="If you need to close the gaps, ask what is still missing.",
                language_tag="en",
            ),
        ],
        asked_items=["gad_q1_nervous"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    plan = planner.build_plan(snapshot, session).dialogue

    assert plan.closure_mode is True
    assert plan.summary_ready is False


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
    assert asked_item in {"phq_q1_anhedonia", "phq_q7_concentration", "phq_q8_psychomotor"}
    assert "चिंता शुरू" not in reply


def test_hindi_day_long_low_mood_answer_advances_past_repeat_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-day-long-low-mood",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="पिछले दो हफ़्तों से मन बहुत भारी रहता है।",
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
                text="नहीं यह दिन भर रहता है।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item != "phq_q2_low_mood"
    assert asked_item != "phq_q2_low_mood"
    assert "भावनात्मक सुन्नपन" not in reply


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


def test_energy_timing_answer_uses_fatigue_timing_variant():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="energy-timing-followup",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When the energy drops, is it more like your body feels heavy, your mind feels slow to get going, or both?",
                language_tag="en",
            ),
            Turn(turn_id=2, speaker="user", text="By the end of the day I feel drained too.", language_tag="en"),
        ],
        asked_items=["phq_q4_fatigue"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    prompt = planner._build_prompt_for_target("en", snapshot.coverage.dialogue, session)

    assert snapshot.coverage.dialogue.target_item == "phq_q4_fatigue"
    assert prompt is not None
    assert "that timing helps" in prompt.lower()
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
    assert reply.startswith(ANXIETY_LOOP_CLOSE_PROMPTS["hi"])


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


def test_repeated_post_close_acknowledgements_shift_to_idle_message_in_all_languages():
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    cases = [
        ("en", "okay"),
        ("hi", "ठीक है"),
        ("hinglish", "theek hai"),
    ]

    for language, acknowledgement in cases:
        session = ChatSession(
            session_id=f"post-close-idle-{language}",
            language=language,  # type: ignore[arg-type]
            turns=[
                Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS[language], language_tag=language),  # type: ignore[arg-type]
                Turn(turn_id=2, speaker="user", text=acknowledgement, language_tag=language),  # type: ignore[arg-type]
            ],
            asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
        )

        first_snapshot = scorer.analyze(session.turns, language, SafetyFlag(level="none"))  # type: ignore[arg-type]
        first_reply, first_item = planner.next_reply(first_snapshot, session)
        session.turns.append(
            Turn(
                turn_id=3,
                speaker="assistant",
                text=first_reply,
                language_tag=language,  # type: ignore[arg-type]
            )
        )
        session.turns.append(
            Turn(
                turn_id=4,
                speaker="user",
                text=acknowledgement,
                language_tag=language,  # type: ignore[arg-type]
            )
        )

        second_snapshot = scorer.analyze(session.turns, language, SafetyFlag(level="none"))  # type: ignore[arg-type]
        second_reply, second_item = planner.next_reply(second_snapshot, session)
        session.turns.append(
            Turn(
                turn_id=5,
                speaker="assistant",
                text=second_reply,
                language_tag=language,  # type: ignore[arg-type]
            )
        )
        session.turns.append(
            Turn(
                turn_id=6,
                speaker="user",
                text=acknowledgement,
                language_tag=language,  # type: ignore[arg-type]
            )
        )

        third_snapshot = scorer.analyze(session.turns, language, SafetyFlag(level="none"))  # type: ignore[arg-type]
        third_reply, third_item = planner.next_reply(third_snapshot, session)

        assert first_item is None
        assert second_item is None
        assert third_item is None
        assert first_reply in FINAL_HOLD_VARIANTS[language]
        assert second_reply == POST_CLOSE_IDLE_MESSAGES[language]
        assert third_reply == POST_CLOSE_IDLE_MESSAGES[language]


def test_recent_break_prompt_is_not_reused_again_in_same_hindi_flow():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-no-repeat-break",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_BREAK_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="एक ही बात पर अटकी रहती है", language_tag="hi"),
            Turn(
                turn_id=3,
                speaker="assistant",
                text="जब आप खुद को शांत करने की कोशिश करते हैं, क्या ज़्यादा मुश्किल दिमाग को शांत करना होता है, शरीर को ढीला करना, या दोनों?",
                language_tag="hi",
            ),
            Turn(turn_id=4, speaker="user", text="साथ में", language_tag="hi"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply.startswith(ANXIETY_LOOP_CLOSE_PROMPTS["hi"])


def test_hindi_post_close_echo_uses_short_rest_message():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-post-close-echo",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(
                turn_id=2,
                speaker="user",
                text="अब मेरे पास मुख्य पैटर्न पकड़ने लायक काफी जानकारी है यह चिंता कुछ खास समय पर बढ़ती है और तनाव वाले दिनों में ज्यादा लग सकती है अगर कोई बहुत जरूरी बात बाकी ना हो तो मैं इसे अभी कामचलाऊ सार मान सकता हूं",
                language_tag="hi",
            ),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is None
    assert reply == FINAL_REST_MESSAGES["hi"]


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


def test_hindi_post_close_continue_signal_reopens_exploration():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-post-close-continue",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="हां तो क्या जानना है आपको", language_tag="hi"),
        ],
        asked_items=[
            "phq_q1_anhedonia",
            "phq_q2_low_mood",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is not None
    assert reply not in {
        ANXIETY_LOOP_CLOSE_PROMPTS["hi"],
        POST_CLOSE_CHOOSER_MESSAGES["hi"],
        POST_CLOSE_IDLE_MESSAGES["hi"],
        FINAL_REST_MESSAGES["hi"],
        *FINAL_HOLD_VARIANTS["hi"],
    }


def test_hindi_post_close_energy_signal_reopens_with_fatigue_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-post-close-energy",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["hi"], language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="हां तुम शरीर में मुझे कोई समस्या नहीं होती है बस थोड़ा आलस लगता है", language_tag="hi"),
        ],
        asked_items=[
            "phq_q1_anhedonia",
            "phq_q2_low_mood",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item == "phq_q4_fatigue"
    assert "थकान" in reply or "ऊर्जा" in reply or "आलस" in reply


def test_english_post_close_continue_signal_reopens_exploration():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-post-close-continue",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["en"], language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Okay, what else do you want to know?", language_tag="en"),
        ],
        asked_items=[
            "phq_q1_anhedonia",
            "phq_q2_low_mood",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item is not None
    assert reply not in {
        ANXIETY_LOOP_CLOSE_PROMPTS["en"],
        POST_CLOSE_CHOOSER_MESSAGES["en"],
        POST_CLOSE_IDLE_MESSAGES["en"],
        FINAL_REST_MESSAGES["en"],
        *FINAL_HOLD_VARIANTS["en"],
    }


def test_english_post_close_energy_signal_reopens_with_fatigue_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="english-post-close-energy",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=ANXIETY_LOOP_CLOSE_PROMPTS["en"], language_tag="en"),
            Turn(turn_id=2, speaker="user", text="There is no body issue, I just feel low energy and slow to get going.", language_tag="en"),
        ],
        asked_items=[
            "phq_q1_anhedonia",
            "phq_q2_low_mood",
            "gad_q2_control_worry",
            "gad_q3_excessive_worry",
            "gad_q4_trouble_relaxing",
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert asked_item == "phq_q4_fatigue"
    assert "energy" in reply.lower() or "tired" in reply.lower() or "slow" in reply.lower()


def test_hindi_working_summary_avoids_false_mind_and_body_claim():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-working-summary",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="पिछले दो हफ़्तों से किसी काम में मन नहीं लगता और मन भारी रहता है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="यह दिन भर रहता है।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="भविष्य की नौकरी को लेकर चिंता रहती है।", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="शरीर में मुझे कोई समस्या नहीं होती, बस दिमाग शांत नहीं होता और थोड़ा आलस लगता है।", language_tag="hi"),
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    summary = planner._build_working_summary(snapshot, session)

    assert "अभी तक जो तस्वीर बन रही है" in summary
    assert "दिमाग" in summary
    assert "दिमाग और शरीर दोनों" not in summary
    assert "आलस" in summary or "ऊर्जा" in summary


def test_hindi_working_summary_prefers_anxiety_tail_over_safety_after_negated_risk():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hindi-working-summary-tail",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="user", text="रात में नींद टूटती रहती है और दिन में आलस रहता है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="जो चीज़ें पहले अच्छी लगती थीं अब उनमें बहुत कम महसूस होता है।", language_tag="hi"),
            Turn(turn_id=3, speaker="user", text="चिंता ज़्यादातर नौकरी और भविष्य को लेकर रहती है।", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="खुद को नुकसान पहुंचाने का मन नहीं है, बस दिमाग शांत नहीं होता।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "phq_q1_anhedonia", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    snapshot.coverage = planner.build_plan(snapshot, session)
    summary = planner._build_working_summary(snapshot, session)

    assert "चिंता" in summary
    assert "सुरक्षा" not in summary


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
    assert reply.startswith(ANXIETY_LOOP_CLOSE_PROMPTS["hi"])


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
    assert reply.startswith(ANXIETY_LOOP_CLOSE_PROMPTS["hi"])


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


def test_clear_sleep_pattern_answer_advances_past_repeat_sleep_probe():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="sleep-pattern-advance",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="Most nights I wake around 3 or 4 and then lie there replaying work stuff.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "phq_q3_sleep"
    assert asked_item == "phq_q3_sleep"
    assert "hard to fall asleep" not in reply.lower()
    assert "how many nights a week" in reply.lower()


def test_hindi_sleep_pattern_answer_with_replay_detail_stays_on_sleep_before_anxiety():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="sleep-before-anxiety-hi",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="अक्सर रात के तीन-चार बजे उठ जाता हूँ और फिर काम की बातें दिमाग में चलती रहती हैं।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "sleep"
    assert coverage.dialogue.target_item == "phq_q3_sleep"
    assert asked_item == "phq_q3_sleep"
    assert "चिंता" not in reply or "कितनी रातों" in reply


def test_sleep_followup_yields_to_fresh_energy_and_appetite_signal():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="sleep-to-energy-handoff",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="Roughly how many nights a week has it been happening like that?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="By midday my energy drops and I sometimes skip meals without meaning to.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q3_sleep"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "energy"
    assert asked_item in {"phq_q4_fatigue", "phq_q5_appetite"}
    assert "nights a week" not in reply.lower()


def test_anhedonia_followup_yields_to_fresh_focus_signal():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="anhedonia-to-focus-handoff",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="When you try to do things you usually care about, does the interest drop before you start, or do you go through with them but feel very little from them?",
                language_tag="en",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="When I sit down to work my focus keeps breaking and I reread the same lines.",
                language_tag="en",
            ),
        ],
        asked_items=["phq_q1_anhedonia"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "focus"
    assert asked_item in {"phq_q7_concentration", "phq_q8_psychomotor"}
    assert "interest drop before you start" not in reply.lower()


def test_appetite_probe_yields_to_fresh_hindi_anhedonia_signal():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="appetite-to-anhedonia-hi",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="जो चीज़ें पहले अच्छी लगती थीं अब शुरू करने से पहले ही मन हट जाता है।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q5_appetite"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "mood"
    assert coverage.dialogue.target_item == "phq_q2_low_mood"
    assert asked_item == "phq_q2_low_mood"
    assert "भूख" not in reply
    assert "उदासी" in reply or "भारीपन" in reply


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
    assert (
        "steady heavy mood" in reply.lower()
        or "emotional numbness" in reply.lower()
        or "going through the motions" in reply.lower()
        or "emotionally flat underneath" in reply.lower()
    )


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
    assert "small moments still cut through" in reply.lower() or "going through the motions" in reply.lower()


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


def test_first_turn_explicit_sleep_signal_stays_on_sleep_even_if_sleep_item_is_already_resolved():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="opening-sleep-anchor-en",
        language="en",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="I've been dragging myself through the day and sleep has been broken for the last couple of weeks.",
                language_tag="en",
            ),
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    snapshot.items["phq_q3_sleep"].status = "resolved"
    snapshot.items["phq_q3_sleep"].value = 2
    snapshot.items["phq_q3_sleep"].confidence = 0.84
    snapshot.items["phq_q3_sleep"].evidence_span_ids = ["EV-1"]

    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "sleep"
    assert coverage.dialogue.target_item is None
    assert asked_item is None
    assert "sleep gets disrupted" in reply.lower() or "sleep" in reply.lower()


def test_first_turn_explicit_sleep_signal_stays_on_sleep_in_hinglish_even_if_sleep_item_is_already_resolved():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="opening-sleep-anchor-hinglish",
        language="hinglish",
        turns=[
            Turn(
                turn_id=1,
                speaker="user",
                text="Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.",
                language_tag="hinglish",
            ),
        ],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    snapshot.items["phq_q3_sleep"].status = "resolved"
    snapshot.items["phq_q3_sleep"].value = 2
    snapshot.items["phq_q3_sleep"].confidence = 0.84
    snapshot.items["phq_q3_sleep"].evidence_span_ids = ["EV-1"]

    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic == "sleep"
    assert coverage.dialogue.target_item is None
    assert asked_item is None
    assert "sleep" in reply.lower()


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


def test_mind_only_anxiety_answer_skips_body_relaxation_repeat_and_moves_to_worry_scope():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="mind-only-worry-scope",
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
                text="It is mostly mental, not body tension. I can sometimes distract myself, but the worry comes back and my mind keeps running.",
                language_tag="en",
            ),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q3_excessive_worry"
    assert asked_item == "gad_q3_excessive_worry"
    assert "relax your body" not in reply.lower()
    assert "both together" not in reply.lower()


def test_hindi_mind_only_anxiety_answer_skips_body_relaxation_repeat_and_moves_to_worry_scope():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-mind-only-worry-scope",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब चिंता शुरू होती है, क्या आप दिमाग को उससे हटा पाते हैं, या रोकने की कोशिश के बाद भी वह चलती रहती है?",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="शरीर में उतना तनाव नहीं होता, केवल दिमाग चलता रहता है। दिमाग को शांत करना मुश्किल होता है।",
                language_tag="hi",
            ),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_item == "gad_q3_excessive_worry"
    assert asked_item == "gad_q3_excessive_worry"
    assert "शरीर को ढीला" not in reply
    assert "दोनों साथ में" not in reply


def test_post_close_hinglish_close_mat_karo_signal_reopens_flow():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-close-mat-karo",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="assistant", text=FINAL_REST_MESSAGES["hinglish"], language_tag="hinglish"),
            Turn(turn_id=2, speaker="user", text="Conversation close mat karo, aur kya poochna hai?", language_tag="hinglish"),
        ],
    )

    assert planner._should_reopen_after_close(session, planner._latest_user_text(session)) is True


def test_hindi_summary_request_returns_working_summary_instead_of_more_questions():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-summary-request",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="काफी आलस रहता है और किसी काम में मन नहीं लगता।", language_tag="hi"),
            Turn(turn_id=3, speaker="assistant", text="जब यह होता है, क्या ज़्यादा दिन भर की उदासी जैसा रहता है या लहरों में आता है?", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="मन भारी भी रहता है और शुरू करने का मन नहीं करता।", language_tag="hi"),
            Turn(turn_id=5, speaker="user", text="अब तक जो समझा है उसका summary बता दो।", language_tag="hi"),
        ],
        asked_items=["phq_q1_anhedonia", "phq_q2_low_mood"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert "?" in reply
    assert asked_item is not None


def test_hindi_polite_summary_request_returns_working_summary():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-summary-request-polite",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="पिछले दो हफ़्तों में सबसे ज़्यादा क्या भारी लगा?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="रात में नींद टूटती रहती है और दिन में आलस रहता है।", language_tag="hi"),
            Turn(turn_id=3, speaker="assistant", text="जो चीज़ें पहले अच्छी लगती थीं, उनमें अभी मन कम लगता है या फिर उनसे बहुत कम महसूस होता है?", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="काम शुरू करने से पहले ही मन हट जाता है और चिंता नौकरी को लेकर रहती है।", language_tag="hi"),
            Turn(turn_id=5, speaker="user", text="अब तक जो समझा है उसका एक साफ़ सार बता दीजिए।", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q4_fatigue", "phq_q1_anhedonia", "gad_q3_excessive_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hi", SafetyFlag(level="none"))
    reply, asked_item = planner.next_reply(snapshot, session)

    assert "?" in reply
    assert asked_item is not None


def test_hinglish_appetite_signal_preempts_old_anxiety_loop():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hinglish-appetite-preempt",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Jab worry start hoti hai, kya mind ko usse hata paate ho, ya woh loop hoti rehti hai?", language_tag="hinglish"),
            Turn(turn_id=2, speaker="user", text="Future aur job wali line par atak jaati hai.", language_tag="hinglish"),
            Turn(turn_id=3, speaker="assistant", text="Toh jab yeh worry aati hai, kya mind ko quiet karna harder hota hai?", language_tag="hinglish"),
            Turn(turn_id=4, speaker="user", text="Haan, aur appetite off hai, meals bhi skip ho rahe hain.", language_tag="hinglish"),
        ],
        asked_items=["gad_q2_control_worry", "gad_q3_excessive_worry"],
    )

    snapshot = ConversationScorer().analyze(session.turns, "hinglish", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)

    assert coverage.dialogue.target_topic == "energy"
    assert coverage.dialogue.target_item == "phq_q5_appetite"


def test_daylong_low_mood_answer_uses_deepening_probe_not_repeat_timing_prompt():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="hi-daylong-mood",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी जैसा रहता है, या कुछ खास समय पर लहरों में आता है?", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="नहीं, यह दिन भर रहता है।", language_tag="hi"),
        ],
        asked_items=["phq_q2_low_mood"],
    )
    plan = DialoguePlan(target_item="phq_q2_low_mood", target_topic="mood", current_topic="mood", stage="clarification")

    prompt = planner._build_item_prompt("hi", plan, session)

    assert "यह समय-सूचना मददगार" not in prompt
    assert "सपाट या भारी एहसास" in prompt


def test_hindi_latest_mood_turn_does_not_get_hijacked_by_stale_anxiety_scene():
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    session = ChatSession(
        session_id="hi-stale-anxiety-scene-hijack",
        language="hi",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="फिर से स्वागत है। अगर यह आपकी हाल की चिंता बातचीत से जुड़ा लग रहा है, तो बताइए आज क्या वैसा है और क्या अलग है।", language_tag="hi"),
            Turn(turn_id=2, speaker="user", text="नीम का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए", language_tag="hi"),
            Turn(turn_id=3, speaker="assistant", text="लगता है इसका असर नींद पर साफ़ पड़ रहा है। जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?", language_tag="hi"),
            Turn(turn_id=4, speaker="user", text="यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है", language_tag="hi"),
            Turn(turn_id=5, speaker="assistant", text="लगता है दिन अपने-आप में ही भारी लग रहे हैं। जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?", language_tag="hi"),
            Turn(turn_id=6, speaker="user", text="मां पहले से ही है जाता है कोई काम करने की इच्छा करती ही नहीं है", language_tag="hi"),
            Turn(turn_id=7, speaker="assistant", text="जब यह सपाट या भारी एहसास रहता है, क्या किसी ज़रूरी चीज़ पर ध्यान देने पर थोड़ा सा हल्का होता है, या काम करते रहने पर भी वैसा ही बना रहता है?", language_tag="hi"),
            Turn(turn_id=8, speaker="user", text="मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है", language_tag="hi"),
            Turn(turn_id=9, speaker="assistant", text="जब दिन ज़्यादा भारी होता है, सबसे आगे क्या महसूस होता है: उदासी, शुरू करने से पहले ही मन हट जाना, या अपने-आप पर ज़्यादा कठोर हो जाना?", language_tag="hi"),
            Turn(turn_id=10, speaker="user", text="उदासी और किसी काम से मन है जाना", language_tag="hi"),
        ],
        asked_items=["phq_q3_sleep", "phq_q2_low_mood", "phq_q6_worthlessness"],
    )

    snapshot = scorer.analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"mood", "energy", "focus"}
    assert coverage.dialogue.target_scene in {"mood_selfview", "sleep_functioning", None}
    assert coverage.dialogue.target_topic != "anxiety"
    assert asked_item != "gad_q4_trouble_relaxing"
    assert "आगे कुछ गलत हो सकता है" not in reply


def test_downplayed_anxiety_with_sleep_energy_and_focus_detail_stays_out_of_anxiety():
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    session = ChatSession(
        session_id="en-downplayed-anxiety-energy-focus",
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
                text="I would not call it panic. Sleep has shifted later, the next day I drag through everything, lunch just slips, and I have to read the same paragraph three times.",
                language_tag="en",
            ),
        ],
        asked_items=["gad_q2_control_worry"],
    )

    snapshot = scorer.analyze(session.turns, "en", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"sleep", "energy", "focus", "mood"}
    assert coverage.dialogue.target_topic != "anxiety"
    assert asked_item in {None, "phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration"}
    assert "pull your mind away" not in reply.lower()
    assert "quiet your thoughts" not in reply.lower()


def test_hindi_fatigue_followup_yields_to_appetite_or_focus_after_daytime_functioning_answer():
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    session = ChatSession(
        session_id="hi-fatigue-yields-to-appetite-focus",
        language="hi",
        turns=[
            Turn(
                turn_id=1,
                speaker="assistant",
                text="जब थकान या ऊर्जा की कमी बढ़ती है, क्या ज़्यादा ऐसा लगता है कि शरीर भारी पड़ रहा है, दिमाग शुरू होने में धीमा है, या दोनों?",
                language_tag="hi",
            ),
            Turn(
                turn_id=2,
                speaker="user",
                text="दोपहर का खाना छूट जाता है और वही लाइन कई बार पढ़नी पड़ती है।",
                language_tag="hi",
            ),
        ],
        asked_items=["phq_q4_fatigue"],
    )

    snapshot = scorer.analyze(session.turns, "hi", SafetyFlag(level="none"))
    coverage = planner.build_plan(snapshot, session)
    reply, asked_item = planner.next_reply(snapshot, session)

    assert coverage.dialogue.target_topic in {"energy", "focus"}
    assert asked_item in {None, "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"}
    assert asked_item != "phq_q4_fatigue"
    assert "शरीर भारी पड़ रहा है" not in reply
