#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles


def main() -> None:
    conversations = load_seed_conversations()
    profiles = load_seed_profiles()

    languages = Counter(conv["language"] for conv in conversations)
    review = Counter(conv["review_status"] for conv in conversations)
    safety = Counter(conv.get("safety_flag", {}).get("level", "none") for conv in conversations)
    profile_languages = Counter(profile["language"] for profile in profiles)
    nuance_tags = Counter(tag for profile in profiles for tag in profile.get("nuance_tags", []))

    print("Conversations:", len(conversations))
    print("Languages:", dict(languages))
    print("Profiles:", len(profiles))
    print("Profile languages:", dict(profile_languages))
    print("Review status:", dict(review))
    print("Safety levels:", dict(safety))
    print("Top nuance tags:", dict(nuance_tags.most_common(8)))


if __name__ == "__main__":
    main()
