# Training Workflows

This folder contains the training and evaluation entry points used during development.

## What lives here

- extractor fine-tuning
- safety classifier training
- checkpoint evaluation
- Colab-oriented orchestration scripts
- Vertex AI continuation helpers for Aya

## Main workflow split

### Colab

Used for:

- compact extractor training
- safety classifier training
- data export and evaluation loops

Typical setup:

```bash
python tools/create_data_splits.py
python tools/export_training_sets.py --source hybrid
python tools/run_colab_full_pipeline.py --device cuda
```

### GCP / Vertex AI

Used for:

- Aya continuation training
- larger staged runs that were less practical in a single Colab session

Main entry points:

```bash
python tools/run_vertex_aya_continue.py \
  --project YOUR_GCP_PROJECT \
  --location us-central1 \
  --staging-bucket gs://YOUR_VERTEX_BUCKET \
  --daic-root gs://YOUR_DATA_BUCKET/DAIC-WOZ \
  --init-adapter /path/to/local/aya_adapter_dir
```

## Useful exports

- `--source gold-core`
  - stricter English gold supervision
- `--source gold`
  - English gold + Hindi pilot supervision
- `--source hybrid`
  - broader multilingual mix

## Main scripts

- `finetune_extractor.py`
- `train_safety_classifier.py`
- `evaluate_extractor_checkpoint.py`
- `evaluate_safety_checkpoint.py`

## Notes

- The current deployed live stack uses Gemini for live conversation and remote Aya for extraction.
- Training artifacts and source data are intentionally kept separate from generated submission bundles.
