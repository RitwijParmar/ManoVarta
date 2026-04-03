#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone or refresh the ManoVarta repo safely inside Colab."
    )
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--repo-dir", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    return parser.parse_args()


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def clone_urls(repo_url: str, github_token: str | None) -> list[str]:
    urls: list[str] = []
    if github_token and repo_url.startswith("https://github.com/"):
        urls.append(repo_url.replace("https://", f"https://oauth2:{github_token}@"))
    urls.append(repo_url)
    return urls


def sync_existing_repo(repo_dir: Path, branch: str) -> bool:
    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        return False
    for cmd in (
        ["git", "-C", str(repo_dir), "fetch", "origin"],
        ["git", "-C", str(repo_dir), "checkout", branch],
        ["git", "-C", str(repo_dir), "reset", "--hard", f"origin/{branch}"],
    ):
        result = run(cmd)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)
    return True


def ensure_empty_target(repo_dir: Path) -> None:
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_dir.parent.mkdir(parents=True, exist_ok=True)


def clone_repo(repo_url: str, repo_dir: Path, branch: str, github_token: str | None) -> None:
    errors: list[dict[str, str]] = []
    for candidate in clone_urls(repo_url, github_token):
        result = run(["git", "clone", "--branch", branch, candidate, str(repo_dir)])
        if result.returncode == 0:
            return
        errors.append(
            {
                "url": candidate.split("@github.com/")[-1] if "@github.com/" in candidate else candidate,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            }
        )
        ensure_empty_target(repo_dir)

    fallback_extract_zip(repo_url, repo_dir, branch, github_token, errors)


def fallback_extract_zip(
    repo_url: str,
    repo_dir: Path,
    branch: str,
    github_token: str | None,
    clone_errors: list[dict[str, str]],
) -> None:
    if not repo_url.startswith("https://github.com/"):
        raise SystemExit(json.dumps({"clone_errors": clone_errors}, indent=2))

    repo_path = repo_url.removeprefix("https://github.com/").removesuffix(".git")
    zip_url = f"https://github.com/{repo_path}/archive/refs/heads/{branch}.zip"
    request = urllib.request.Request(zip_url)
    if github_token:
        request.add_header("Authorization", f"Bearer {github_token}")

    ensure_empty_target(repo_dir)
    with tempfile.TemporaryDirectory(prefix="manovarta-colab-sync-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        archive_path = tmp_dir / "repo.zip"
        try:
            with urllib.request.urlopen(request) as response, archive_path.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        except urllib.error.URLError as exc:
            payload = {"clone_errors": clone_errors, "zip_url": zip_url, "zip_error": str(exc)}
            raise SystemExit(json.dumps(payload, indent=2))

        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(tmp_dir)

        extracted_root = next(
            (path for path in tmp_dir.iterdir() if path.is_dir() and path.name.startswith(repo_path.split("/")[-1] + "-")),
            None,
        )
        if extracted_root is None:
            raise SystemExit(
                json.dumps(
                    {"clone_errors": clone_errors, "zip_url": zip_url, "zip_error": "Could not locate extracted repo root"},
                    indent=2,
                )
            )
        shutil.move(str(extracted_root), str(repo_dir))


def main() -> int:
    args = parse_args()
    repo_dir = Path(args.repo_dir)

    if sync_existing_repo(repo_dir, args.branch):
        print(f"Repo refreshed at {repo_dir}", flush=True)
        return 0

    ensure_empty_target(repo_dir)
    clone_repo(args.repo_url, repo_dir, args.branch, args.github_token)
    print(f"Repo ready at {repo_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
