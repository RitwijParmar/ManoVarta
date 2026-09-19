# ManoVarta

ManoVarta is a multilingual, agentic screening-support system for mental-health check-ins. Instead of presenting PHQ-9 and GAD-7 as a rigid questionnaire, it runs a guided conversation, extracts item-level evidence from the dialogue, updates evidence-bound scores, and routes safety-sensitive cases through a separate escalation path.

This repository contains the application code, training workflows, evaluation tests, and report source for the final project implementation.

## Current scope

- Languages: English and Hindi
- Additional robustness condition: Hinglish
- Screening targets: PHQ-9 and GAD-7
- Voice support: browser and cloud speech paths
- Safety support: separate review / urgent escalation logic

ManoVarta is a screening-support prototype. It is not a therapy product, not a diagnostic device, and not a replacement for licensed clinical care.

## Repository layout

- `manovarta_core/`
  - FastAPI runtime
  - dialogue planner
  - scoring engine
  - safety logic
  - frontend assets
- `manovarta_admin/`
  - Django admin-side project files
- `screening/`
  - data/admin models and management utilities
- `data/`
  - seed, gold, and processed datasets
- `training/`
  - training and evaluation entry points
- `tests/`
  - automated regression coverage
- `tools/`
  - export, deployment, reporting, and utility scripts
- `reports/acl_paper/`
  - final paper source bundle
- `docs/`
  - architecture, deployment, data/training, and testing notes

## Architecture summary

ManoVarta uses a controller-led multi-agent stack. The agents are bounded workflow roles, not autonomous clinical actors:

1. **Safety Guardian** independently checks rules and safety-model signals and can pause the workflow.
2. **Evidence Analyst** builds typed PHQ-9/GAD-7 evidence spans; it does not diagnose.
3. **Dialogue Supervisor** chooses a constrained next question from the controller state.
4. **Response Editor** may phrase only an approved response; urgent cases use a fixed crisis protocol instead of free-form generation.
5. **Human handoff** is required for urgent signals. No agent can clear an urgent flag, write to a health record, prescribe, or diagnose.

Each chat response includes an auditable `agent_run` handoff trace. The application owns the screening flow; models help with phrasing and extraction but do not control the workflow end-to-end.

More detail:

- [docs/architecture.md](docs/architecture.md)

## Current live deployment

Public app:

- [manovarta-runtime-ciiiagnzaq-uk.a.run.app](https://manovarta-runtime-ciiiagnzaq-uk.a.run.app)

Current live split:

- live reply: `gemini-3-flash-preview`
- live analysis: `gemini-3-pro-preview`
- extraction: remote trained Aya
- safety: local checkpoint + rules

Useful runtime endpoints:

- [health](https://manovarta-runtime-ciiiagnzaq-uk.a.run.app/health)
- [runtime/config](https://manovarta-runtime-ciiiagnzaq-uk.a.run.app/runtime/config)

More detail:

- [docs/deployment.md](docs/deployment.md)

## Production safety and privacy controls

- Session IDs use 128-bit randomness, with an HttpOnly, secure session capability cookie required for turns, summaries, and exports.
- Sessions expire after 30 minutes and the public Cloud Run service uses one concurrent request per instance to avoid split in-memory conversation state.
- Public batch-scoring, runtime diagnostics, seed profiles, and presenter tools are operator-only in production.
- Input and audio uploads are bounded; public expensive routes have process-local rate limits. Cloud Armor or an API gateway should add fleet-wide rate limits before a real rollout.
- The public deployment uses Vertex extraction. The optional remote Aya extractor is intentionally not used until it has service-to-service authentication.
- For an urgent safety signal, the screening flow stops and gives immediate local-emergency guidance plus U.S. 988 and India Tele-MANAS resources. This is a routing protocol, not an emergency response service.

The production runtime is intentionally ephemeral: it does not retain conversations across a Cloud Run restart. This reduces data retention but means it is not a clinical record system.

## Data and training

The repository uses a layered data setup:

- `data/seed/` for seed supervision and compact runtime data
- `data/gold/` for bilingual gold packets and adjudication material
- `data/processed/` for exported training/evaluation files

Training was split across:

- Google Colab for compact fine-tuning and fast iteration
- GCP / Vertex AI for Aya continuation training

More detail:

- [docs/data-and-training.md](docs/data-and-training.md)
- [training/README.md](training/README.md)

## Running locally

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[runtime-cloud]
```

Start the runtime:

```bash
uvicorn manovarta_core.api:app --reload
```

Open the web client at:

- `http://127.0.0.1:8000`

## Testing

Common focused runs:

```bash
python3 -m pytest -q tests/test_dialogue.py
python3 -m pytest -q tests/test_api.py
python3 -m pytest -q tests/test_llm.py
```

More detail:

- [docs/testing.md](docs/testing.md)

## Final project sources

The repository keeps final source material, not every generated submission artifact.

- final paper source: `reports/acl_paper/`
- code and tests: top-level application folders
- deployment utilities: `tools/`

Generated submission zips, demo renders, and temporary packaging folders are intentionally kept out of git so the repository stays reviewable.
