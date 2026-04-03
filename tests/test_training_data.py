import json
from collections import Counter

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles
from manovarta_core.training_data import (
    assign_conversations_to_splits,
    build_best_extractor_train_examples,
    build_extractor_examples,
    build_follow_up_examples,
    build_profile_splits,
    build_safety_examples,
)


def test_profile_splits_stay_balanced_by_language():
    profiles = load_seed_profiles()
    manifest = build_profile_splits(profiles)
    total_profiles = len(profiles)

    assert len(manifest.train_profiles) + len(manifest.dev_profiles) + len(manifest.test_profiles) == total_profiles

    profiles = {profile["patient_id"]: profile for profile in profiles}
    for profile_ids in (manifest.train_profiles, manifest.dev_profiles, manifest.test_profiles):
        language_counts = Counter(profiles[profile_id]["language"] for profile_id in profile_ids)
        assert set(language_counts) == {"en", "hi", "hinglish"}
        assert len(set(language_counts.values())) == 1


def test_training_examples_export_for_all_tasks():
    conversations = load_seed_conversations()
    manifest = build_profile_splits(load_seed_profiles())
    grouped = assign_conversations_to_splits(conversations, manifest)

    extractor = build_extractor_examples(grouped["train"])
    follow_ups = build_follow_up_examples(grouped["train"])
    safety = build_safety_examples(grouped["train"])

    assert extractor
    assert follow_ups
    assert safety
    extractor_payload = json.loads(extractor[0]["response"])
    assert set(extractor_payload) == {"items", "safety_level"}
    if extractor_payload["items"]:
        assert set(extractor_payload["items"][0]) == {"item_id", "value"}
    assert safety[0]["label"] in {"none", "review", "urgent"}
    assert "Most recent disclosure:" in safety[0]["text"]

    positive_conversations = sum(
        1 for conversation in grouped["train"] if conversation.get("safety_flag", {}).get("level") != "none"
    )
    assert len(safety) >= len(grouped["train"]) + positive_conversations


def test_best_extractor_train_examples_boost_multilingual_coverage():
    conversations = load_seed_conversations()
    manifest = build_profile_splits(load_seed_profiles())
    grouped = assign_conversations_to_splits(conversations, manifest)

    train_examples = build_extractor_examples(grouped["train"])
    best_examples = build_best_extractor_train_examples(train_examples)

    train_counts = Counter(example["language"] for example in train_examples)
    best_counts = Counter(example["language"] for example in best_examples)

    assert best_counts["hi"] >= train_counts["hi"] * 2
    assert best_counts["hinglish"] >= train_counts["hinglish"] * 2
    assert best_counts["en"] >= train_counts["en"]


def test_best_extractor_train_examples_can_boost_hinglish_hardcases_and_limit_daic_ratio():
    multilingual_examples = [
        {"id": "en-1", "language": "en", "text": "en"},
        {"id": "hi-1", "language": "hi", "text": "hi"},
        {
            "id": "hinglish-safe",
            "language": "hinglish",
            "text": "hinglish-safe",
            "safety_level": "none",
            "positive_item_count": 4,
            "annotator_notes": "",
        },
        {
            "id": "hinglish-hard",
            "language": "hinglish",
            "text": "hinglish-hard",
            "safety_level": "review",
            "positive_item_count": 9,
            "annotator_notes": "Indirect masking case.",
        },
    ]
    auxiliary_examples = [{"id": f"aux-{idx}", "language": "en", "text": f"aux-{idx}"} for idx in range(10)]

    best_examples = build_best_extractor_train_examples(
        multilingual_examples,
        auxiliary_english_examples=auxiliary_examples,
        language_weights={"en": 1, "hi": 1, "hinglish": 1},
        auxiliary_ratio=0.2,
        hinglish_hardcase_repeats=3,
    )

    counts = Counter(example["id"] for example in best_examples)

    assert counts["hinglish-safe"] == 1
    assert counts["hinglish-hard"] == 3
    assert counts["aux-0"] == 1
