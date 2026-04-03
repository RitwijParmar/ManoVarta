#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DISPLAY_PREFIX = "manovarta-aya-daic-continue"
DEFAULT_OUTPUT_PREFIX = "manovarta/vertex-runs"
DEFAULT_STAGING_PREFIX = "manovarta/vertex-staging"
DEFAULT_MACHINE_TYPE = "g2-standard-24"
DEFAULT_ACCELERATOR_TYPE = "NVIDIA_L4"
DEFAULT_ACCELERATOR_COUNT = 1
DEFAULT_BOOT_DISK_SIZE_GB = 300
DEFAULT_EXTRACTOR_MODEL = "CohereLabs/aya-expanse-8b"
VERTEX_REQUIREMENTS = [
    "fastapi==0.115.12",
    "pydantic>=2.10,<=2.12.3",
    "huggingface_hub>=0.34.0,<1.0",
    "python-dotenv>=1.0,<2.0",
    "google-cloud-storage>=2.18.0",
    "datasets>=3.0.0",
    "accelerate>=1.0.0",
    "trl>=0.11.0",
    "peft>=0.12.0",
    "transformers>=4.45",
    "numpy>=1.26.0",
    "sentencepiece>=0.2.0",
    "bitsandbytes>=0.45.0",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit Aya DAIC continuation training to Vertex AI CustomJob."
    )
    parser.add_argument("--project", required=True, help="GCP project ID.")
    parser.add_argument("--location", default="us-central1", help="Vertex AI region, for example us-central1.")
    parser.add_argument(
        "--staging-bucket",
        required=True,
        help="GCS bucket for Vertex staging, for example gs://my-vertex-bucket.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Optional GCS root for uploaded outputs/reports. Defaults under the staging bucket.",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Optional Vertex job display name. Defaults to a timestamped ManoVarta Aya continuation name.",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="Optional Vertex runtime service account email.",
    )
    parser.add_argument(
        "--container-uri",
        default=None,
        help="Optional override for the Vertex prebuilt training container URI.",
    )
    parser.add_argument(
        "--daic-root",
        required=True,
        help="DAIC-WOZ root. Can be a gs:// URI or a local directory to upload before job submission.",
    )
    parser.add_argument(
        "--init-adapter",
        required=True,
        help="Aya LoRA adapter to continue from. Can be a gs:// URI, a local directory, or a local tar.gz bundle.",
    )
    parser.add_argument("--machine-type", default=DEFAULT_MACHINE_TYPE)
    parser.add_argument("--accelerator-type", default=DEFAULT_ACCELERATOR_TYPE)
    parser.add_argument("--accelerator-count", type=int, default=DEFAULT_ACCELERATOR_COUNT)
    parser.add_argument("--boot-disk-size-gb", type=int, default=DEFAULT_BOOT_DISK_SIZE_GB)
    parser.add_argument("--extractor-model", default=DEFAULT_EXTRACTOR_MODEL)
    parser.add_argument("--extractor-epochs", type=int, default=1)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--disable-extractor-4bit", action="store_true")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the job to finish instead of returning right after submission.",
    )
    return parser.parse_args()


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    without_scheme = uri[5:]
    bucket, _, prefix = without_scheme.partition("/")
    if not bucket:
        raise ValueError(f"Missing bucket in URI: {uri}")
    return bucket, prefix.strip("/")


def normalize_bucket_uri(value: str) -> str:
    uri = value if value.startswith("gs://") else f"gs://{value}"
    bucket, prefix = parse_gcs_uri(uri)
    if prefix:
        raise ValueError(f"Staging bucket must not include a path: {value}")
    return f"gs://{bucket}"


def join_gcs_uri(root: str, *parts: str) -> str:
    bucket, prefix = parse_gcs_uri(root)
    clean_parts = [prefix] if prefix else []
    clean_parts.extend(part.strip("/") for part in parts if part and part.strip("/"))
    if clean_parts:
        return f"gs://{bucket}/{'/'.join(clean_parts)}"
    return f"gs://{bucket}"


def default_output_root(staging_bucket: str, display_name: str) -> str:
    return join_gcs_uri(staging_bucket, DEFAULT_OUTPUT_PREFIX, display_name)


def region_group(location: str) -> str:
    lowered = location.lower()
    if lowered.startswith("europe-"):
        return "europe"
    if lowered.startswith("asia-"):
        return "asia"
    return "us"


def default_training_container(location: str) -> str:
    region = region_group(location)
    return f"{region}-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def upload_local_path(storage_client: Any, local_path: Path, destination_uri: str) -> str:
    local_path = local_path.resolve()
    bucket_name, prefix = parse_gcs_uri(destination_uri)
    bucket = storage_client.bucket(bucket_name)

    if local_path.is_file():
        blob_name = "/".join(part for part in (prefix, local_path.name) if part)
        bucket.blob(blob_name).upload_from_filename(str(local_path))
        return f"gs://{bucket_name}/{blob_name}"

    if not local_path.is_dir():
        raise FileNotFoundError(f"Path does not exist: {local_path}")

    for file_path in sorted(path for path in local_path.rglob("*") if path.is_file()):
        blob_name = "/".join(part for part in (prefix, _relative_posix(file_path, local_path)) if part)
        bucket.blob(blob_name).upload_from_filename(str(file_path))
    return destination_uri


def stage_input(storage_client: Any, source: str, destination_uri: str) -> str:
    if source.startswith("gs://"):
        return source.rstrip("/")
    return upload_local_path(storage_client, Path(source), destination_uri)


def build_worker_args(
    args: argparse.Namespace,
    gcs_daic_root: str,
    gcs_init_adapter: str,
    gcs_output_root: str,
) -> list[str]:
    worker_args = [
        "--device",
        "cuda",
        "--daic-root",
        gcs_daic_root,
        "--init-adapter",
        gcs_init_adapter,
        "--gcs-output-root",
        gcs_output_root,
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
        worker_args.append("--disable-extractor-4bit")
    return worker_args


def collect_environment_variables() -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def main() -> int:
    args = parse_args()
    display_name = args.display_name or f"{DEFAULT_DISPLAY_PREFIX}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    staging_bucket = normalize_bucket_uri(args.staging_bucket)
    output_root = args.output_root or default_output_root(staging_bucket, display_name)

    try:
        from google.cloud import aiplatform
        from google.cloud import storage
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Install Vertex dependencies first: pip install -e .[vertex]"
        ) from exc

    storage_client = storage.Client(project=args.project)
    staged_daic_root = stage_input(
        storage_client,
        args.daic_root,
        join_gcs_uri(staging_bucket, DEFAULT_STAGING_PREFIX, display_name, "inputs", "daic"),
    )
    staged_init_adapter = stage_input(
        storage_client,
        args.init_adapter,
        join_gcs_uri(staging_bucket, DEFAULT_STAGING_PREFIX, display_name, "inputs", "init_adapter"),
    )

    worker_args = build_worker_args(args, staged_daic_root, staged_init_adapter, output_root)
    env_vars = collect_environment_variables()
    container_uri = args.container_uri or default_training_container(args.location)

    aiplatform.init(
        project=args.project,
        location=args.location,
        staging_bucket=staging_bucket,
    )
    custom_job = aiplatform.CustomJob.from_local_script(
        display_name=display_name,
        script_path=str(PROJECT_ROOT / "tools" / "vertex_aya_continue_worker.py"),
        container_uri=container_uri,
        requirements=VERTEX_REQUIREMENTS,
        args=worker_args,
        replica_count=1,
        machine_type=args.machine_type,
        accelerator_type=args.accelerator_type if args.accelerator_count > 0 else None,
        accelerator_count=args.accelerator_count,
        boot_disk_size_gb=args.boot_disk_size_gb,
        base_output_dir=output_root,
        environment_variables=env_vars or None,
    )
    custom_job.submit(
        service_account=args.service_account or None,
    )
    custom_job.wait_for_resource_creation()
    resource_name = custom_job.resource_name
    if args.wait:
        custom_job.wait()

    payload = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "display_name": display_name,
        "project": args.project,
        "location": args.location,
        "staging_bucket": staging_bucket,
        "output_root": output_root,
        "container_uri": container_uri,
        "daic_root": staged_daic_root,
        "init_adapter": staged_init_adapter,
        "machine_type": args.machine_type,
        "accelerator_type": args.accelerator_type,
        "accelerator_count": args.accelerator_count,
        "service_account": args.service_account,
        "waited_for_completion": bool(args.wait),
        "resource_name": resource_name,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
