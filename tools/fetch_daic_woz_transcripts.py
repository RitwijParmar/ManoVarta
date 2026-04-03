#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from urllib.parse import urljoin

from remotezip import RemoteZip

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.fetch_daic_woz import (  # noqa: E402
    DEFAULT_DAIC_SOURCE_URL,
    OPTIONAL_METADATA_FILES,
    SPLIT_FILES,
    fetch_file,
    map_available_session_zips,
    parse_session_ids,
    parse_index_links,
    read_split_ids,
    read_text,
    select_ids_by_split,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download only the DAIC-WOZ split metadata and transcript CSVs from the public session zip files."
    )
    parser.add_argument("--source-url", default=DEFAULT_DAIC_SOURCE_URL)
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "external" / "DAIC-WOZ-transcripts"),
        help="Directory to write split CSVs and transcript-only session folders.",
    )
    parser.add_argument(
        "--session-split",
        choices=("train", "dev", "test", "all"),
        default="all",
        help="Which split's transcript zips to materialize.",
    )
    parser.add_argument(
        "--session-ids",
        default="",
        help="Optional comma-separated session IDs to include in addition to the selected split(s).",
    )
    parser.add_argument("--max-session-zips", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def fetch_transcript_from_zip(zip_url: str, session_id: str, output_dir: Path, overwrite: bool = False) -> Path:
    session_dir = output_dir / f"{session_id}_P"
    transcript_name = f"{session_id}_TRANSCRIPT.csv"
    transcript_path = session_dir / transcript_name
    if transcript_path.exists() and not overwrite:
        print(f"[skip] {transcript_name} already exists")
        return transcript_path

    session_dir.mkdir(parents=True, exist_ok=True)
    with RemoteZip(zip_url) as archive:
        if transcript_name not in archive.namelist():
            raise FileNotFoundError(f"{transcript_name} not found inside {zip_url}")
        with archive.open(transcript_name) as handle:
            transcript_path.write_bytes(handle.read())
    print(f"[ok] downloaded {transcript_name}")
    return transcript_path


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
    if args.session_split == "all":
        split_ids = set().union(*(read_split_ids(path) for path in downloaded_metadata.values()))
    else:
        split_ids = select_ids_by_split(args.session_split, downloaded_metadata)
    requested_ids = sorted(explicit_ids.union(split_ids), key=int)

    if args.max_session_zips is not None and args.max_session_zips >= 0:
        requested_ids = requested_ids[: args.max_session_zips]

    available_session_zips = map_available_session_zips(links)
    if not requested_ids:
        requested_ids = sorted(available_session_zips.keys(), key=int)
        if args.max_session_zips is not None and args.max_session_zips >= 0:
            requested_ids = requested_ids[: args.max_session_zips]

    missing = [session_id for session_id in requested_ids if session_id not in available_session_zips]
    for session_id in missing:
        print(f"[warn] session zip not found in index: {session_id}_P.zip")

    transcript_count = 0
    for session_id in requested_ids:
        zip_name = available_session_zips.get(session_id)
        if not zip_name:
            continue
        zip_url = urljoin(source_url, zip_name)
        fetch_transcript_from_zip(zip_url, session_id, output_dir, overwrite=args.overwrite)
        transcript_count += 1

    print(f"[done] downloaded {transcript_count} transcript(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
