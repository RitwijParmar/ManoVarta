from manovarta_core.json_utils import parse_json_object


def test_parse_json_object_handles_fenced_content():
    payload = parse_json_object(
        """```json
{"items": [{"item_id": "phq_q2_low_mood", "value": 2}], "safety_level": "none"}
```"""
    )

    assert payload is not None
    assert payload["items"][0]["item_id"] == "phq_q2_low_mood"


def test_parse_json_object_recovers_first_balanced_object_with_trailing_text():
    payload = parse_json_object(
        '{"items": [{"item_id": "gad_q1_nervous", "value": 2}], "safety_level": "review"}\nextra tokens'
    )

    assert payload is not None
    assert payload["safety_level"] == "review"

