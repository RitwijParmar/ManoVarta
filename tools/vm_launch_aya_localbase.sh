#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="/home/ritwij/manovarta_vmrun/manovarta-aya-daic-vm-20260412-033124"
FRIEND_ROOT="/home/ritwij/friend_bundle/manovarta"
IMAGE="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "Missing run dir: $RUN_DIR" >&2
  exit 2
fi
if [[ ! -d "$FRIEND_ROOT/daic" ]]; then
  echo "Missing DAIC dir: $FRIEND_ROOT/daic" >&2
  exit 2
fi
if [[ ! -d "$FRIEND_ROOT/aya_bundle" ]]; then
  echo "Missing adapter dir: $FRIEND_ROOT/aya_bundle" >&2
  exit 2
fi
if [[ ! -d "$FRIEND_ROOT/models/aya-expanse-8b" ]]; then
  echo "Missing base model dir: $FRIEND_ROOT/models/aya-expanse-8b" >&2
  exit 2
fi

TS="$(date +%Y%m%d-%H%M%S)"
LOG="${RUN_DIR}/train_localbase_${TS}.log"
PIDFILE="${RUN_DIR}/train_localbase.pid"
INNER="${RUN_DIR}/docker_train_inner.sh"

cat >"$INNER" <<'INNER_EOF'
#!/usr/bin/env bash
set -euo pipefail

cd /workspace
python -m pip install --upgrade pip
python -m pip install \
  fastapi==0.115.12 \
  pydantic==2.12.3 \
  huggingface_hub==0.34.0 \
  'hf_transfer>=0.1.8' \
  python-dotenv==1.0.1 \
  google-cloud-storage==2.18.0 \
  datasets==3.0.0 \
  accelerate==1.0.0 \
  trl==0.11.0 \
  peft==0.18.1 \
  transformers==4.45.0 \
  numpy==1.26.0 \
  sentencepiece==0.2.0 \
  bitsandbytes==0.45.0

python tools/run_colab_daic_continue.py \
  --device cuda \
  --daic-root /friend_root/daic \
  --init-adapter /friend_root/aya_bundle \
  --base-model-path /friend_root/models/aya-expanse-8b \
  --extractor-model CohereLabs/aya-expanse-8b \
  --reports-dir /friend_root/reports/colab_daic_continue_vm \
  --extractor-output /friend_root/outputs/extractor-aya-8b-compact-daic-continue-vm \
  --extractor-epochs 1 \
  --extractor-batch-size 1 \
  --extractor-grad-accum 8 \
  --extractor-max-length 1536 \
  --extractor-save-steps 10 \
  --extractor-max-new-tokens 900 \
  --smoke-limit 8
INNER_EOF

chmod +x "$INNER"

nohup sudo docker run --rm --gpus all \
  -v "$RUN_DIR:/workspace" \
  -v "$FRIEND_ROOT:/friend_root" \
  --entrypoint /bin/bash \
  "$IMAGE" \
  -lc "/workspace/docker_train_inner.sh" \
  >"$LOG" 2>&1 &

echo $! >"$PIDFILE"

echo "LOG=$LOG"
echo "PID=$(cat "$PIDFILE")"
