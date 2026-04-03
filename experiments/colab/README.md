# Colab Workbench

Use this path when you want GPU-backed experiments without bloating the local runtime.
The fastest route is to open `manovarta_training_colab.ipynb` in Colab and run cells top to bottom.
If you want the Aya continuation path with DAIC-backed checkpoints saved directly to Drive, use `manovarta_aya_daic_continue_colab.ipynb`.

If you prefer one unattended command instead of stepping through the notebook, use:

```bash
python tools/run_colab_full_pipeline.py \
  --device cuda \
  --drive-dir /content/drive/MyDrive/ManoVartaOutputs
```

## Suggested Colab flow

```bash
export GITHUB_TOKEN=...
git clone https://oauth2:${GITHUB_TOKEN}@github.com/RitwijParmar/ManoVarta.git
cd ManoVarta
python tools/colab_bootstrap.py
```

Optional environment setup:

```bash
export HF_TOKEN=...
export MANOVARTA_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
export MANOVARTA_EXTRACTION_MODEL=CohereLabs/aya-expanse-32b
```

## Useful Colab commands

Baseline evaluation:

```bash
python tools/evaluate_seed_runtime.py --mode heuristic
python tools/evaluate_seed_runtime.py --mode llm --model CohereLabs/aya-expanse-32b
python tools/evaluate_seed_runtime.py --mode llm --model moonshotai/Kimi-K2-Instruct
```

Semantic safety encoder:

```bash
python tools/semantic_safety_eval.py --model ai4bharat/IndicBERTv2-MLM-only
```

Training exports and fine-tuning:

```bash
python tools/generate_seed_scaleup.py
python tools/create_data_splits.py
python tools/fetch_daic_woz.py --output-dir /content/drive/MyDrive/DAIC-WOZ
python tools/export_training_sets.py
python -m training.finetune_extractor --model-name Qwen/Qwen2.5-7B-Instruct --train-file data/processed/extractor_train.jsonl --eval-file data/processed/extractor_dev.jsonl --output-dir outputs/extractor-qwen25
python -m training.train_safety_classifier --model-name ai4bharat/IndicBERTv2-MLM-only --train-file data/processed/safety_train.jsonl --eval-file data/processed/safety_dev.jsonl --output-dir outputs/safety-indicbert
```

The fetch helper uses the official source index:
`https://dcapswoz.ict.usc.edu/wwwdaicwoz/`

The unattended wrapper above is preferred now because it:

- trains from `extractor_train_best.jsonl` by default,
- keeps extractor evaluation resumable,
- stops early if the extractor smoke eval hits parse failures,
- and auto-selects the strongest saved safety checkpoint.

Finalize the run and package durable outputs:

```bash
python tools/finalize_colab_run.py \
  --checkpoint-path outputs/extractor-qwen25 \
  --semantic-model ai4bharat/IndicBERTv2-MLM-only
```

If Drive is mounted, you can also copy outputs, reports, and the bundle zip in one step:

```bash
python tools/finalize_colab_run.py \
  --checkpoint-path outputs/extractor-qwen25 \
  --semantic-model ai4bharat/IndicBERTv2-MLM-only \
  --drive-dir /content/drive/MyDrive/ManoVartaOutputs
```

Annotation packet export:

```bash
python tools/build_annotation_packets.py
```

## What this is for

- batch model comparison without local CPU bottlenecks
- trying the IndicBERT-style encoder path on Hindi and Hinglish cases
- exporting seed packets for annotation cleanup or second-pass review

Keep the local app lightweight and use Colab for the heavier evaluation loops.
