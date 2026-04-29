#!/usr/bin/env bash
set -euo pipefail

GCLOUD_BIN="${GCLOUD_BIN:-}"
if [[ -z "${GCLOUD_BIN}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    GCLOUD_BIN="$(command -v gcloud)"
  elif [[ -x "${HOME}/google-cloud-sdk/bin/gcloud" ]]; then
    GCLOUD_BIN="${HOME}/google-cloud-sdk/bin/gcloud"
  else
    echo "gcloud not found on PATH or at ${HOME}/google-cloud-sdk/bin/gcloud" >&2
    exit 1
  fi
fi

PROJECT_ID="${PROJECT_ID:-project-2281c357-4539-4bc6-b96}"
REGION="${REGION:-us-east4}"
SERVICE="${SERVICE:-manovarta-aya-extractor}"
BUCKET="${BUCKET:-project-2281c357-4539-4bc6-b96-us-east4-vertex}"
REPO="${REPO:-cloud-run-source-deploy}"
TAG="${TAG:-aya-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${IMAGE_URI:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/manovarta-aya-extractor:${TAG}}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-122722888597-compute@developer.gserviceaccount.com}"
VERTEX_PROJECT="${VERTEX_PROJECT:-${PROJECT_ID}}"
VERTEX_LOCATION="${VERTEX_LOCATION:-us-central1}"
EXTRACTION_MODEL="${EXTRACTION_MODEL:-/mnt/models/manovarta/runtime-models/aya-expanse-8b}"
LOCAL_EXTRACTION_ADAPTER="${LOCAL_EXTRACTION_ADAPTER:-/mnt/models/manovarta/runtime-models/aya_bundle}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STAGING_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${STAGING_DIR}"
}
trap cleanup EXIT

cp "${ROOT}/pyproject.toml" "${STAGING_DIR}/"
cp "${ROOT}/README.md" "${STAGING_DIR}/"
cp "${ROOT}/Dockerfile.cloudrun-aya" "${STAGING_DIR}/"
cp "${ROOT}/cloudbuild.cloudrun-aya.yaml" "${STAGING_DIR}/"
cp -R "${ROOT}/manovarta_core" "${STAGING_DIR}/"

echo "[build] image=${IMAGE_URI}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" "${GCLOUD_BIN}" builds submit "${STAGING_DIR}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --config "${STAGING_DIR}/cloudbuild.cloudrun-aya.yaml" \
  --substitutions "_IMAGE_URI=${IMAGE_URI}"

echo "[deploy] service=${SERVICE}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" "${GCLOUD_BIN}" run deploy "${SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE_URI}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --execution-environment gen2 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --cpu 8 \
  --memory 32Gi \
  --timeout 900 \
  --concurrency 1 \
  --max-instances 1 \
  --min-instances 0 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --add-volume name=models,type=cloud-storage,bucket="${BUCKET}",readonly=true,mount-options="implicit-dirs" \
  --add-volume-mount volume=models,mount-path=/mnt/models \
  --set-secrets "HF_TOKEN=hf-token:latest" \
  --set-env-vars "MANOVARTA_MODEL_PROVIDER=local,MANOVARTA_CHAT_PROVIDER=vertex,MANOVARTA_EXTRACTION_PROVIDER=local,MANOVARTA_SAFETY_PROVIDER=local,MANOVARTA_CHAT_MODEL=gemini-2.5-flash,MANOVARTA_EXTRACTION_MODEL=${EXTRACTION_MODEL},MANOVARTA_LOCAL_EXTRACTION_ADAPTER=${LOCAL_EXTRACTION_ADAPTER},MANOVARTA_LOCAL_LOAD_IN_4BIT=true,MANOVARTA_VERTEX_PROJECT=${VERTEX_PROJECT},MANOVARTA_VERTEX_LOCATION=${VERTEX_LOCATION},MANOVARTA_LIVE_CHAT_LLM_ANALYSIS=false,MANOVARTA_ASYNC_SCORING_ENABLED=false,MANOVARTA_LOCAL_SAFETY_CHECKPOINT="

echo "[done] image=${IMAGE_URI}"
