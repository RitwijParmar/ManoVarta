#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTORCH_ENABLE_MPS_FALLBACK=1
export TOKENIZERS_PARALLELISM=false

mkdir -p logs outputs/local_mps

EXTRACTOR_OUT="outputs/local_mps/extractor-qwen25-1_5b-mps"
SAFETY_OUT="outputs/local_mps/safety-indicbert-mps"

EXTRACTOR_LOG="logs/extractor_mps.log"
SAFETY_LOG="logs/safety_mps.log"

echo "== extractor =="
./.venv/bin/python -m training.finetune_extractor \
  --model-name Qwen/Qwen2.5-1.5B-Instruct \
  --train-file data/processed/extractor_train.jsonl \
  --eval-file data/processed/extractor_dev.jsonl \
  --output-dir "$EXTRACTOR_OUT" \
  --device mps \
  --precision fp16 \
  --model-dtype fp16 \
  --epochs 2 \
  --batch-size 1 \
  --grad-accum 8 \
  --max-length 1024 \
  --gradient-checkpointing \
  --save-strategy steps \
  --save-steps 2 \
  --save-total-limit 6 \
  --eval-strategy steps \
  --eval-steps 4 \
  --resume-from-checkpoint last | tee "$EXTRACTOR_LOG"

echo "== safety =="
./.venv/bin/python -m training.train_safety_classifier \
  --model-name ai4bharat/IndicBERTv2-MLM-only \
  --train-file data/processed/safety_train.jsonl \
  --eval-file data/processed/safety_dev.jsonl \
  --output-dir "$SAFETY_OUT" \
  --device mps \
  --precision fp16 \
  --epochs 3 \
  --batch-size 4 \
  --save-strategy steps \
  --save-steps 2 \
  --save-total-limit 6 \
  --eval-strategy steps \
  --eval-steps 4 \
  --resume-from-checkpoint last | tee "$SAFETY_LOG"

echo "training complete"
