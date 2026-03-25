# Training Workflows

This folder contains Colab-friendly scripts for fine-tuning and evaluation.

## Recommended defaults

- extractor fine-tuning base: `Qwen/Qwen2.5-7B-Instruct`
- safety encoder fine-tuning base: `google/muril-base-cased`
- primary hosted evaluation model remains `CohereLabs/aya-expanse-32b`
- second LLM baseline remains `moonshotai/Kimi-K2-Instruct`

The idea is simple:

- use the hosted stronger models for comparison and prompt-based extraction,
- use the open smaller models for training and ablation work in Colab.

## Setup

```bash
python tools/colab_bootstrap.py
python tools/create_data_splits.py
python tools/export_training_sets.py
```

## Fine-tune extraction model

```bash
python -m training.finetune_extractor \
  --model-name Qwen/Qwen2.5-7B-Instruct \
  --train-file data/processed/extractor_train.jsonl \
  --eval-file data/processed/extractor_dev.jsonl \
  --output-dir outputs/extractor-qwen25 \
  --precision auto
```

## Train safety classifier

```bash
python -m training.train_safety_classifier \
  --model-name google/muril-base-cased \
  --train-file data/processed/safety_train.jsonl \
  --eval-file data/processed/safety_dev.jsonl \
  --output-dir outputs/safety-indicbert \
  --precision auto
```

## Evaluate extractor checkpoint

```bash
python training/evaluate_extractor_checkpoint.py \
  --model-path outputs/extractor-qwen25 \
  --eval-file data/processed/extractor_test.jsonl
```
