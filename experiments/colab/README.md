# Colab Workbench

Use this path when you want GPU-backed experiments without bloating the local runtime.
The fastest route is to open `manovarta_training_colab.ipynb` in Colab and run cells top to bottom.

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
python tools/semantic_safety_eval.py --model google/muril-base-cased
```

Training exports and fine-tuning:

```bash
python tools/create_data_splits.py
python tools/export_training_sets.py
python -m training.finetune_extractor --model-name Qwen/Qwen2.5-7B-Instruct --train-file data/processed/extractor_train.jsonl --eval-file data/processed/extractor_dev.jsonl --output-dir outputs/extractor-qwen25
python -m training.train_safety_classifier --model-name google/muril-base-cased --train-file data/processed/safety_train.jsonl --eval-file data/processed/safety_dev.jsonl --output-dir outputs/safety-indicbert
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
