#!/usr/bin/env python3
import argparse
from datetime import datetime
from pathlib import Path
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(description="Package local training outputs into one zip file.")
    parser.add_argument("--source-dir", default=str(PROJECT_ROOT / "outputs"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "artifacts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)

    if not source_dir.exists():
        raise SystemExit(f"Missing source directory: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = output_dir / f"manovarta_training_artifacts_{stamp}.zip"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(source_dir))

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
