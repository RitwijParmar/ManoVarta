from manovarta_core.safety import SafetyMonitor
from manovarta_core.schemas import Turn


def test_review_level_safety_handles_indirect_disappearance_language():
    turns = [
        Turn(turn_id=1, speaker="user", text="Kabhi kabhi lagta hai bas gayab ho jaun for a while.", language_tag="hinglish"),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "review"
    assert flag.needs_human_review is True


def test_review_level_safety_handles_english_disappear_for_a_while_language():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="I have been feeling low and sometimes I wish I could disappear for a while.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "review"
    assert flag.needs_human_review is True


def test_review_level_safety_handles_english_not_being_here_language():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sometimes I feel like not being here would be easier.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "review"
    assert flag.needs_human_review is True


def test_review_level_safety_handles_hindi_disappearance_language():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="कभी कभी लगता है काश मैं कुछ समय के लिए गायब हो जाऊँ।",
            language_tag="hi",
        ),
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


def test_urgent_safety_handles_passive_not_waking_up_paraphrase():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="I have been feeling low and sometimes I think it might be easier if I do not wake up.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "urgent"
    assert flag.needs_human_review is True
    assert any("wake up" in cue.lower() for cue in flag.cues)


def test_review_safety_handles_burden_language():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Kabhi lagta hai mere bina sab theek hoga and I am just a burden at home.",
            language_tag="hinglish",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "review"
    assert flag.needs_human_review is True


def test_urgent_safety_handles_method_plus_time_language():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="I keep thinking about taking all the pills tonight because nothing matters.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "urgent"
    assert flag.needs_human_review is True


def test_safety_does_not_match_partial_word_fragments():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sleep is messy and I have not eaten properly for days.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "none"
