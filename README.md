# ManoVarta

ManoVarta is a text-first multilingual screening prototype for English, Hindi, and limited Hinglish conversations. The project is designed around PHQ-9 and GAD-7 style item inference, evidence spans, confidence tracking, and a separate safety pass.

The current repository includes two layers:

- `FastAPI` runtime endpoints for chat, transcript scoring, and summary generation
- `Django` admin models for seed data, review workflow, and annotation support
- optional `Hugging Face` responder path for live chat drafting when `HF_TOKEN` is configured

The goal is a credible research prototype, not a therapy product or diagnostic system.

## Project layout

| Path | Purpose |
| --- | --- |
| `manovarta_core/` | shared screening logic, schemas, safety, dialogue, and FastAPI app |
| `manovarta_admin/` | Django project configuration |
| `screening/` | Django app for profiles, conversations, evidence, and reviews |
| `data/seed/` | seed profiles and conversations for local testing |
| `tests/` | API and scoring tests |
| `README_phase1.md` | proposal and Milestone 1 package summary |
| `tools/demo_cli.py` | terminal demo loop using the same runtime logic |

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run the API

```bash
source .venv/bin/activate
uvicorn manovarta_core.api:app --reload
```

## Run Django admin

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Load seed data

```bash
source .venv/bin/activate
python manage.py load_seed_data
python manage.py rebuild_snapshots
```

## Run tests

```bash
source .venv/bin/activate
pytest
```

## Optional Hugging Face hookup

If you want live response drafting through Hugging Face Inference Providers, set:

```bash
export HF_TOKEN=...
export MANOVARTA_CHAT_MODEL=mistralai/Mistral-Nemo-Instruct-2407
```

Then verify auth with:

```bash
python tools/hf_smoketest.py
```

## Notes

- Large-model hosting is intentionally left out of this repository.
- Voice can be added later as a speech wrapper over the text pipeline.
- Seed data is synthetic and should be treated as pilot material only.
