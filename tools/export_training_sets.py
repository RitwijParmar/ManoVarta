#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.daic_woz import load_daic_conversations
from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles
from manovarta_core.training_data import (
    assign_conversations_to_splits,
    build_best_extractor_train_examples,
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
    parser.add_argument(
        "--daic-root",
        default=None,
        help="Optional DAIC-WOZ root directory. When provided, writes auxiliary English extractor sets and an augmented train set.",
    )
    parser.add_argument(
        "--extractor-style",
        choices=["compact", "verbose"],
        default="compact",
        help="Extractor supervision style. compact is recommended for better schema stability.",
    )
    parser.add_argument("--best-en-weight", type=int, default=1, help="Repeat factor for English seed examples.")
    parser.add_argument("--best-hi-weight", type=int, default=2, help="Repeat factor for Hindi seed examples.")
    parser.add_argument(
        "--best-hinglish-weight",
        type=int,
        default=2,
        help="Repeat factor for Hinglish seed examples before hard-case boosting.",
    )
    parser.add_argument(
        "--hinglish-hardcase-repeats",
        type=int,
        default=1,
        help="Total repeat factor for Hinglish hard cases identified from safety/annotation cues.",
    )
    parser.add_argument(
        "--daic-ratio",
        type=float,
        default=0.5,
        help="Fraction of the multilingual rebalanced train set to append from DAIC auxiliary English examples.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()
    split_manifest = build_profile_splits(profiles)
    split_conversations = assign_conversations_to_splits(conversations, split_manifest)

    for split_name, split_records in split_conversations.items():
        extractor_examples = build_extractor_examples(split_records, schema_style=args.extractor_style)
        follow_up_examples = build_follow_up_examples(split_records)
        safety_examples = build_safety_examples(split_records)
        write_jsonl(output_dir / f"extractor_{split_name}.jsonl", extractor_examples)
        write_jsonl(output_dir / f"follow_up_{split_name}.jsonl", follow_up_examples)
        write_jsonl(output_dir / f"safety_{split_name}.jsonl", safety_examples)
        print(
            f"{split_name}: extractor={len(extractor_examples)} "
            f"follow_up={len(follow_up_examples)} safety={len(safety_examples)}"
        )

    best_train = build_best_extractor_train_examples(
        build_extractor_examples(split_conversations["train"], schema_style=args.extractor_style),
        language_weights={
            "en": args.best_en_weight,
            "hi": args.best_hi_weight,
            "hinglish": args.best_hinglish_weight,
        },
        hinglish_hardcase_repeats=args.hinglish_hardcase_repeats,
    )
    write_jsonl(output_dir / "extractor_train_best.jsonl", best_train)
    print(f"best train: extractor={len(best_train)}")

    if args.daic_root:
        daic_conversations = load_daic_conversations(Path(args.daic_root))
        daic_train_examples = build_extractor_examples(daic_conversations["train"], schema_style=args.extractor_style)
        daic_dev_examples = build_extractor_examples(daic_conversations["dev"], schema_style=args.extractor_style)
        daic_test_examples = build_extractor_examples(daic_conversations["test"], schema_style=args.extractor_style)
        write_jsonl(output_dir / "extractor_daic_train.jsonl", daic_train_examples)
        write_jsonl(output_dir / "extractor_daic_dev.jsonl", daic_dev_examples)
        write_jsonl(output_dir / "extractor_daic_test.jsonl", daic_test_examples)

        augmented_train = build_extractor_examples(split_conversations["train"], schema_style=args.extractor_style) + daic_train_examples
        write_jsonl(output_dir / "extractor_train_augmented_daic.jsonl", augmented_train)
        best_augmented_train = build_best_extractor_train_examples(
            build_extractor_examples(split_conversations["train"], schema_style=args.extractor_style),
            auxiliary_english_examples=daic_train_examples,
            language_weights={
                "en": args.best_en_weight,
                "hi": args.best_hi_weight,
                "hinglish": args.best_hinglish_weight,
            },
            auxiliary_ratio=args.daic_ratio,
            hinglish_hardcase_repeats=args.hinglish_hardcase_repeats,
        )
        write_jsonl(output_dir / "extractor_train_best_augmented_daic.jsonl", best_augmented_train)
        print(
            "daic auxiliary: "
            f"train={len(daic_train_examples)} dev={len(daic_dev_examples)} "
            f"test={len(daic_test_examples)} augmented_train={len(augmented_train)} "
            f"best_augmented_train={len(best_augmented_train)} "
            f"daic_ratio={args.daic_ratio}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
