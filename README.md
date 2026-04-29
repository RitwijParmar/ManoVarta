# ManoVarta

ManoVarta is a multilingual conversational screening system for mental health. Instead of administering PHQ-9 and GAD-7 as a rigid form, it conducts a guided dialogue, extracts symptom evidence from open-ended responses, assigns item-level questionnaire scores, tracks uncertainty, and routes safety-critical cases through a separate escalation path.

The project was built for the "Conversational AI Chatbot for Multilingual Mental Health Screening" assignment, with English and Hindi as the required languages and Hinglish treated as an additional real-world robustness condition.

ManoVarta is a research prototype and screening-support system. It is not a therapy product, not a diagnostic device, and not a replacement for licensed clinical care.

## Bilingual evidence datasets

To close assignment gaps around bilingual audio-backed evidence and item-level scoring coverage, the repo now includes a bilingual labeled-data workflow under `data/gold/`.

This includes:

- bilingual audio/transcript layout and registry
- annotation/adjudication templates and guidance
- importers for public English/Hindi audio-transcript sources
- a validator that blocks placeholder assets

Public-source research and import status are tracked in:

- `reports/public_dataset_sourcing_report_20260409.md`
- `tools/fetch_edaic_public.py`
- `tools/fetch_po_em_mhlcds.py`
- `tools/import_indicvoices_hindi_valid.py`
- `tools/import_edaic_english_public.py`

Current local status (from `python tools/validate_gold_dataset.py --strict --require-human-labels`):

- 60/60 sessions structurally complete (`30 en + 30 hi`)
- audio/transcript/metadata present for all sessions
- no placeholder metadata/transcripts/labels
- human annotator A/B/adjudicated files present for all sessions

Dataset interpretation caveat:

- `English` is the stronger labeled gold core, built from E-DAIC public interview transcripts/audio and extended in-repo with dual human PHQ-9/GAD-7 annotation plus adjudication.
- `Hindi` is a repurposed real-audio pilot set imported from IndicVoices and labeled in-repo with the same PHQ-9/GAD-7 workflow, but the source corpus is not a native mental-health screening interview dataset.
- `Hinglish` remains a robustness condition in seed/runtime evaluation, not a gold dataset split.

So the repo now has a complete bilingual labeled asset stack for the assignment: English is the stronger clinically matched gold core, while Hindi is a real-audio multilingual voice-extension pilot labeled in-repo through the allowed DSM-5-TR-aligned transcript-grading path. The Hindi side is still weaker as a source-matched benchmark than English E-DAIC, so it should be described as a repurposed pilot rather than a native Hindi screening corpus.

Human-label process controls now available:

- `python tools/validate_gold_dataset.py --strict --require-human-labels`
- `python tools/generate_reviewer_workflow_pack.py --annotator-a-capacity 8 --annotator-b-capacity 8 --adjudicator-capacity 6`
- `python tools/generate_gold_adjudication_report.py`

These produce:

- human-label gating in `reports/gold_dataset_status.json`
- reviewer A/B/adjudicator queues and day-wise batches in `reports/reviewer_workflow_pack.json`
- item-wise Cohen's kappa + conflict heatmap in `reports/gold_adjudication_status.json` and `data/gold/adjudication/`

Training/export now supports explicit corpus selection:

- `python tools/export_training_sets.py --source gold-core` for the English adjudicated gold core
- `python tools/export_training_sets.py --source gold` for English gold core plus the Hindi pilot voice-extension set
- `python tools/export_training_sets.py --source hybrid` for seed + English gold core + Hindi pilot

The default export path is now `hybrid`, so the supervised training pipeline is no longer seed-only.

AI-assisted completion snapshot is documented in:

- `reports/ai_assisted_completion_report_20260410.md`

## Current status

The final repository state is not just a notebook experiment. It includes:

- a FastAPI runtime for chat, transcript scoring, summaries, voice endpoints, and runtime inspection
- a Django admin/data layer for seed data, annotation workflow, and review support
- a controller / extractor split where the application owns steering, Vertex can power the live language layer, and Aya remains the specialized scorer
- a budget-safe deployment path that keeps the public runtime on CPU Cloud Run while moving heavy Aya scoring to an asynchronous worker
- a hybrid safety stack with rules plus a promoted local safety checkpoint
- patient-profile onboarding in the actual user flow
- browser voice plus backend speech-to-text and text-to-speech routes
- a final ACL-format report bundle in PDF, DOCX, and LaTeX
- a final project presentation deck in PPTX
- a clean phase submission zip with compact relevant weights included

Recommended final runtime split:

- `MANOVARTA_CHAT_PROVIDER=vertex` and `MANOVARTA_CHAT_MODEL=gemini-2.5-flash` for live multilingual replies
- `MANOVARTA_EXTRACTION_PROVIDER=remote`, `MANOVARTA_EXTRACTION_MODEL=trained-aya-remote`, and `MANOVARTA_REMOTE_EXTRACTION_URL=https://...` when you want live trained-Aya extraction behind the public runtime
- `MANOVARTA_EXTRACTION_PROVIDER=vertex` and `MANOVARTA_EXTRACTION_MODEL=gemini-2.5-flash` remain the cheaper fallback for real-time turn interpretation
- `tools/process_async_score_queue.py` on a separate worker with `MANOVARTA_EXTRACTION_PROVIDER=local`, `MANOVARTA_EXTRACTION_MODEL=/models/aya-expanse-8b`, and `MANOVARTA_LOCAL_EXTRACTION_ADAPTER=/models/aya_bundle` for checkpoint or end-of-session clinical scoring

In other words: the application logic remains the real controller, Gemini/Vertex supplies the live language layer, and trained Aya is preserved for the higher-value clinical scoring pass instead of burning budget on every turn.

## Final results

The metrics below come from the archived self-hosted local-inference benchmark that established the strongest held-out runtime quality before the budget-safe deployment pivot. The current low-cost production plan reuses the same controller logic and safety stack, but swaps the always-on live model path to Vertex/Gemini and keeps Aya for asynchronous scoring checkpoints.

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

## Deployment modes

Archived self-hosted deployment snapshot recorded in the report bundle:

- `https://manovarta-runtime-122722888597.us-east4.run.app`

That earlier deployment report described:

- `provider: local`
- `self_hosted_inference_enabled: true`
- `hybrid_safety_enabled: true`
- `local_safety_checkpoint_enabled: true`
- `speech_to_text_enabled: true`
- `text_to_speech_enabled: true`

Recommended low-cost production path now:

- public runtime: CPU Cloud Run service using our controller/state logic plus Vertex/Gemini for live replies and either Vertex or remote Aya for turn extraction
- live trained Aya option: dedicated GPU Cloud Run extractor service mounted on the staged Aya base model plus the trained `aya_bundle` adapter
- async scoring: queue-based Aya worker that drains `artifacts/async_scoring` or a shared bucket-backed queue and writes scored snapshots back to the app
- deployment helper for the public runtime: `tools/deploy_cloudrun_vertex.sh`
- deployment helper for the live trained Aya extractor: `tools/deploy_cloudrun_aya_extractor.sh`
- worker helper for trained Aya scoring: `tools/run_aya_async_worker.sh`
- async scoring API: `POST /screen/transcript/async`, `POST /chat/sessions/{session_id}/score_async`, `GET /screen/requests/{request_id}`

This split is the practical path when credits matter. It keeps the conversational layer online for weeks on CPU while still preserving the trained Aya artifact as the specialist scorer.

### Async Aya worker notes

The intended worker shape is:

- download the Aya base model on the worker host directly from Hugging Face
- mount or copy your trained adapter to `/models/aya_bundle`
- point `MANOVARTA_EXTRACTION_MODEL` at the base model path
- run `tools/run_aya_async_worker.sh --max-jobs 1` on demand or from a small loop

The worker uses the same queue directory structure as the API runtime, so the public service can enqueue jobs and the Aya worker can complete them later without keeping a GPU online all day.

## What the system does

At runtime, ManoVarta works as a structured conversational pipeline:

1. The user selects language and optionally enters profile context.
2. The application-side dialogue planner decides what topic needs to be covered next.
3. The live language model turns that state into the next natural question and can also help interpret the latest turn into structured state updates.
4. The scorer updates PHQ-9 and GAD-7 item state.
5. The runtime checks whether evidence is still insufficient and should trigger a follow-up question.
6. The safety stack separately checks for `none`, `review`, or `urgent` risk.
7. The async Aya worker can be triggered at high-value checkpoints to run a richer multilingual evidence extraction pass.
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
  - adaptive nudge deck with low-pressure choice prompts, compare prompts, intensity prompts, and topic-specific body/impact anchors
  - nudge feedback loop that promotes helpful prompt families and rotates away from unhelpful ones
- Linguistic personalization
  - style-aware follow-up shaping
  - gentler prompts for guarded users
  - smaller prompts for brief users
  - more open prompts for detailed users
  - code-mix awareness for Hinglish interactions
  - continuity-aware then-versus-now prompts when recent check-ins are available
  - autonomy-supportive wording that keeps burden low for guarded or fatigued users

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

Final demo videos:

- `reports/demo_assets/video/manovarta_linkedin_demo_v3.mp4`
- `reports/demo_assets/video/manovarta_linkedin_demo_v3.srt`
- `reports/demo_assets/video/manovarta_voice_mode_demo_v3.mp4`
- `reports/demo_assets/video/manovarta_voice_mode_demo_v3.srt`

## Repository layout

| Path | Purpose |
| --- | --- |
| `manovarta_core/` | FastAPI app, dialogue logic, extraction, scoring, safety, voice, schemas |
| `manovarta_admin/` | Django project config |
| `screening/` | Django app for profiles, conversations, evidence, and review |
| `data/seed/` | synthetic multilingual seed data |
| `data/gold/` | bilingual labeled evidence assets (English gold core + Hindi pilot audio set) |
| `data/processed/` | exported train/dev/test JSONL splits |
| `reports/` | evaluation bundles, runtime reports, final assignment reports |
| `reports/acl_paper/` | final paper, bibliography, figures, presentation |
| `reports/demo_assets/video/` | final LinkedIn demo and voice-mode demo assets |
| `outputs/` | saved model checkpoints and promoted runtime artifacts |
| `tools/` | evaluation and report-generation utilities still relevant to the final system |
| `tests/` | unit and runtime tests |

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
