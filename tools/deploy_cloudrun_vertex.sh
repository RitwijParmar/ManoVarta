#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-2281c357-4539-4bc6-b96}"
REGION="${REGION:-us-east4}"
SERVICE="${SERVICE:-manovarta-runtime}"
REPO="${REPO:-cloud-run-source-deploy}"
TAG="${TAG:-vertex-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${IMAGE_URI:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/manovarta-runtime:${TAG}}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-122722888597-compute@developer.gserviceaccount.com}"
VERTEX_PROJECT="${VERTEX_PROJECT:-${PROJECT_ID}}"
VERTEX_LOCATION="${VERTEX_LOCATION:-us-central1}"
CHAT_MODEL="${CHAT_MODEL:-gemini-2.5-flash}"
EXTRACTION_MODEL="${EXTRACTION_MODEL:-gemini-2.5-flash}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[build] image=${IMAGE_URI}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" gcloud builds submit "${ROOT}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --tag "${IMAGE_URI}"

echo "[deploy] service=${SERVICE}"
CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3}" gcloud run deploy "${SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE_URI}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --cpu 2 \
  --memory 4Gi \
  --concurrency 8 \
  --max-instances 3 \
  --min-instances 0 \
  --allow-unauthenticated \
  --set-env-vars "MANOVARTA_MODEL_PROVIDER=vertex,MANOVARTA_CHAT_PROVIDER=vertex,MANOVARTA_EXTRACTION_PROVIDER=vertex,MANOVARTA_SAFETY_PROVIDER=local,MANOVARTA_CHAT_MODEL=${CHAT_MODEL},MANOVARTA_EXTRACTION_MODEL=${EXTRACTION_MODEL},MANOVARTA_VERTEX_PROJECT=${VERTEX_PROJECT},MANOVARTA_VERTEX_LOCATION=${VERTEX_LOCATION},MANOVARTA_ASYNC_SCORING_ENABLED=true,MANOVARTA_ASYNC_SCORING_DIR=/app/artifacts/async_scoring,MANOVARTA_LOCAL_SAFETY_CHECKPOINT=/app/outputs/local_safety_boost/safety-indicbert-best-infer-fp16,MANOVARTA_LIVE_CHAT_LLM_ANALYSIS=true,MANOVARTA_LIVE_LLM_TURN_THRESHOLD=1"

echo "[done] image=${IMAGE_URI}"
