# ManoVarta

ManoVarta is a text-first multilingual screening prototype for English, Hindi, and limited Hinglish conversations. The project is designed around PHQ-9 and GAD-7 style item inference, evidence spans, confidence tracking, and a separate safety pass.

The current repository includes two layers:

- `FastAPI` runtime endpoints for chat, transcript scoring, and summary generation
- `Django` admin models for seed data, review workflow, and annotation support
- optional `Hugging Face` responder path for live chat drafting when `HF_TOKEN` is configured
- browser voice wrapper using speech recognition and speech synthesis when supported
- Colab-ready training scripts for extractor and safety fine-tuning
- Vertex AI submitter/worker scripts for Aya continuation training with DAIC-WOZ auxiliary supervision

The runtime now exposes an explicit coverage planner as part of the snapshot state. That planner tracks touched items, resolved items, abstained items, a follow-up queue, and a review queue so contradictory evidence is surfaced instead of being silently forced into a score.

The goal is a credible research prototype, not a therapy product or diagnostic system.

## Dataset snapshot

The checked-in synthetic annotated corpus now uses a `curated core + silver extension` design:

- `48` patient profiles
- `48` curated conversation records
- `132` silver conversation variants built from the curated core
- `180` total conversation records
- balanced language coverage: `60` English, `60` Hindi, `60` Hinglish
- review mix: `24` `consensus_final`, `24` `double_annotated`, `132` `draft`
- safety mix: `127` none, `37` review, `16` urgent
- nuance coverage that now includes guarded openings, deny-then-reveal cases, Hindi somatic phrasing, Hinglish code-mixing, passive disappearance language, contradiction-style disclosures, burden language, exam/work masking, caregiving stress, breakup narratives, and low-engagement short replies

The current processed split after export is:

- extractor: `84` train / `48` dev / `48` test
- follow-up: `120` train / `96` dev / `144` test
- safety: `84` train / `48` dev / `48` test

Everything is still synthetic pilot data, but it is now large enough to exercise the training and evaluation pipeline without the earlier tiny-sample bottleneck. The curated core is the higher-trust subset for careful review and error analysis; the silver layer is mainly there to improve robustness to conversational variation.

## Project layout

| Path | Purpose |
| --- | --- |
| `manovarta_core/` | shared screening logic, schemas, safety, dialogue, and FastAPI app |
| `manovarta_admin/` | Django project configuration |
| `screening/` | Django app for profiles, conversations, evidence, and reviews |
| `data/seed/` | seed profiles and conversations for local testing |
| `tests/` | API and scoring tests |
| `README_phase1.md` | proposal and Milestone 1 package summary |
| `data_nuance_strategy.md` | rationale for the curated core, silver variants, and nuance dimensions |
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

## Shipped baseline

The current shipped baseline is frozen at git tag `shipped-baseline-2026-04-04`.

It uses:

- chat/runtime drafting: `Qwen/Qwen2.5-7B-Instruct`
- structured extraction: `CohereLabs/aya-expanse-32b`
- safety: hybrid runtime with rule monitor plus an auto-discovered local checkpoint

The shipped reference docs are:

- `reports/ship_note_2026-04-04.md`
- `reports/best_current_system_report.md`

To package the lean shipped demo/submission bundle:

```bash
make ship-bundle
```

That writes:

- `artifacts/manovarta_shipped_baseline_20260404.zip`

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
python tools/generate_seed_scaleup.py
python tools/generate_seed_nuance_pack.py
python tools/generate_seed_silver_variants.py
python tools/dataset_stats.py
python tools/validate_seed_data.py
python tools/evaluate_seed_runtime.py --mode heuristic
```

The scale-up and nuance generators add harder disclosure patterns without overwriting the original curated packs. The silver-variant generator then produces additional guarded, minimizing, and self-correcting versions for robustness experiments.

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

For the extractor, the export now also writes a stronger train set:

- `extractor_train_best.jsonl`: compact-schema supervision with extra Hindi and Hinglish weighting
- `extractor_train_best_augmented_daic.jsonl`: same idea plus capped English `DAIC-WOZ` auxiliary data when `--daic-root` is provided

You can optionally add `DAIC-WOZ` as an auxiliary English-only extractor source:

```bash
python tools/fetch_daic_woz.py --output-dir data/external/DAIC-WOZ
# Optional: pull a small sample of train session zips.
python tools/fetch_daic_woz.py --output-dir data/external/DAIC-WOZ --session-split train --max-session-zips 5
python tools/export_training_sets.py --daic-root /path/to/DAIC-WOZ
```

The official DAIC-WOZ source index used by the helper script is:
`https://dcapswoz.ict.usc.edu/wwwdaicwoz/`

That writes:

- `extractor_daic_train.jsonl`
- `extractor_daic_dev.jsonl`
- `extractor_daic_test.jsonl`
- `extractor_train_augmented_daic.jsonl`

The DAIC export is intentionally kept separate from the main multilingual split. It is best used to improve English depression-item extraction, not to claim better Hindi or Hinglish coverage.

## How to improve Hindi and Hinglish

`DAIC-WOZ` helps mostly with English PHQ-style supervision. For Hindi and Hinglish, the higher-return path is:

- add more gold reviewed Hindi and Hinglish conversations, especially off-by-one severity cases
- add more code-mixed, guarded, somatic, and contradiction-heavy examples
- use Aya or Qwen as a teacher to draft Hindi and Hinglish variants, then manually review them
- keep the multilingual test split separate from any English-only auxiliary corpus

In other words: use `DAIC-WOZ` to sharpen the English extractor, but improve Hindi and Hinglish with targeted multilingual data rather than hoping an English interview corpus transfers cleanly.

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
export MANOVARTA_SEMANTIC_SAFETY_MODEL=ai4bharat/IndicBERTv2-MLM-only
```

That path is optional and heavier, so it is best tested in Colab first.

The runtime now also auto-discovers a promoted local safety checkpoint when either of these directories exists:

- `outputs/local_safety_boost/safety-indicbert-best-infer-fp16`
- `outputs/local_safety_boost/safety-indicbert-best`

That means the hybrid safety stack can come up by default without editing `.env.local`. If you want to override it manually, set:

```bash
export MANOVARTA_LOCAL_SAFETY_CHECKPOINT=/absolute/path/to/checkpoint
```

## Optional Colab encoder work

If you want to test the Hindi-sensitive encoder path on GPU:

```bash
pip install -e .[gpu]
python tools/semantic_safety_eval.py --model ai4bharat/IndicBERTv2-MLM-only
```

There is also a Colab-specific walkthrough in `experiments/colab/README.md`.
Full fine-tuning commands live in `training/README.md`.
The ready-to-run notebook is `experiments/colab/manovarta_training_colab.ipynb`.

If you want the full remote train/eval path in one command on Colab GPU, use:

```bash
python tools/run_colab_full_pipeline.py --device cuda
```

If you want to continue-train Aya on Vertex AI instead of Colab, use the submitter in `tools/run_vertex_aya_continue.py`. The worker reuses the same compact-schema DAIC continuation flow and uploads checkpoints/reports back into GCS.

## Saved evaluation bundle

To write a durable evaluation summary into `reports/`:

```bash
python tools/generate_eval_bundle.py
```

You can optionally include a local checkpoint path:

```bash
python tools/generate_eval_bundle.py --checkpoint outputs/extractor-qwen25
```

To package the current recommended runtime stack and the latest hybrid Colab validation into a single report:

```bash
python tools/generate_best_current_system_report.py
```

To package trained outputs after a Colab or local run:

```bash
python tools/package_training_artifacts.py --source-dir outputs
```

If you finish a Colab training run and want the repo-friendly outputs in one pass:

```bash
python tools/finalize_colab_run.py \
  --checkpoint-path outputs/extractor-qwen25 \
  --semantic-model ai4bharat/IndicBERTv2-MLM-only
```

That will:

- run checkpoint, heuristic, semantic safety, and live LLM evaluation when available
- save durable JSON reports under `reports/colab_run/`
- write a Markdown bundle summary
- package `outputs/` and `reports/colab_run/` into `artifacts/manovarta_colab_bundle.zip`

If you also want a Drive copy from Colab:

```bash
python tools/finalize_colab_run.py \
  --checkpoint-path outputs/extractor-qwen25 \
  --semantic-model ai4bharat/IndicBERTv2-MLM-only \
  --drive-dir /content/drive/MyDrive/ManoVartaOutputs
```

## Notes

- Large-model hosting is intentionally left out of this repository.
- Voice uses browser-native APIs, so it depends on microphone permission and browser support.
- Seed data is synthetic and should be treated as pilot material only.
