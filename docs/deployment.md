# Deployment

## Public runtime

The public ManoVarta app is deployed on Cloud Run:

- [manovarta-runtime-ciiiagnzaq-uk.a.run.app](https://manovarta-runtime-ciiiagnzaq-uk.a.run.app)

## Current deployment split

- Conversation / live reply: Vertex Gemini
- Live analysis: Vertex Gemini
- Structured extraction: Vertex Gemini in the public runtime
- Safety: local checkpoint + rules

## Important scripts

- `tools/provision_cloudrun_security.sh`
  - creates the dedicated runtime service account, binds only Vertex/model-bucket/secret access, and creates the operator secret without printing it
- `tools/deploy_cloudrun_vertex.sh`
  - builds and deploys the hardened public runtime
- `tools/deploy_cloudrun_aya_extractor.sh`
  - Remote Aya extractor deployment
- `tools/run_aya_async_worker.sh`
  - Async scoring worker flow

## Runtime inspection

- `/health`

`/runtime/config`, seed profiles, presenter tooling, batch scoring, and agent architecture details require the `X-Manovarta-Admin-Key` value held in Secret Manager. They are not public endpoints.

These endpoints are useful for confirming the live stack before and after deployment.

## Hardened public deployment

```bash
export CLOUDSDK_PYTHON="$(command -v python3)"
export PROJECT_ID="project-2281c357-4539-4bc6-b96"
export REGION="us-east4"
./tools/provision_cloudrun_security.sh
./tools/deploy_cloudrun_vertex.sh
```

The deploy script runs the public service with a dedicated service account, one concurrent request, one maximum instance, an HttpOnly session capability cookie, a 30-minute session TTL, no public demo seed data, no public batch scoring, and a Secret Manager-backed operator key.

The public service deliberately disables filesystem-backed asynchronous scoring. A real asynchronous path needs a durable, authenticated queue and a separate worker rather than the Cloud Run container filesystem.

## Safety resources

The urgent handoff copy is verified against the [988 Lifeline](https://988lifeline.org/get-help/) for the U.S. and territories, and India's [National Mental Health Programme / Tele-MANAS](https://www.dghs.mohfw.gov.in/national-mental-health-programme.php) for 14416 and 1-800-891-4416. The app instructs a user in immediate danger to contact local emergency services or go to the nearest emergency department.

## Deployment rule

For stable public behavior, keep the model / extractor configuration fixed and treat planner changes separately from infrastructure changes.
