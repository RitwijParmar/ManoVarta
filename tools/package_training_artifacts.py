#!/usr/bin/env python3
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(description="Package local training outputs and reports into one zip file.")
    parser.add_argument("--source-dir", default=str(PROJECT_ROOT / "outputs"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "artifacts"))
    parser.add_argument(
        "--include-dir",
        action="append",
        default=[],
        help="Extra directory to include in the archive. Can be repeated.",
    )
    parser.add_argument("--archive-name", help="Optional fixed archive filename.")
    return parser.parse_args()


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    extra_dirs = [Path(path) for path in args.include_dir]

    if not source_dir.exists():
        raise SystemExit(f"Missing source directory: {source_dir}")
    for directory in extra_dirs:
        if not directory.exists():
            raise SystemExit(f"Missing include directory: {directory}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = args.archive_name
    if not archive_name:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"manovarta_training_artifacts_{stamp}.zip"
    archive_path = output_dir / archive_name

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "git_revision": git_revision(),
            "source_dir": str(source_dir),
            "included_dirs": [str(directory) for directory in extra_dirs],
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")

        directories = [source_dir, *extra_dirs]
        for directory in directories:
            prefix = directory.name
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=Path(prefix) / path.relative_to(directory))

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
