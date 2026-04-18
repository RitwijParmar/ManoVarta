#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse


RANGE_RE = re.compile(r"bytes=(\d+)-(\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robust Google Drive resumable upload with token refresh per chunk.")
    parser.add_argument("--upload-url", required=True, help="Resumable upload URL from Drive init response.")
    parser.add_argument("--file", required=True, help="Path to local file to upload.")
    parser.add_argument("--chunk-mb", type=int, default=64, help="Chunk size in MB.")
    parser.add_argument(
        "--gcloud-bin",
        default="/Users/ritwij/google-cloud-sdk/bin/gcloud",
        help="Path to gcloud binary.",
    )
    parser.add_argument(
        "--cloudsdk-python",
        default="/Users/ritwij/miniforge3/bin/python",
        help="Interpreter for CLOUDSDK_PYTHON.",
    )
    parser.add_argument("--max-retries", type=int, default=8)
    return parser.parse_args()


def access_token(gcloud_bin: str, cloudsdk_python: str) -> str:
    env = dict(os.environ)
    env["CLOUDSDK_PYTHON"] = cloudsdk_python
    out = subprocess.check_output([gcloud_bin, "auth", "print-access-token"], env=env, text=True)
    token = out.strip()
    if not token:
        raise RuntimeError("Failed to fetch access token from gcloud.")
    return token


def request_put(url: str, token: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"
    conn = http.client.HTTPSConnection(parsed.netloc, timeout=1800)
    req_headers = {"Authorization": f"Bearer {token}"}
    req_headers.update(headers)
    conn.request("PUT", path, body=body, headers=req_headers)
    resp = conn.getresponse()
    resp_body = resp.read()
    resp_headers = {k.lower(): v for k, v in resp.getheaders()}
    status = resp.status
    conn.close()
    return status, resp_headers, resp_body


def parse_uploaded_end(headers: dict[str, str]) -> int:
    value = headers.get("range", "").strip()
    if not value:
        return -1
    match = RANGE_RE.fullmatch(value)
    if not match:
        return -1
    return int(match.group(2))


def probe_offset(upload_url: str, total_size: int, gcloud_bin: str, cloudsdk_python: str) -> int:
    token = access_token(gcloud_bin, cloudsdk_python)
    headers = {
        "Content-Length": "0",
        "Content-Range": f"bytes */{total_size}",
    }
    status, resp_headers, _ = request_put(upload_url, token, headers, b"")
    if status == 308:
        uploaded_end = parse_uploaded_end(resp_headers)
        return uploaded_end + 1
    if status in (200, 201):
        return total_size
    raise RuntimeError(f"Probe failed with status={status}, headers={resp_headers}")


def human_bytes(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024.0
        unit += 1
    return f"{value:.2f}{units[unit]}"


def main() -> None:
    args = parse_args()
    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise SystemExit(f"File not found: {file_path}")

    total = file_path.stat().st_size
    chunk_size = args.chunk_mb * 1024 * 1024
    start = probe_offset(args.upload_url, total, args.gcloud_bin, args.cloudsdk_python)

    if start >= total:
        print("Upload already complete.", flush=True)
        return

    print(
        f"Resuming upload from byte {start} / {total} ({(start / total) * 100:.2f}%). "
        f"chunk={args.chunk_mb}MB",
        flush=True,
    )

    with file_path.open("rb") as f:
        f.seek(start)
        while start < total:
            end = min(start + chunk_size - 1, total - 1)
            length = end - start + 1
            chunk = f.read(length)
            if len(chunk) != length:
                raise RuntimeError(f"Read mismatch at [{start}, {end}] (wanted {length}, got {len(chunk)})")

            attempt = 0
            while True:
                attempt += 1
                token = access_token(args.gcloud_bin, args.cloudsdk_python)
                headers = {
                    "Content-Type": "application/x-tar",
                    "Content-Length": str(length),
                    "Content-Range": f"bytes {start}-{end}/{total}",
                }
                try:
                    status, resp_headers, resp_body = request_put(args.upload_url, token, headers, chunk)
                except Exception as exc:  # noqa: BLE001
                    if attempt >= args.max_retries:
                        raise RuntimeError(f"Network error at chunk [{start}, {end}]: {exc}") from exc
                    sleep_s = min(2 ** attempt, 30)
                    print(
                        f"Transient network error on [{start}, {end}] attempt={attempt}: {exc}; retry in {sleep_s}s",
                        flush=True,
                    )
                    time.sleep(sleep_s)
                    continue

                if status in (200, 201):
                    uploaded = total
                    print(
                        f"Uploaded {human_bytes(uploaded)} / {human_bytes(total)} (100.00%)",
                        flush=True,
                    )
                    if resp_body:
                        try:
                            payload = json.loads(resp_body.decode("utf-8", errors="ignore"))
                            print(json.dumps(payload, ensure_ascii=True), flush=True)
                        except Exception:  # noqa: BLE001
                            print(resp_body.decode("utf-8", errors="ignore"), flush=True)
                    return

                if status == 308:
                    uploaded_end = parse_uploaded_end(resp_headers)
                    if uploaded_end < start - 1:
                        raise RuntimeError(
                            f"Drive reported uploaded_end={uploaded_end} behind start={start}. "
                            f"headers={resp_headers}"
                        )
                    new_start = uploaded_end + 1
                    uploaded = new_start
                    pct = (uploaded / total) * 100.0
                    print(
                        f"Uploaded {human_bytes(uploaded)} / {human_bytes(total)} ({pct:.2f}%)",
                        flush=True,
                    )
                    start = new_start
                    f.seek(start)
                    break

                if status in (429, 500, 502, 503, 504):
                    if attempt >= args.max_retries:
                        body_txt = resp_body.decode("utf-8", errors="ignore")
                        raise RuntimeError(
                            f"Retryable status {status} exceeded retries at [{start}, {end}]. body={body_txt}"
                        )
                    sleep_s = min(2 ** attempt, 30)
                    print(
                        f"Retryable status={status} on [{start}, {end}] attempt={attempt}; retry in {sleep_s}s",
                        flush=True,
                    )
                    time.sleep(sleep_s)
                    continue

                body_txt = resp_body.decode("utf-8", errors="ignore")
                raise RuntimeError(
                    f"Upload failed status={status} at [{start}, {end}] headers={resp_headers} body={body_txt}"
                )


if __name__ == "__main__":
    main()

