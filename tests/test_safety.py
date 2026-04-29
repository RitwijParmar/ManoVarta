from manovarta_core.safety import SafetyMonitor
from manovarta_core.safety_assessors import compose_runtime_safety_flag
from manovarta_core.schemas import SafetyFlag, Turn


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


def test_negated_self_harm_phrase_does_not_false_trigger_urgent():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="I would not say I want to hurt myself, but I do feel stuck and useless sometimes.",
            language_tag="en",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "none"


def test_hindi_negated_self_harm_phrase_does_not_false_trigger_urgent():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="खुद को नुकसान पहुंचाने का मन नहीं है, बस दिमाग शांत नहीं होता।",
            language_tag="hi",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "none"


def test_hindi_negated_self_harm_with_death_phrase_does_not_false_trigger_urgent():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="खुद को नुकसान पहुंचाने या मरने जैसा कुछ नहीं सोच रहा हूं, बस नींद और दिमाग दोनों खराब चल रहे हैं।",
            language_tag="hi",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "none"


def test_hindi_negated_self_harm_without_death_phrase_does_not_false_trigger_urgent():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="खुद को नुकसान पहुँचाने जैसा कुछ नहीं सोच रहा हूँ, बस नींद और ध्यान दोनों गड़बड़ हैं।",
            language_tag="hi",
        ),
    ]

    flag = SafetyMonitor().assess(turns)

    assert flag.level == "none"


def test_advisory_only_safety_signal_does_not_escalate_without_runtime_corroboration():
    flag = compose_runtime_safety_flag(
        extractor_flag=SafetyFlag(level="urgent", cues=["semantic:test"], rationale="similarity-only"),
        rule_flag=SafetyFlag(level="none"),
        checkpoint_flag=SafetyFlag(level="none"),
    )

    assert flag.level == "none"
