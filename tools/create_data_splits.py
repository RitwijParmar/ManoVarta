#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_profiles
from manovarta_core.training_data import build_profile_splits


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic profile-level train/dev/test splits.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "processed" / "splits.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()

    manifest = build_profile_splits(load_seed_profiles())
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    print(f"wrote split manifest to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
