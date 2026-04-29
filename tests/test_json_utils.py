from manovarta_core.json_utils import normalize_extractor_payload, normalize_safety_level, parse_extractor_payload, parse_json_object


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


def test_parse_extractor_payload_salvages_truncated_item_list():
    payload = parse_extractor_payload(
        '{"items": [{"item_id": "phq_q2_low_mood", "value": 1, "evidence_quote": ""}, '
        '{"item_id": "phq_q3_sleep", "value": 2, "evidence_quote": "sleep bad"}, '
        '{"item_id": "gad_q1_nervous", "value": 1'
    )

    assert payload is not None
    assert [item["item_id"] for item in payload["items"]] == [
        "phq_q2_low_mood",
        "phq_q3_sleep",
        "gad_q1_nervous",
    ]
    assert [item["value"] for item in payload["items"]] == [1, 2, 1]


def test_parse_extractor_payload_normalizes_compact_schema_and_safety_aliases():
    payload = parse_extractor_payload(
        '{"items": [{"item_id": "phq_q2_low_mood", "value": 2}], "safety_level": "high_caution"}'
    )

    assert payload is not None
    assert payload["items"] == [{"item_id": "phq_q2_low_mood", "value": 2}]
    assert payload["safety_level"] == "review"


def test_parse_extractor_payload_normalizes_legacy_item_aliases():
    payload = parse_extractor_payload(
        '{"items": [{"item_id": "gad_q7_fear_awful", "value": 2}], "safety_level": "none"}'
    )

    assert payload is not None
    assert payload["items"] == [{"item_id": "gad_q7_afraid", "value": 2}]


def test_parse_extractor_payload_salvages_line_based_items():
    payload = parse_extractor_payload(
        "gad_q3_excessive_worry: 2\n"
        "gad_q4_trouble_relaxing -> 1\n"
        "phq_q3_sleep is 2"
    )

    assert payload is not None
    assert [item["item_id"] for item in payload["items"]] == [
        "gad_q3_excessive_worry",
        "gad_q4_trouble_relaxing",
        "phq_q3_sleep",
    ]
    assert [item["value"] for item in payload["items"]] == [2, 1, 2]


def test_normalize_extractor_payload_keeps_explicit_zero_value():
    payload = normalize_extractor_payload(
        {
            "items": [
                {
                    "item_id": "phq_q9_self_harm",
                    "value": 0,
                    "evidence_quote": "I am not suicidal and I do not want to hurt myself.",
                    "confidence_note": "Explicit denial.",
                }
            ],
            "safety_level": "none",
        }
    )

    assert payload is not None
    assert payload["items"] == [
        {
            "item_id": "phq_q9_self_harm",
            "value": 0,
            "evidence_quote": "I am not suicidal and I do not want to hurt myself.",
            "confidence_note": "Explicit denial.",
        }
    ]


def test_normalize_safety_level_maps_aliases():
    assert normalize_safety_level("high_caution") == "review"
    assert normalize_safety_level("crisis") == "urgent"
    assert normalize_safety_level("safe") == "none"
