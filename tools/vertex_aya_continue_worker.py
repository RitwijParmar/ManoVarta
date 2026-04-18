#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vertex AI worker that runs Aya DAIC continuation training locally on the training VM and uploads outputs to GCS."
    )
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="cuda")
    parser.add_argument("--daic-root", required=True, help="DAIC-WOZ source path. Supports gs:// or local.")
    parser.add_argument("--init-adapter", required=True, help="Aya adapter source path. Supports gs:// or local.")
    parser.add_argument("--gcs-output-root", required=True, help="GCS root where outputs and reports should be uploaded.")
    parser.add_argument("--scratch-dir", default="/tmp/manovarta_vertex")
    parser.add_argument("--extractor-model", default="CohereLabs/aya-expanse-8b")
    parser.add_argument("--extractor-epochs", type=int, default=1)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--disable-extractor-4bit", action="store_true")
    return parser.parse_args()


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    without_scheme = uri[5:]
    bucket, _, prefix = without_scheme.partition("/")
    if not bucket:
        raise ValueError(f"Missing bucket in URI: {uri}")
    return bucket, prefix.strip("/")


def join_gcs_uri(root: str, *parts: str) -> str:
    bucket, prefix = parse_gcs_uri(root)
    clean_parts = [prefix] if prefix else []
    clean_parts.extend(part.strip("/") for part in parts if part and part.strip("/"))
    if clean_parts:
        return f"gs://{bucket}/{'/'.join(clean_parts)}"
    return f"gs://{bucket}"


def _storage_client():
    try:
        from google.cloud import storage
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Vertex worker is missing google-cloud-storage. Install training extras for the custom job."
        ) from exc
    return storage.Client()


def _download_blob_to_path(blob: Any, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(target_path))


def download_gcs_tree(uri: str, destination: Path) -> None:
    storage_client = _storage_client()
    bucket_name, prefix = parse_gcs_uri(uri)
    bucket = storage_client.bucket(bucket_name)
    blobs = list(storage_client.list_blobs(bucket_or_name=bucket_name, prefix=prefix.rstrip("/") + "/"))
    if not blobs:
        raise FileNotFoundError(f"No GCS objects found under {uri}")
    destination.mkdir(parents=True, exist_ok=True)
    prefix_root = prefix.rstrip("/") + "/"
    for blob in blobs:
        relative_name = blob.name[len(prefix_root) :]
        if not relative_name or blob.name.endswith("/"):
            continue
        _download_blob_to_path(blob, destination / relative_name)


def download_gcs_file(uri: str, destination: Path) -> Path:
    storage_client = _storage_client()
    bucket_name, blob_name = parse_gcs_uri(uri)
    blob = storage_client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise FileNotFoundError(f"GCS object does not exist: {uri}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(destination))
    return destination


def upload_directory(local_dir: Path, destination_root: str) -> None:
    storage_client = _storage_client()
    bucket_name, prefix = parse_gcs_uri(destination_root)
    bucket = storage_client.bucket(bucket_name)
    for file_path in sorted(path for path in local_dir.rglob("*") if path.is_file()):
        blob_name = "/".join(part for part in (prefix, file_path.relative_to(local_dir).as_posix()) if part)
        bucket.blob(blob_name).upload_from_filename(str(file_path))


def upload_file(local_path: Path, destination_uri: str) -> None:
    storage_client = _storage_client()
    bucket_name, blob_name = parse_gcs_uri(destination_uri)
    storage_client.bucket(bucket_name).blob(blob_name).upload_from_filename(str(local_path))


def materialize_input(source: str, destination: Path) -> Path:
    def _resolve_adapter_root(path: Path) -> Path:
        if path.is_file():
            return path

        direct_config = path / "adapter_config.json"
        if direct_config.exists():
            return path

        candidates = sorted(path.rglob("adapter_config.json"))
        if not candidates:
            return path

        # Prefer a directory that also has adapter weights, then shortest path depth.
        ranked: list[tuple[int, int, Path]] = []
        for config_path in candidates:
            root = config_path.parent
            has_weights = int((root / "adapter_model.safetensors").exists())
            depth = len(root.relative_to(path).parts)
            ranked.append((-has_weights, depth, root))
        ranked.sort()
        return ranked[0][2]

    def _extract_archive(file_path: Path, extract_root: Path) -> Path:
        extract_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(file_path, "r:*") as archive:
            archive.extractall(extract_root)
        return _resolve_adapter_root(extract_root)

    if source.startswith("gs://"):
        bucket_name, blob_or_prefix = parse_gcs_uri(source)
        storage_client = _storage_client()
        blob = storage_client.bucket(bucket_name).blob(blob_or_prefix)
        if blob.exists():
            local_file = destination / Path(blob_or_prefix).name
            download_gcs_file(source, local_file)
            if tarfile.is_tarfile(local_file):
                return _extract_archive(local_file, destination / "extracted")
            return local_file
        download_gcs_tree(source, destination)
        return _resolve_adapter_root(destination)

    source_path = Path(source)
    if source_path.is_file() and tarfile.is_tarfile(source_path):
        return _extract_archive(source_path, destination)
    if source_path.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_path, destination)
        return destination
    if source_path.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        return destination
    raise FileNotFoundError(f"Input path does not exist: {source}")


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def write_manifest(args: argparse.Namespace, manifest_path: Path, reports_root: str, outputs_root: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "daic_root": args.daic_root,
        "init_adapter": args.init_adapter,
        "gcs_output_root": args.gcs_output_root,
        "gcs_reports_root": reports_root,
        "gcs_outputs_root": outputs_root,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    scratch_root = Path(args.scratch_dir).resolve()
    scratch_root.mkdir(parents=True, exist_ok=True)
    run_root = scratch_root / "aya_daic_continue"
    if run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    local_daic_root = materialize_input(args.daic_root, run_root / "daic")
    local_init_adapter = materialize_input(args.init_adapter, run_root / "init_adapter")
    local_reports_dir = run_root / "reports" / "vertex_aya_continue"
    local_extractor_output = run_root / "outputs" / "extractor-aya-8b-compact-daic-continue"

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "run_colab_daic_continue.py"),
        "--device",
        args.device,
        "--daic-root",
        str(local_daic_root),
        "--init-adapter",
        str(local_init_adapter),
        "--reports-dir",
        str(local_reports_dir),
        "--extractor-output",
        str(local_extractor_output),
        "--extractor-model",
        args.extractor_model,
        "--extractor-epochs",
        str(args.extractor_epochs),
        "--extractor-batch-size",
        str(args.extractor_batch_size),
        "--extractor-grad-accum",
        str(args.extractor_grad_accum),
        "--extractor-max-length",
        str(args.extractor_max_length),
        "--extractor-save-steps",
        str(args.extractor_save_steps),
        "--extractor-max-new-tokens",
        str(args.extractor_max_new_tokens),
        "--smoke-limit",
        str(args.smoke_limit),
    ]
    if args.disable_extractor_4bit:
        cmd.append("--disable-extractor-4bit")
    run(cmd)

    outputs_root = join_gcs_uri(args.gcs_output_root, "outputs", local_extractor_output.name)
    reports_root = join_gcs_uri(args.gcs_output_root, "reports", local_reports_dir.name)
    upload_directory(local_extractor_output, outputs_root)
    upload_directory(local_reports_dir, reports_root)

    manifest_path = run_root / "vertex_job_manifest.json"
    write_manifest(args, manifest_path, reports_root, outputs_root)
    upload_file(manifest_path, join_gcs_uri(reports_root, manifest_path.name))
    print(json.dumps({"reports_root": reports_root, "outputs_root": outputs_root}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
