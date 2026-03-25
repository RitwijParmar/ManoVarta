from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn


def test_scoring_keeps_local_symptom_context():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How have things felt lately?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I feel drained all day and my sleep schedule is messed up.",
            language_tag="en",
        ),
    ]

    safety = SafetyMonitor().assess(turns)
    snapshot = ConversationScorer().analyze(turns, "en", safety)

    assert snapshot.items["phq_q3_sleep"].value == 2
    assert snapshot.items["phq_q4_fatigue"].value == 3
    assert snapshot.items["phq_q9_self_harm"].value is None


def test_scoring_picks_up_hindi_worry_and_sleep():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="Pichhle do hafton mein sabse zyada kya pareshan kar raha hai?", language_tag="hi"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Dimag hamesha chalta rehta hai aur raat ko soch band nahi hoti.",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Neend toot toot ke aati hai.",
            language_tag="hi",
        ),
    ]

    safety = SafetyMonitor().assess(turns)
    snapshot = ConversationScorer().analyze(turns, "hi", safety)

    assert snapshot.items["gad_q2_control_worry"].value == 3
    assert snapshot.items["phq_q3_sleep"].value == 2
