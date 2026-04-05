from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import ChatSession, SafetyFlag


def test_dialogue_planner_prioritizes_appetite_in_energy_topic_when_unresolved():
    planner = DialoguePlanner()
    snapshot = ConversationScorer().analyze([], "en", SafetyFlag(level="none"))
    session = ChatSession(session_id="session-1", language="en")

    target_item = planner._select_target_item(snapshot, session, "energy", [])

    assert target_item == "phq_q5_appetite"


def test_dialogue_planner_prioritizes_control_worry_in_anxiety_topic_when_unresolved():
    planner = DialoguePlanner()
    snapshot = ConversationScorer().analyze([], "en", SafetyFlag(level="none"))
    session = ChatSession(session_id="session-2", language="en")

    target_item = planner._select_target_item(snapshot, session, "anxiety", [])

    assert target_item == "gad_q2_control_worry"
