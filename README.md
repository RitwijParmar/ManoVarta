# ManoVarta

ManoVarta is a multilingual conversational screening system for mental-health check-ins. Instead of presenting PHQ-9 and GAD-7 as a rigid questionnaire, it runs a guided conversation, extracts symptom evidence from the dialogue, updates item-level scores, and routes safety-sensitive cases through a separate escalation path.

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

ManoVarta uses a controller-led stack:

1. The web client collects typed or spoken user input.
2. The API runtime maintains session state and exposes live endpoints.
3. The dialogue planner chooses the next topic and follow-up.
4. The scoring engine updates PHQ-9 / GAD-7 evidence state.
5. The safety stack checks for review or urgent risk.
6. Model backends generate live phrasing and structured extraction.

The important design decision is that the application owns the screening flow. The models help with phrasing, extraction, and scoring, but they do not control the full workflow end-to-end.

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
