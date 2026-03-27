#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$HOME/ManoVarta}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip wheel setuptools
python -m pip install -e ".[dev,train,train-cuda]"

python tools/generate_seed_scaleup.py
python tools/generate_seed_nuance_pack.py
python tools/generate_seed_silver_variants.py
python tools/create_data_splits.py
python tools/export_training_sets.py

mkdir -p logs outputs/vast_remote artifacts reports/vast_run

echo "vast bootstrap complete"
