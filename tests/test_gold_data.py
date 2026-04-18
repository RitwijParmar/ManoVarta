from manovarta_core.gold_data import load_gold_conversations, load_gold_profiles


def test_load_gold_conversations_gold_core_excludes_hindi_pilot():
    conversations = load_gold_conversations(include_hindi_pilot=False, gold_core_only=True)

    assert conversations
    assert all(record["language"] == "en" for record in conversations)
    assert all(record["dataset_role"] == "gold_core" for record in conversations)


def test_load_gold_conversations_normalizes_gad_q7_schema():
    conversations = load_gold_conversations(include_hindi_pilot=True, gold_core_only=False)

    assert conversations
    sample = next(record for record in conversations if record["language"] == "en")
    assert "gad_q7_afraid" in sample["gad7_item_labels"]
    assert "gad_q7_fear_awful" not in sample["gad7_item_labels"]


def test_load_gold_profiles_marks_hindi_as_voice_extension_pilot():
    profiles = load_gold_profiles(include_hindi_pilot=True, gold_core_only=False)

    assert profiles
    hindi_profile = next(profile for profile in profiles if profile["language"] == "hi")
    assert "pilot_voice_extension" in hindi_profile["nuance_tags"]
