from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles
from manovarta_core.training_data import (
    assign_conversations_to_splits,
    build_extractor_examples,
    build_follow_up_examples,
    build_profile_splits,
    build_safety_examples,
)


def test_profile_splits_stay_balanced_by_language():
    manifest = build_profile_splits(load_seed_profiles())

    assert len(manifest.train_profiles) == 6
    assert len(manifest.dev_profiles) == 3
    assert len(manifest.test_profiles) == 3


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
    assert "items" in extractor[0]["response"]
    assert safety[0]["label"] in {"none", "review", "urgent"}
