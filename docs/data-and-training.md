# Data And Training

## Data layers

The repository uses multiple data layers for different purposes.

- `data/seed/`
  - Seed conversations and compact synthetic supervision
- `data/gold/`
  - Gold bilingual screening packets
  - Annotation and adjudication material
- `data/processed/`
  - Exported training and evaluation JSONL files

## Language scope

- Required project languages: English and Hindi
- Additional runtime robustness condition: Hinglish

## Training workflow

Training was split by workload.

- Colab
  - Compact extractor fine-tuning
  - Safety classifier fine-tuning
  - Export / evaluation workflow iteration
- GCP / Vertex AI
  - Aya continuation training
  - Larger cloud-staged continuation runs

## Main artifact families

- Extractor artifacts
  - Qwen-based compact extractor experiments
  - Remote trained Aya deployment path
- Safety artifacts
  - IndicBERT-based safety classifier checkpoint

## Export entry points

- `python tools/export_training_sets.py --source gold-core`
- `python tools/export_training_sets.py --source gold`
- `python tools/export_training_sets.py --source hybrid`

Use `gold-core` for stricter English-only gold supervision, and `hybrid` for the broader multilingual training mix.
