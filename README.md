# ManoVarta

ManoVarta is a text-first multilingual screening prototype for English, Hindi, and limited Hinglish conversations. The project is designed around PHQ-9 and GAD-7 style item inference, evidence spans, confidence tracking, and a separate safety pass.

The current repository includes two layers:

- `FastAPI` runtime endpoints for chat, transcript scoring, and summary generation
- `Django` admin models for seed data, review workflow, and annotation support
- optional `Hugging Face` responder path for live chat drafting when `HF_TOKEN` is configured
- Colab-ready training scripts for extractor and safety fine-tuning

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

## Seed-data utilities

```bash
python tools/dataset_stats.py
python tools/validate_seed_data.py
python tools/evaluate_seed_runtime.py --mode heuristic
```

If `HF_TOKEN` is set, you can also compare the current LLM extraction path:

```bash
python tools/evaluate_seed_runtime.py --mode llm
python tools/evaluate_seed_runtime.py --mode llm --model moonshotai/Kimi-K2-Instruct
python tools/compare_llm_baselines.py
```

## Annotation workflow helpers

```bash
python tools/build_annotation_packets.py
```

This exports a compact JSONL packet with transcript turns, metadata, and blank slots for a second annotation pass.

## Training data export

```bash
python tools/create_data_splits.py
python tools/export_training_sets.py
```

That prepares:

- extractor fine-tuning sets,
- follow-up generation sets,
- safety classification sets.

## Optional Hugging Face hookup

If you want live response drafting through Hugging Face Inference Providers, set:

```bash
export HF_TOKEN=...
export MANOVARTA_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
export MANOVARTA_EXTRACTION_MODEL=CohereLabs/aya-expanse-32b
```

You can also put the same values in a local `.env.local` file. It is ignored by git.

Then verify auth with:

```bash
python tools/hf_smoketest.py
```

The current default split is:

- chat/runtime drafting: `Qwen/Qwen2.5-7B-Instruct`
- structured extraction: `CohereLabs/aya-expanse-32b`

That split keeps latency reasonable while using the stronger multilingual model where it matters most.

If you want the optional semantic safety encoder in runtime, also set:

```bash
export MANOVARTA_SEMANTIC_SAFETY_MODEL=google/muril-base-cased
```

That path is optional and heavier, so it is best tested in Colab first.

## Optional Colab encoder work

If you want to test the Hindi-sensitive encoder path on GPU:

```bash
pip install -e .[gpu]
python tools/semantic_safety_eval.py --model google/muril-base-cased
```

There is also a Colab-specific walkthrough in `experiments/colab/README.md`.
Full fine-tuning commands live in `training/README.md`.
The ready-to-run notebook is `experiments/colab/manovarta_training_colab.ipynb`.

## Notes

- Large-model hosting is intentionally left out of this repository.
- Voice can be added later as a speech wrapper over the text pipeline.
- Seed data is synthetic and should be treated as pilot material only.
