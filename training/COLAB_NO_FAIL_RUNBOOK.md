# Colab No-Fail Runbook (Aya Continue)

Use this runbook in Google Colab to avoid starting a bad training run.

## 1) Colab Setup

```bash
!nvidia-smi
!git clone https://github.com/<your-org>/<your-repo>.git
%cd <your-repo>
!pip install -U pip
!pip install -e ".[training]"
```

If you are downloading Aya from Hugging Face in Colab, set your HF token:

```python
import os
os.environ["HF_TOKEN"] = "<your_hf_token>"
os.environ["HUGGING_FACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]
os.environ["HUGGINGFACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]
```

If you already have a local Aya base snapshot on Drive (shared with your friend), you can skip HF token and set:

```python
BASE_MODEL_PATH = "/content/drive/MyDrive/manovarta/models/aya-expanse-8b"
```

If you use HF token mode, omit `--base-model-path` in the commands below.

## 2) Define Input Paths

Set local Colab/Drive paths:

```python
DAIC_ROOT = "/content/drive/MyDrive/manovarta/daic"          # local folder
INIT_ADAPTER = "/content/drive/MyDrive/manovarta/aya_bundle" # folder containing adapter_config.json (or nested)
REPORTS_DIR = "/content/drive/MyDrive/manovarta/reports/colab_daic_continue"
EXTRACTOR_OUT = "/content/drive/MyDrive/manovarta/outputs/extractor-aya-8b-compact-daic-continue"
BASE_MODEL_PATH = "/content/drive/MyDrive/manovarta/models/aya-expanse-8b"  # optional local base model
```

## 3) Preflight Only (Required)

This will fail fast if anything is wrong (GPU/HF/data/adapter):

```bash
!python tools/run_colab_daic_continue.py \
  --device cuda \
  --daic-root "$DAIC_ROOT" \
  --init-adapter "$INIT_ADAPTER" \
  --base-model-path "$BASE_MODEL_PATH" \
  --reports-dir "$REPORTS_DIR" \
  --extractor-output "$EXTRACTOR_OUT" \
  --extractor-model CohereLabs/aya-expanse-8b \
  --preflight-only
```

## 4) Full Run (Only After Preflight Passes)

```bash
!python tools/run_colab_daic_continue.py \
  --device cuda \
  --daic-root "$DAIC_ROOT" \
  --init-adapter "$INIT_ADAPTER" \
  --base-model-path "$BASE_MODEL_PATH" \
  --reports-dir "$REPORTS_DIR" \
  --extractor-output "$EXTRACTOR_OUT" \
  --extractor-model CohereLabs/aya-expanse-8b \
  --extractor-epochs 1 \
  --extractor-batch-size 1 \
  --extractor-grad-accum 8 \
  --extractor-max-length 1536 \
  --extractor-save-steps 10 \
  --smoke-limit 8
```

## 5) Success Signal

Run is successful when this file appears:

- `<REPORTS_DIR>/daic_continue_summary.json`

And output adapter/checkpoints appear under:

- `<EXTRACTOR_OUT>`
