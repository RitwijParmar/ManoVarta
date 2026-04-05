# ManoVarta

ManoVarta is a multilingual conversational screening system for mental health. Instead of administering PHQ-9 and GAD-7 as a rigid form, it conducts a guided dialogue, extracts symptom evidence from open-ended responses, assigns item-level questionnaire scores, tracks uncertainty, and routes safety-critical cases through a separate escalation path.

The project was built for the "Conversational AI Chatbot for Multilingual Mental Health Screening" assignment, with English and Hindi as the required languages and Hinglish treated as an additional real-world robustness condition.

ManoVarta is a research prototype and screening-support system. It is not a therapy product, not a diagnostic device, and not a replacement for licensed clinical care.

## Current status

The final repository state is not just a notebook experiment. It includes:

- a FastAPI runtime for chat, transcript scoring, summaries, voice endpoints, and runtime inspection
- a Django admin/data layer for seed data, annotation workflow, and review support
- self-hosted local inference for the deployed runtime
- a hybrid safety stack with rules plus a promoted local safety checkpoint
- patient-profile onboarding in the actual user flow
- browser voice plus backend speech-to-text and text-to-speech routes
- a final ACL-format report bundle in PDF, DOCX, and LaTeX
- a final project presentation deck in PPTX
- a clean phase submission zip with compact relevant weights included

## Final results

Final live runtime metrics from `reports/live_runtime_eval_20260404.json`:

| Metric | Value |
| --- | --- |
| Coverage completeness | `0.783` |
| Exact match rate | `0.639` |
| Macro-F1 | `0.251` |
| MAE | `0.424` |
| Safety precision | `1.000` |
| Safety recall | `1.000` |
| Parse failures | `0` |

Language-wise live runtime breakdown:

| Language | Coverage | Exact | Macro-F1 | MAE |
| --- | --- | --- | --- | --- |
| English | `0.844` | `0.667` | `0.239` | `0.370` |
| Hindi | `0.719` | `0.609` | `0.242` | `0.435` |
| Hinglish | `0.786` | `0.636` | `0.232` | `0.477` |

Assignment-aligned evaluation from `reports/final_assignment_completion_report.json`:

- Disclosure Efficiency: average `2.292` user turns to a stable item score
- Safety Accuracy: precision `1.0`, recall `1.0`, F1 `1.0`
- Latency: cold start `937.69 ms`, warm median `32.73 ms`, warm p95 `32.89 ms`
- Discourse Effectiveness: coverage `0.783`, exact `0.639`, macro-F1 `0.251`, parse failures `0`

## Live deployment

The final public runtime URL recorded in the current report bundle is:

- `https://manovarta-runtime-122722888597.us-east4.run.app`

The live deployment report currently describes:

- `provider: local`
- `self_hosted_inference_enabled: true`
- `hybrid_safety_enabled: true`
- `local_safety_checkpoint_enabled: true`
- `speech_to_text_enabled: true`
- `text_to_speech_enabled: true`

## What the system does

At runtime, ManoVarta works as a structured conversational pipeline:

1. The user selects language and optionally enters profile context.
2. The dialogue planner decides what topic needs to be covered next.
3. The extractor pulls questionnaire-aligned evidence from the conversation.
4. The scorer updates PHQ-9 and GAD-7 item state.
5. The runtime checks whether evidence is still insufficient and should trigger a follow-up question.
6. The safety stack separately checks for `none`, `review`, or `urgent` risk.
7. The response generator turns the current screening state into the next natural question.
8. The voice layer optionally handles microphone input and spoken replies.

This separation was one of the main project findings. Direct prompting alone was not enough. The strongest improvements came from:

- evidence-first extraction instead of raw transcript scoring
- separate safety fusion instead of trusting the main conversational model
- coverage-aware planning instead of a fixed questionnaire order
- language-sensitive lexical and verifier passes
- targeted post-hoc calibration instead of one more generic retrain

## Why Aya was chosen for extraction

The extractor decision was based on measured behavior, not model branding.

Important checkpoints in the project:

| System | Coverage | Exact | Macro-F1 | Notes |
| --- | --- | --- | --- | --- |
| Heuristic seed runtime | `0.022` | `0.635` | `0.058` | misleadingly sparse |
| Early raw Aya scoring check | `0.009` | `0.400` | `0.006` | fluent but clinically silent |
| Local Qwen2.5-1.5B probe | `0.429` | `0.667` | `0.129` | saved probe, Hindi brittle |
| Retrospective Llama 3.1 8B probe | `0.893` | `0.640` | `0.190` | good tiny-slice coverage, still worse than Aya on macro-F1 and safety behavior |
| Aya offline extractor baseline | `0.913` | `0.562` | `0.272` | first strong archived multilingual extractor result |
| Final live runtime | `0.783` | `0.639` | `0.251` | deployment-ready, safe default |

Interpretation:

- Qwen was useful as an early compact-model path, but the saved probe was too brittle to justify multilingual extractor selection.
- Llama 3.1 8B was tested later through a real local MLX 4-bit probe and looked stronger than Qwen on a tiny multilingual slice, but it still did not beat the archived Aya extractor on the main held-out comparison and over-escalated safety on benign examples.
- Aya remained the best extractor backbone because it was the first model family in the project to produce a strong archived multilingual evaluation.
- The final deployed runtime later moved to self-hosted local inference for productization, but the extractor design decisions were still driven by the Aya result path.

## Safety design

Safety is handled separately from ordinary item scoring.

The runtime combines:

- rule-based safety monitoring
- a promoted local safety checkpoint
- runtime corroboration logic to reduce false positives

This separation mattered. The project initially had a stronger raw extractor than a safe deployed system. Later calibration made the runtime much safer without collapsing back into useless abstention.

Current safety result:

- final live runtime safety precision `1.0`
- final live runtime safety recall `1.0`

## Bonus features implemented

Both bonus features were implemented in the final product:

- Gamification
  - interactive confidence boosters
  - guided first-line prompts
  - adaptive nudges that encourage more descriptive disclosure
- Linguistic personalization
  - style-aware follow-up shaping
  - gentler prompts for guarded users
  - smaller prompts for brief users
  - more open prompts for detailed users
  - code-mix awareness for Hinglish interactions

## Voice support

The final system is more than a browser-only speech demo.

Voice stack:

- browser speech recognition and speech synthesis when available
- backend `/voice/transcribe`
- backend `/voice/speak`
- cloud STT/TTS support in deployment

Current state:

- good enough for the project brief
- not yet a fully streaming duplex phone-call product

That means:

- microphone input works in the browser flow
- spoken replies can be generated through the backend
- continuous voice mode exists
- but this is still a product prototype, not a production telephony stack

## Saved weights and model artifacts

Important saved artifacts in this repo:

### Final compact extractor artifacts

- `outputs/local_mps/extractor-qwen25-1_5b-best-compact/`

This directory contains:

- `adapter_model.safetensors`
- tokenizer files
- adapter config
- compact training outputs kept for reproducibility

### Final promoted safety inference checkpoint

- `outputs/local_safety_boost/safety-indicbert-best-infer-fp16/`

This directory contains the promoted inference-only safety checkpoint used in the final hybrid runtime path.

### Additional experiment notes

The detailed Qwen, Granite, and Llama comparison results are summarized in the final paper bundle rather than kept as separate top-level report clutter. They should be interpreted as small retrospective probes, not full held-out multilingual benchmarks.

## Final report and presentation

Final report assets:

- `reports/acl_paper/project2_acl_report.pdf`
- `reports/acl_paper/project2_acl_report.docx`
- `reports/acl_paper/project2_acl_report.tex`
- `reports/acl_paper/project2_acl_report.bib`

Final presentation:

- `reports/acl_paper/project2_presentation.pptx`

Supporting report bundle:

- `reports/final_assignment_completion_report.md`
- `reports/final_assignment_completion_report.json`
- `reports/best_current_system_report.md`
- `reports/best_current_system_report.json`
- `reports/live_runtime_eval_20260404.json`

## Clean submission bundle

A cleaned phase submission bundle is prepared at:

- `submission/ProjectPhase3_UBid1_UBid2.zip`

This bundle includes:

- working code
- tests
- seed and processed data
- final PDF report
- final DOCX report
- final PPTX presentation
- key evaluation artifacts
- compact relevant saved weights

This bundle intentionally excludes:

- `.env.local`
- `.venv`
- `.DS_Store`
- `__pycache__`
- `data/external/`
- giant historical zip bundles under `artifacts/`
- unnecessary intermediate checkpoints

If you want to rebuild the presentation or submission package:

```bash
python3 tools/build_project2_presentation.py
python3 tools/build_phase3_submission_bundle.py
```

## Repository layout

| Path | Purpose |
| --- | --- |
| `manovarta_core/` | FastAPI app, dialogue logic, extraction, scoring, safety, voice, schemas |
| `manovarta_admin/` | Django project config |
| `screening/` | Django app for profiles, conversations, evidence, and review |
| `data/seed/` | synthetic multilingual seed data |
| `data/processed/` | exported train/dev/test JSONL splits |
| `reports/` | evaluation bundles, runtime reports, final assignment reports |
| `reports/acl_paper/` | final paper, bibliography, figures, presentation |
| `outputs/` | saved model checkpoints and promoted runtime artifacts |
| `tools/` | training, evaluation, packaging, and presentation scripts |
| `tests/` | unit and runtime tests |
| `submission/` | cleaned final submission bundle |

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run the API locally

```bash
source .venv/bin/activate
uvicorn manovarta_core.api:app --reload
```

Useful endpoints:

- `/`
- `/health`
- `/runtime/config`
- `/chat/sessions`
- `/chat/turn`
- `/screen/transcript`
- `/voice/transcribe`
- `/voice/speak`
- `/knowledge/base`

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

## Data generation and export

Seed-data utilities:

```bash
python tools/generate_seed_scaleup.py
python tools/generate_seed_nuance_pack.py
python tools/generate_seed_silver_variants.py
python tools/dataset_stats.py
python tools/validate_seed_data.py
```

Training/export utilities:

```bash
python tools/create_data_splits.py
python tools/export_training_sets.py
```

This writes the extractor, follow-up, and safety training sets under `data/processed/`.

## Evaluation utilities

Heuristic and hosted-LLM comparison:

```bash
python tools/evaluate_seed_runtime.py --mode heuristic
python tools/evaluate_seed_runtime.py --mode llm
python tools/compare_llm_baselines.py
```

Runtime and report generation:

```bash
python tools/generate_best_current_system_report.py
python tools/generate_assignment_completion_report.py
python tools/generate_acl_report_figures.py
python tools/build_acl_report_artifacts.py
```

## Deployment

Deployment assets included in the repo:

- `Dockerfile`
- `docker-compose.demo.yml`
- `render.yaml`

Local container demo:

```bash
docker compose -f docker-compose.demo.yml up --build
```

## Rebuilding the current project artifacts

```bash
python3 tools/build_project2_presentation.py
python3 tools/build_phase3_submission_bundle.py
python3 tools/build_acl_report_artifacts.py
```

## Important limitations

This repo is honest about what is done and what is still limited.

- The system is a research prototype, not a clinically validated product.
- The seed corpus is still synthetic and relatively small.
- Hindi is currently the weakest final language slice.
- Voice is real, but not yet a streaming duplex telephony product.
- Some planning-stage models, such as Gemma and Mistral, were discussed during development, but there is no reproducible final archived held-out result for them in the repo.
- The Qwen and Llama probe artifacts are small comparison probes, not full end-to-end benchmarks.

## Safety and ethics note

ManoVarta is intended for research and educational screening support only.

- It should not be used as a diagnostic authority.
- It should not be used as a substitute for emergency or licensed mental-health care.
- Human review remains mandatory for real high-risk settings.

If you are adapting this code for real-world use, privacy, consent, clinical review, and safety escalation design must be treated as first-class requirements rather than post-processing details.
