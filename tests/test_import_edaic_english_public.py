from tools.import_edaic_english_public import (
    build_score_map,
    parse_score,
    select_participant_rows,
)


def test_parse_score_clamps_to_valid_range() -> None:
    assert parse_score("2") == 2
    assert parse_score("3.0") == 3
    assert parse_score("9") == 3
    assert parse_score("-2") == 0
    assert parse_score("not-a-number") == 0


def test_select_participant_rows_balances_binary_classes() -> None:
    rows = [
        {"participant_id": "1", "phq_binary": "0"},
        {"participant_id": "2", "phq_binary": "0"},
        {"participant_id": "3", "phq_binary": "0"},
        {"participant_id": "4", "phq_binary": "1"},
        {"participant_id": "5", "phq_binary": "1"},
        {"participant_id": "6", "phq_binary": "1"},
    ]
    selected = select_participant_rows(rows, max_sessions=4)
    assert [row["participant_id"] for row in selected] == ["1", "2", "4", "5"]


def test_build_score_map_prefers_public_phq8_values() -> None:
    text = "i cannot sleep and i feel anxious and worried all day"
    phq8 = {
        "phq_q1_anhedonia": 1,
        "phq_q2_low_mood": 2,
        "phq_q3_sleep": 3,
        "phq_q4_fatigue": 1,
        "phq_q5_appetite": 0,
        "phq_q6_worthlessness": 0,
        "phq_q7_concentration": 1,
        "phq_q8_psychomotor": 0,
    }
    scores = build_score_map(normalized_text=text, phq8_scores=phq8)
    assert scores["phq_q3_sleep"] == 3
    assert scores["phq_q2_low_mood"] == 2
    assert scores["gad_q1_nervous"] >= 1
