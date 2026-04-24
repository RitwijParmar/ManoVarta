#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-2281c357-4539-4bc6-b96}"
REGION="${REGION:-us-east4}"
SERVICE="${SERVICE:-manovarta-runtime}"
BUCKET="${BUCKET:-project-2281c357-4539-4bc6-b96-us-east4-vertex}"
REPO="${REPO:-cloud-run-source-deploy}"
TAG="${TAG:-gpu-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${IMAGE_URI:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/manovarta-runtime:${TAG}}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-122722888597-compute@developer.gserviceaccount.com}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[build] image=${IMAGE_URI}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" gcloud builds submit "${ROOT}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --config "${ROOT}/cloudbuild.cloudrun-gpu.yaml" \
  --substitutions "_IMAGE_URI=${IMAGE_URI}"

echo "[deploy] service=${SERVICE}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" gcloud run deploy "${SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE_URI}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --execution-environment gen2 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --cpu 8 \
  --memory 32Gi \
  --concurrency 1 \
  --max-instances 1 \
  --min-instances 0 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --add-volume name=models,type=cloud-storage,bucket="${BUCKET}",readonly=true,mount-options="implicit-dirs" \
  --add-volume-mount volume=models,mount-path=/mnt/models \
  --set-env-vars "MANOVARTA_MODEL_PROVIDER=local,MANOVARTA_CHAT_MODEL=/models/qwen3-14b,MANOVARTA_EXTRACTION_MODEL=/mnt/models/manovarta/runtime-models/aya-expanse-8b,MANOVARTA_LOCAL_EXTRACTION_ADAPTER=/mnt/models/manovarta/runtime-models/aya_bundle,MANOVARTA_LOCAL_LOAD_IN_4BIT=true,MANOVARTA_LIVE_CHAT_LLM_ANALYSIS=true,MANOVARTA_LIVE_LLM_TURN_THRESHOLD=1,MANOVARTA_LOCAL_SAFETY_CHECKPOINT=/mnt/models/manovarta/runtime/safety-indicbert-best-infer-fp16"

echo "[done] image=${IMAGE_URI}"
