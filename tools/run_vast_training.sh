#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$HOME/ManoVarta}"
cd "$ROOT_DIR"

source .venv/bin/activate

export TOKENIZERS_PARALLELISM=false
export HF_HUB_ENABLE_HF_TRANSFER=1

GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || echo unknown)"
echo "gpu=${GPU_NAME}"

EXTRACTOR_MODEL="${MANOVARTA_REMOTE_EXTRACTOR_MODEL:-CohereLabs/aya-expanse-8b}"
SAFETY_CLASSIFIER_MODEL="${MANOVARTA_REMOTE_SAFETY_CLASSIFIER_MODEL:-ai4bharat/IndicBERTv2-MLM-only}"
SAFETY_RUNTIME_MODEL="${MANOVARTA_REMOTE_SAFETY_MODEL:-Qwen/Qwen3Guard-Gen-8B}"

EXTRACTOR_OUT="${MANOVARTA_REMOTE_EXTRACTOR_OUT:-outputs/vast_remote/extractor}"
SAFETY_OUT="${MANOVARTA_REMOTE_SAFETY_OUT:-outputs/vast_remote/safety}"

EXTRACTOR_LOG="${MANOVARTA_REMOTE_EXTRACTOR_LOG:-logs/vast_extractor.log}"
SAFETY_LOG="${MANOVARTA_REMOTE_SAFETY_LOG:-logs/vast_safety.log}"

export MANOVARTA_SAFETY_MODEL="$SAFETY_RUNTIME_MODEL"

python -m training.finetune_extractor \
  --model-name "$EXTRACTOR_MODEL" \
  --train-file data/processed/extractor_train.jsonl \
  --eval-file data/processed/extractor_dev.jsonl \
  --output-dir "$EXTRACTOR_OUT" \
  --device cuda \
  --precision bf16 \
  --model-dtype bf16 \
  --epochs "${MANOVARTA_REMOTE_EPOCHS:-3}" \
  --batch-size "${MANOVARTA_REMOTE_BATCH_SIZE:-1}" \
  --grad-accum "${MANOVARTA_REMOTE_GRAD_ACCUM:-8}" \
  --max-length "${MANOVARTA_REMOTE_MAX_LENGTH:-1536}" \
  --gradient-checkpointing \
  --use-4bit \
  --save-strategy steps \
  --save-steps "${MANOVARTA_REMOTE_SAVE_STEPS:-10}" \
  --save-total-limit "${MANOVARTA_REMOTE_SAVE_LIMIT:-8}" \
  --eval-strategy steps \
  --eval-steps "${MANOVARTA_REMOTE_EVAL_STEPS:-10}" \
  --resume-from-checkpoint last 2>&1 | tee "$EXTRACTOR_LOG"

python -m training.train_safety_classifier \
  --model-name "$SAFETY_CLASSIFIER_MODEL" \
  --train-file data/processed/safety_train.jsonl \
  --eval-file data/processed/safety_dev.jsonl \
  --output-dir "$SAFETY_OUT" \
  --device cuda \
  --precision bf16 \
  --epochs "${MANOVARTA_REMOTE_SAFETY_EPOCHS:-4}" \
  --batch-size "${MANOVARTA_REMOTE_SAFETY_BATCH_SIZE:-8}" \
  --save-strategy steps \
  --save-steps "${MANOVARTA_REMOTE_SAFETY_SAVE_STEPS:-20}" \
  --save-total-limit "${MANOVARTA_REMOTE_SAFETY_SAVE_LIMIT:-8}" \
  --eval-strategy steps \
  --eval-steps "${MANOVARTA_REMOTE_SAFETY_EVAL_STEPS:-20}" \
  --resume-from-checkpoint last 2>&1 | tee "$SAFETY_LOG"

python tools/finalize_colab_run.py \
  --checkpoint-path "$EXTRACTOR_OUT" \
  --safety-checkpoint-path "$SAFETY_OUT"

echo "vast training complete"
