from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles


def test_seed_loader_reads_all_seed_bundles():
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()

    assert len(profiles) == 12
    assert len(conversations) == 12
    assert {conversation["language"] for conversation in conversations} == {"en", "hi", "hinglish"}
