from collections import Counter

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles
from manovarta_core.training_data import assign_conversations_to_splits, build_profile_splits


def test_seed_corpus_is_balanced_and_scaled():
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()

    assert len(profiles) >= 48
    assert len(conversations) >= 48

    language_counts = Counter(conversation["language"] for conversation in conversations)
    assert language_counts["en"] >= 16
    assert language_counts["hi"] >= 16
    assert language_counts["hinglish"] >= 16

    review_count = sum(
        1 for conversation in conversations if conversation.get("safety_flag", {}).get("level") == "review"
    )
    urgent_count = sum(
        1 for conversation in conversations if conversation.get("safety_flag", {}).get("level") == "urgent"
    )
    assert review_count >= 10
    assert urgent_count >= 4


def test_split_manifest_keeps_each_language_in_all_splits():
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()
    manifest = build_profile_splits(profiles)
    split_conversations = assign_conversations_to_splits(conversations, manifest)

    for split_name in ("train", "dev", "test"):
        language_counts = Counter(record["language"] for record in split_conversations[split_name])
        assert language_counts["en"] >= 1, split_name
        assert language_counts["hi"] >= 1, split_name
        assert language_counts["hinglish"] >= 1, split_name
