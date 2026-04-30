# Deployment

## Public runtime

The public ManoVarta app is deployed on Cloud Run:

- [manovarta-runtime-ciiiagnzaq-uk.a.run.app](https://manovarta-runtime-ciiiagnzaq-uk.a.run.app)

## Current deployment split

- Conversation / live reply: Vertex Gemini
- Live analysis: Vertex Gemini
- Structured extraction: remote trained Aya
- Safety: local checkpoint + rules

## Important scripts

- `tools/deploy_cloudrun_vertex.sh`
  - Public runtime deployment
- `tools/deploy_cloudrun_aya_extractor.sh`
  - Remote Aya extractor deployment
- `tools/run_aya_async_worker.sh`
  - Async scoring worker flow

## Runtime inspection

- `/health`
- `/runtime/config`

These endpoints are useful for confirming the live stack before and after deployment.

## Deployment rule

For stable public behavior, keep the model / extractor configuration fixed and treat planner changes separately from infrastructure changes.
