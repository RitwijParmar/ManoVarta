#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


DEFAULT_IMAGE_URI = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"
DEFAULT_MACHINE_TYPE = "g2-standard-4"
DEFAULT_ACCELERATOR_TYPE = "NVIDIA_L4"
DEFAULT_ACCELERATOR_COUNT = 1
DEFAULT_EXTRACTOR_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_GCLOUD_BIN = "/Users/ritwij/.local/opt/google-cloud-sdk/bin/gcloud"

PIP_DEPENDENCIES = [
    "fastapi==0.115.12",
    "pydantic==2.12.3",
    "huggingface_hub==0.34.0",
    "hf_transfer>=0.1.8",
    "python-dotenv==1.0.1",
    "google-cloud-storage==2.18.0",
    "datasets==3.0.0",
    "accelerate==1.0.0",
    "trl==0.11.0",
    "peft==0.12.0",
    "transformers==4.45.0",
    "numpy==1.26.0",
    "sentencepiece==0.2.0",
    "bitsandbytes==0.45.0",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit a Vertex CustomJob via REST using gcloud auth token (no ADC required)."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--display-name", default=None)
    parser.add_argument("--source-gcs", required=True, help="GCS URI of source tarball uploaded for worker bootstrap.")
    parser.add_argument("--daic-root", required=True, help="GCS URI of DAIC transcript root.")
    parser.add_argument("--init-adapter", required=True, help="GCS URI of initial adapter directory.")
    parser.add_argument("--output-root", required=True, help="GCS URI where outputs/reports should be uploaded.")
    parser.add_argument("--machine-type", default=DEFAULT_MACHINE_TYPE)
    parser.add_argument("--accelerator-type", default=DEFAULT_ACCELERATOR_TYPE)
    parser.add_argument("--accelerator-count", type=int, default=DEFAULT_ACCELERATOR_COUNT)
    parser.add_argument("--image-uri", default=DEFAULT_IMAGE_URI)
    parser.add_argument(
        "--scheduling-strategy",
        default="STANDARD",
        choices=["STANDARD", "SPOT"],
        help="Vertex scheduling strategy. Use SPOT to run on Spot VMs.",
    )
    parser.add_argument("--extractor-model", default=DEFAULT_EXTRACTOR_MODEL)
    parser.add_argument("--extractor-epochs", type=int, default=1)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--hf-token", default=None, help="Optional HF token for gated base models.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip remote GCS object checks before submit.")
    parser.add_argument("--gcloud-bin", default=None, help="Optional gcloud binary path.")
    return parser.parse_args()


def resolve_gcloud_bin(explicit: str | None) -> str:
    if explicit:
        return explicit
    found = shutil.which("gcloud")
    if found:
        return found
    if os.path.exists(DEFAULT_GCLOUD_BIN):
        return DEFAULT_GCLOUD_BIN
    raise FileNotFoundError("Unable to find gcloud binary. Pass --gcloud-bin explicitly.")


def get_access_token(gcloud_bin: str) -> str:
    token = subprocess.check_output([gcloud_bin, "auth", "print-access-token"], text=True).strip()
    if not token:
        raise RuntimeError("gcloud returned an empty access token.")
    return token


def resolve_gsutil_bin(gcloud_bin: str) -> str:
    candidate = str(Path(gcloud_bin).with_name("gsutil"))
    if os.path.exists(candidate):
        return candidate
    found = shutil.which("gsutil")
    if found:
        return found
    raise FileNotFoundError("Unable to find gsutil binary for GCS preflight checks.")


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_hf_token(explicit: str | None) -> str | None:
    if explicit:
        return explicit.strip() or None

    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value.strip()

    merged: dict[str, str] = {}
    for path in (Path.cwd() / ".env.local", Path.cwd() / ".env"):
        merged.update(_parse_dotenv_file(path))
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        value = merged.get(key)
        if value:
            return value.strip()
    return None


def requires_hf_token(model_name: str) -> bool:
    lowered = model_name.lower()
    return "aya-expanse" in lowered or lowered.startswith("coherelabs/aya")


def assert_gcs_exists(gsutil_bin: str, uri: str) -> None:
    result = subprocess.run(
        [gsutil_bin, "ls", uri],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "Unknown gsutil error"
        raise FileNotFoundError(f"GCS check failed for {uri}: {detail}")


def run_preflight_checks(args: argparse.Namespace, gcloud_bin: str) -> None:
    if args.skip_preflight:
        return
    gsutil_bin = resolve_gsutil_bin(gcloud_bin)
    assert_gcs_exists(gsutil_bin, args.source_gcs)
    assert_gcs_exists(gsutil_bin, args.init_adapter)
    daic_probe = args.daic_root.rstrip("/") + "/"
    assert_gcs_exists(gsutil_bin, daic_probe)


def build_bootstrap_script(args: argparse.Namespace) -> str:
    deps = " ".join(PIP_DEPENDENCIES)
    return f"""set -euo pipefail
python -m pip install --upgrade pip
python -m pip install {deps}
python - <<'PY2'
from google.cloud import storage
uri = "{args.source_gcs}"
bucket, blob = uri[5:].split("/", 1)
storage.Client().bucket(bucket).blob(blob).download_to_filename("/tmp/manovarta_source.tgz")
PY2
mkdir -p /tmp/manovarta_src
cd /tmp/manovarta_src
tar -xzf /tmp/manovarta_source.tgz
python tools/vertex_aya_continue_worker.py --device cuda --daic-root {args.daic_root} --init-adapter {args.init_adapter} --gcs-output-root {args.output_root} --extractor-model {args.extractor_model} --extractor-epochs {args.extractor_epochs} --extractor-batch-size {args.extractor_batch_size} --extractor-grad-accum {args.extractor_grad_accum} --extractor-max-length {args.extractor_max_length} --extractor-save-steps {args.extractor_save_steps} --extractor-max-new-tokens {args.extractor_max_new_tokens} --smoke-limit {args.smoke_limit}
"""


def build_payload(args: argparse.Namespace, display_name: str, hf_token: str | None) -> dict:
    bootstrap_script = build_bootstrap_script(args)
    container_spec: dict[str, object] = {
        "imageUri": args.image_uri,
        "command": ["bash", "-lc"],
        "args": [bootstrap_script],
    }
    if hf_token:
        container_spec["env"] = [
            {"name": "HF_TOKEN", "value": hf_token},
            {"name": "HUGGING_FACE_HUB_TOKEN", "value": hf_token},
            {"name": "HUGGINGFACE_HUB_TOKEN", "value": hf_token},
        ]
    return {
        "displayName": display_name,
        "jobSpec": {
            "scheduling": {
                "strategy": args.scheduling_strategy,
            },
            "workerPoolSpecs": [
                {
                    "machineSpec": {
                        "machineType": args.machine_type,
                        "acceleratorType": args.accelerator_type,
                        "acceleratorCount": args.accelerator_count,
                    },
                    "replicaCount": "1",
                    "containerSpec": container_spec,
                }
            ]
        },
    }


def submit_job(args: argparse.Namespace, payload: dict, token: str) -> dict:
    endpoint = (
        f"https://{args.location}-aiplatform.googleapis.com/v1/projects/"
        f"{args.project}/locations/{args.location}/customJobs"
    )
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def main() -> int:
    args = parse_args()
    display_name = args.display_name or f"manovarta-qwen-daic-rest-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    gcloud_bin = resolve_gcloud_bin(args.gcloud_bin)
    hf_token = resolve_hf_token(args.hf_token)

    if requires_hf_token(args.extractor_model) and not hf_token:
        print(
            "Missing Hugging Face token for gated model access. Set HF_TOKEN (or pass --hf-token) before submitting Aya jobs.",
            file=sys.stderr,
        )
        return 1

    try:
        run_preflight_checks(args, gcloud_bin)
        token = get_access_token(gcloud_bin)
        payload = build_payload(args, display_name, hf_token)
        response = submit_job(args, payload, token)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(detail, file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "project": args.project,
                "location": args.location,
                "display_name": display_name,
                "output_root": args.output_root,
                "resource_name": response.get("name"),
                "state": response.get("state"),
                "create_time": response.get("createTime"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
