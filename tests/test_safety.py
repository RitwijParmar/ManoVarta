from manovarta_core.safety import SafetyMonitor
from manovarta_core.schemas import Turn


def test_review_level_safety_handles_indirect_disappearance_language():
    turns = [
        Turn(turn_id=1, speaker="user", text="Kabhi kabhi lagta hai bas gayab ho jaun for a while.", language_tag="hinglish"),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "review"
    assert flag.needs_human_review is True


def test_urgent_safety_handles_direct_self_harm_language():
    turns = [
        Turn(turn_id=1, speaker="user", text="Some nights I don't want to live like this.", language_tag="en"),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "urgent"
    assert flag.needs_human_review is True
