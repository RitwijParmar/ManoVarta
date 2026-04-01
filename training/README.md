# Training Workflows

This folder contains Colab-friendly scripts for fine-tuning and evaluation.

## Recommended defaults

- extractor fine-tuning base: `Qwen/Qwen2.5-7B-Instruct`
- safety encoder fine-tuning base: `ai4bharat/IndicBERTv2-MLM-only`
- primary hosted evaluation model remains `CohereLabs/aya-expanse-32b`
- second LLM baseline remains `moonshotai/Kimi-K2-Instruct`

The idea is simple:

- use the hosted stronger models for comparison and prompt-based extraction,
- use the open smaller models for training and ablation work in Colab.

## Setup

```bash
python tools/generate_seed_scaleup.py
python tools/colab_bootstrap.py
python tools/create_data_splits.py
python tools/export_training_sets.py
```

## One-shot Colab pipeline

If you want a single resumable Colab command that:

- exports the compact multilingual training sets,
- fine-tunes the extractor,
- fine-tunes safety,
- selects the best saved safety checkpoint on the held-out test split,
- runs staged extractor evaluation with an early parse-failure smoke test,
- and packages the reports and artifacts,

use:

```bash
python tools/run_colab_full_pipeline.py \
  --device cuda \
  --drive-dir /content/drive/MyDrive/ManoVartaOutputs
```

If you also have `DAIC-WOZ` mounted in Colab, add:

```bash
--daic-root /content/drive/MyDrive/DAIC-WOZ
```

To fetch from the USC DAIC-WOZ index directly in Colab:

```bash
python tools/fetch_daic_woz.py --output-dir /content/drive/MyDrive/DAIC-WOZ
# Optional sample session zips:
python tools/fetch_daic_woz.py --output-dir /content/drive/MyDrive/DAIC-WOZ --session-split train --max-session-zips 5
```

For the strongest extractor train set, prefer:

- `data/processed/extractor_train_best.jsonl`
- or `data/processed/extractor_train_best_augmented_daic.jsonl` if you export with `--daic-root`

Those exports use the compact JSON schema and upweight Hindi/Hinglish examples so English auxiliary data does not dominate the multilingual objective.

## Fine-tune extraction model

```bash
python -m training.finetune_extractor \
  --model-name Qwen/Qwen2.5-7B-Instruct \
  --train-file data/processed/extractor_train_best.jsonl \
  --eval-file data/processed/extractor_dev.jsonl \
  --output-dir outputs/extractor-qwen25 \
  --precision auto
```

## Train safety classifier

```bash
python -m training.train_safety_classifier \
  --model-name ai4bharat/IndicBERTv2-MLM-only \
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

## Finalize a Colab run

```bash
python tools/finalize_colab_run.py \
  --checkpoint-path outputs/extractor-qwen25 \
  --semantic-model ai4bharat/IndicBERTv2-MLM-only
```

That writes durable JSON reports under `reports/colab_run/` and packages the run into `artifacts/manovarta_colab_bundle.zip`.
