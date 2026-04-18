#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
from urllib.request import urlopen


DEFAULT_EDAIC_SOURCE_URL = "https://dcapswoz.ict.usc.edu/wwwedaic/"
DEFAULT_OUTPUT_DIR = Path("data") / "external" / "E-DAIC-public"
ROOT_FILES = (
    ("metadata_mapped.csv", "metadata_mapped.csv"),
    ("E-DAIC%20Manual.pdf", "E-DAIC Manual.pdf"),
    ("labels2019.tar.gz", "labels2019.tar.gz"),
)
LABEL_FILES = (
    "Detailed_PHQ8_Labels.csv",
    "detailed_lables.csv",
    "train_split.csv",
    "dev_split.csv",
    "test_split.csv",
)
SESSION_ARCHIVE_RE = re.compile(r"^(\d+)_P\.tar\.gz$")
HREF_RE = re.compile(r'href="([^"#?]+)"', re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download public E-DAIC metadata/labels and optional participant tarballs."
    )
    parser.add_argument("--source-url", default=DEFAULT_EDAIC_SOURCE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--session-ids",
        default="",
        help="Optional comma-separated session IDs to download full participant tarballs for.",
    )
    parser.add_argument("--max-session-archives", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_text(url: str) -> str:
    with urlopen(url) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_index_links(html: str) -> set[str]:
    return {unescape(match.group(1)).strip() for match in HREF_RE.finditer(html) if match.group(1).strip()}


def fetch_file(source_url: str, filename: str, output_dir: Path, overwrite: bool = False) -> Path | None:
    destination = output_dir / filename
    if destination.exists() and not overwrite:
        print(f"[skip] {filename} already exists")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    url = urljoin(source_url, filename)
    try:
        with urlopen(url) as response:
            destination.write_bytes(response.read())
    except Exception as exc:  # pragma: no cover - network error handling
        print(f"[warn] failed to download {filename}: {exc}")
        return None
    print(f"[ok] downloaded {filename}")
    return destination


def parse_session_ids(raw_ids: str) -> set[str]:
    ids: set[str] = set()
    for token in raw_ids.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        cleaned = cleaned.removesuffix(".tar.gz").removesuffix("_P")
        if cleaned.isdigit():
            ids.add(str(int(cleaned)))
    return ids


def map_available_session_archives(links: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for link in links:
        match = SESSION_ARCHIVE_RE.match(link)
        if not match:
            continue
        mapping[str(int(match.group(1)))] = link
    return mapping


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    root_url = args.source_url if args.source_url.endswith("/") else f"{args.source_url}/"
    labels_url = urljoin(root_url, "labels/")
    data_url = urljoin(root_url, "data/")

    print(f"[info] source: {root_url}")
    print(f"[info] output: {output_dir}")

    root_links = parse_index_links(read_text(root_url))
    labels_links = parse_index_links(read_text(labels_url))
    data_links = parse_index_links(read_text(data_url))

    for source_name, target_name in ROOT_FILES:
        if source_name in root_links:
            downloaded = fetch_file(root_url, source_name, output_dir, overwrite=args.overwrite)
            if downloaded is not None and downloaded.name != target_name:
                target_path = downloaded.with_name(target_name)
                if target_path.exists() and args.overwrite:
                    target_path.unlink()
                if not target_path.exists():
                    downloaded.rename(target_path)
        else:
            print(f"[warn] root file not present in source index: {source_name}")

    for filename in LABEL_FILES:
        if filename in labels_links:
            fetch_file(labels_url, filename, output_dir / "labels", overwrite=args.overwrite)
        else:
            print(f"[warn] label file not present in source index: {filename}")

    requested_ids = sorted(parse_session_ids(args.session_ids), key=int)
    if args.max_session_archives is not None and args.max_session_archives >= 0:
        requested_ids = requested_ids[: args.max_session_archives]

    if not requested_ids:
        print("[info] no participant tarballs requested")
        return 0

    archive_map = map_available_session_archives(data_links)
    download_count = 0
    for session_id in requested_ids:
        filename = archive_map.get(session_id)
        if not filename:
            print(f"[warn] participant tarball not found in index: {session_id}_P.tar.gz")
            continue
        downloaded = fetch_file(data_url, filename, output_dir / "archives", overwrite=args.overwrite)
        if downloaded is not None:
            download_count += 1
    print(f"[done] downloaded {download_count} participant tarball(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
