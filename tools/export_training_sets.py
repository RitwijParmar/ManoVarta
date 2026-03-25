#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles
from manovarta_core.training_data import (
    assign_conversations_to_splits,
    build_extractor_examples,
    build_follow_up_examples,
    build_profile_splits,
    build_safety_examples,
    write_jsonl,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export fine-tuning and classifier datasets from the seed corpus.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "processed"),
        help="Directory for JSONL outputs.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()
    split_manifest = build_profile_splits(profiles)
    split_conversations = assign_conversations_to_splits(conversations, split_manifest)

    for split_name, split_records in split_conversations.items():
        extractor_examples = build_extractor_examples(split_records)
        follow_up_examples = build_follow_up_examples(split_records)
        safety_examples = build_safety_examples(split_records)
        write_jsonl(output_dir / f"extractor_{split_name}.jsonl", extractor_examples)
        write_jsonl(output_dir / f"follow_up_{split_name}.jsonl", follow_up_examples)
        write_jsonl(output_dir / f"safety_{split_name}.jsonl", safety_examples)
        print(
            f"{split_name}: extractor={len(extractor_examples)} "
            f"follow_up={len(follow_up_examples)} safety={len(safety_examples)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
