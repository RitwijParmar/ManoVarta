from tools.import_indicvoices_hindi_valid import normalize_text_field, session_ids_to_fill, transcript_payload


def test_session_ids_to_fill_generates_expected_range():
    ids = session_ids_to_fill(start_index=1, max_sessions=3)
    assert ids == ["MVGOLD-HI-001", "MVGOLD-HI-002", "MVGOLD-HI-003"]


def test_transcript_payload_prefers_verbatim_text():
    payload = transcript_payload(
        session_id="MVGOLD-HI-001",
        cohort="pilot",
        metadata_obj={
            "verbatim": "मुझे नींद नहीं आती।",
            "normalized": "मुझे नींद नहीं आती",
            "speaker_id": "S1",
            "age_group": "26-35",
        },
        source_json_path="Hindi/v1/valid/example.json",
        source_wav_path="Hindi/v1/valid/example.wav",
    )
    assert payload["is_placeholder"] is False
    assert payload["turns"][0]["text"] == "मुझे नींद नहीं आती।"
    assert payload["source"]["speaker_id"] == "S1"


def test_normalize_text_field_handles_segment_list():
    text = normalize_text_field(
        [
            {"start": 1.0, "end": 2.0, "text": "हलो"},
            {"start": 2.1, "end": 3.0, "text": "नमस्कार"},
        ]
    )
    assert text == "हलो नमस्कार"
