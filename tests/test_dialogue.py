from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import ChatSession, DialoguePlan, DisclosureMetrics, SafetyFlag, UserStyleProfile


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
