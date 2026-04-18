#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen


DEFAULT_ZIP_URL = "https://github.com/Mishrakshitij/Po-Em-MHLCDS/archive/refs/heads/main.zip"
DEFAULT_OUTPUT_DIR = Path("data") / "external" / "Po-Em-MHLCDS"
FILES_TO_EXTRACT = {
    "ROOT_README.md": "README.md",
    "Data/readme.md": "data_readme.md",
    "Data/MHLCD.csv": "MHLCD.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the public Po-Em-MHLCDS counseling dialogue bundle.")
    parser.add_argument("--zip-url", default=DEFAULT_ZIP_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def download_zip(url: str) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="po_em_mhlcds_", suffix=".zip", delete=False)
    temp_path = Path(handle.name)
    with handle:
        with urlopen(url) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    return temp_path


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    existing = [output_dir / target for target in FILES_TO_EXTRACT.values()]
    if all(path.exists() for path in existing) and not args.overwrite:
        print("[skip] Po-Em-MHLCDS public files already present")
        return 0

    archive_path = download_zip(args.zip_url)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            destination = output_dir / FILES_TO_EXTRACT["ROOT_README.md"]
            if not destination.exists() or args.overwrite:
                destination.write_bytes(archive.read("Po-Em-MHLCDS-main/README.md"))
                print(f"[ok] extracted {destination.name}")

            nested_bytes = archive.read("Po-Em-MHLCDS-main/Po-Em-MHLCDS_Codes_and_Data.zip")
            nested_archive = zipfile.ZipFile(io.BytesIO(nested_bytes))
            for source_suffix, target_name in FILES_TO_EXTRACT.items():
                if source_suffix == "ROOT_README.md":
                    continue
                archive_name = f"Po-Em-MHLCDS_Codes_and_Data/{source_suffix}"
                destination = output_dir / target_name
                if destination.exists() and not args.overwrite:
                    print(f"[skip] {target_name} already exists")
                    continue
                destination.write_bytes(nested_archive.read(archive_name))
                print(f"[ok] extracted {target_name}")
    finally:
        archive_path.unlink(missing_ok=True)

    print("[done] downloaded Po-Em-MHLCDS public bundle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
