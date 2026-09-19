#!/usr/bin/env bash
set -euo pipefail

GCLOUD_BIN="${GCLOUD_BIN:-$(command -v gcloud)}"
PROJECT_ID="${PROJECT_ID:-project-2281c357-4539-4bc6-b96}"
BUCKET="${BUCKET:-${PROJECT_ID}-us-east4-vertex}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-manovarta-runtime}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SECRET_NAME="${INTERNAL_API_KEY_SECRET:-manovarta-internal-api-key}"

if ! "${GCLOUD_BIN}" iam service-accounts describe "${SERVICE_ACCOUNT}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  "${GCLOUD_BIN}" iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project "${PROJECT_ID}" \
    --display-name "ManoVarta Cloud Run runtime"
fi

"${GCLOUD_BIN}" projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role "roles/aiplatform.user" \
  --quiet
"${GCLOUD_BIN}" storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role "roles/storage.objectViewer" \
  --quiet

if ! "${GCLOUD_BIN}" secrets describe "${SECRET_NAME}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  python3 -c 'import secrets; print(secrets.token_urlsafe(48))' | "${GCLOUD_BIN}" secrets create "${SECRET_NAME}" \
    --project "${PROJECT_ID}" \
    --replication-policy automatic \
    --data-file -
fi

"${GCLOUD_BIN}" secrets add-iam-policy-binding "${SECRET_NAME}" \
  --project "${PROJECT_ID}" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role "roles/secretmanager.secretAccessor" \
  --quiet

echo "Provisioned ${SERVICE_ACCOUNT} with Vertex, model-bucket, and internal-secret access."
