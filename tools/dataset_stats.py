#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parent.parent / "data" / "seed" / "conversations.json"
    conversations = json.loads(path.read_text(encoding="utf-8"))

    languages = Counter(conv["language"] for conv in conversations)
    review = Counter(conv["review_status"] for conv in conversations)
    safety = Counter(conv.get("safety_flag", {}).get("level", "none") for conv in conversations)

    print("Conversations:", len(conversations))
    print("Languages:", dict(languages))
    print("Review status:", dict(review))
    print("Safety levels:", dict(safety))


if __name__ == "__main__":
    main()
