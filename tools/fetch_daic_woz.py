#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
from urllib.request import urlopen


DEFAULT_DAIC_SOURCE_URL = "https://dcapswoz.ict.usc.edu/wwwdaicwoz/"
DEFAULT_OUTPUT_DIR = Path("data") / "external" / "DAIC-WOZ"
SPLIT_FILES = {
    "train": "train_split_Depression_AVEC2017.csv",
    "dev": "dev_split_Depression_AVEC2017.csv",
    "test": "test_split_Depression_AVEC2017.csv",
}
OPTIONAL_METADATA_FILES = (
    "full_test_split.csv",
    "DAICWOZDepression_Documentation_AVEC2017.pdf",
)
SESSION_ZIP_RE = re.compile(r"^(\d+)_P\.zip$")
HREF_RE = re.compile(r'href="([^"#?]+)"', re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download DAIC-WOZ metadata and optional session zip files.")
    parser.add_argument("--source-url", default=DEFAULT_DAIC_SOURCE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--session-split", choices=("none", "train", "dev", "test", "all"), default="none")
    parser.add_argument(
        "--session-ids",
        default="",
        help="Optional comma-separated session IDs (for example: 300,301,302).",
    )
    parser.add_argument("--max-session-zips", type=int, default=None)
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
        if cleaned.endswith("_P"):
            cleaned = cleaned[:-2]
        if cleaned.isdigit():
            ids.add(str(int(cleaned)))
    return ids


def read_split_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return set()
        field_lookup = {"".join(ch.lower() for ch in name if ch.isalnum()): name for name in reader.fieldnames}
        session_field = None
        for candidate in ("participantid", "participant_id", "sessionid", "session_id"):
            if candidate in field_lookup:
                session_field = field_lookup[candidate]
                break
        if session_field is None:
            session_field = reader.fieldnames[0]
        ids: set[str] = set()
        for row in reader:
            raw_value = str(row.get(session_field, "")).strip()
            if raw_value.isdigit():
                ids.add(str(int(raw_value)))
        return ids


def select_ids_by_split(session_split: str, split_paths: dict[str, Path]) -> set[str]:
    if session_split == "none":
        return set()
    if session_split == "all":
        return set().union(*(read_split_ids(path) for path in split_paths.values()))
    return read_split_ids(split_paths[session_split])


def map_available_session_zips(links: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for link in links:
        match = SESSION_ZIP_RE.match(link)
        if not match:
            continue
        session_id = str(int(match.group(1)))
        mapping[session_id] = link
    return mapping


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_url = args.source_url if args.source_url.endswith("/") else f"{args.source_url}/"

    print(f"[info] source: {source_url}")
    print(f"[info] output: {output_dir}")
    index_html = read_text(source_url)
    links = parse_index_links(index_html)

    downloaded_metadata: dict[str, Path] = {}
    for split_name, split_filename in SPLIT_FILES.items():
        if split_filename in links:
            path = fetch_file(source_url, split_filename, output_dir, overwrite=args.overwrite)
            if path is not None:
                downloaded_metadata[split_name] = path
        else:
            print(f"[warn] split file not present in source index: {split_filename}")
    for filename in OPTIONAL_METADATA_FILES:
        if filename in links:
            fetch_file(source_url, filename, output_dir, overwrite=args.overwrite)

    explicit_ids = parse_session_ids(args.session_ids)
    split_ids = select_ids_by_split(args.session_split, downloaded_metadata)
    requested_ids = sorted(explicit_ids.union(split_ids), key=int)

    if args.max_session_zips is not None and args.max_session_zips >= 0:
        requested_ids = requested_ids[: args.max_session_zips]

    if not requested_ids:
        print("[info] no session zips requested (use --session-split and/or --session-ids)")
        return 0

    available_session_zips = map_available_session_zips(links)
    missing = [session_id for session_id in requested_ids if session_id not in available_session_zips]
    for session_id in missing:
        print(f"[warn] session zip not found in index: {session_id}_P.zip")

    download_count = 0
    for session_id in requested_ids:
        filename = available_session_zips.get(session_id)
        if not filename:
            continue
        downloaded = fetch_file(source_url, filename, output_dir, overwrite=args.overwrite)
        if downloaded is not None:
            download_count += 1

    print(f"[done] downloaded {download_count} session zip(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
