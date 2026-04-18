# Colab Private-Source Aya Continue: Common Failure Points

Use this list before and during run.

## 1) Source access failure
- Symptom: `git clone` or repo fetch fails.
- Fix: Use `ManoVarta_Colab_Aya_Continue_PrivateSource_NoToken.ipynb` with `SOURCE_MODE='drive_archive'` or `drive_folder`.

## 2) Base Aya model missing
- Symptom: preflight fails with base model path missing.
- Fix: ensure `BASE_MODEL_PATH` points to a full local Aya snapshot folder (config + model shards).

## 3) Adapter path invalid
- Symptom: preflight fails on missing `adapter_config.json`.
- Fix: point `INIT_ADAPTER` to the exact `aya_bundle` folder (or parent containing it).

## 4) DAIC path incomplete
- Symptom: preflight warning/error around DAIC root or no CSV files.
- Fix: verify transcript CSV files exist under `DAIC_ROOT`.

## 5) Colab disk exhaustion
- Symptom: unpack/install/train fails unexpectedly, often with IO/OSError.
- Fix: keep source archive lean and check `df -h /content` before training.

## 6) GPU runtime mismatch
- Symptom: slow run or CUDA unavailable.
- Fix: select GPU runtime in Colab before executing; notebook prints `nvidia-smi`.

## 7) Gated-model token failures
- Symptom: Hugging Face auth errors for Aya.
- Fix: for this notebook, avoid token path entirely by using `--base-model-path` local snapshot.

## 8) No outputs at end
- Symptom: training exits but no summary file.
- Fix: check `REPORTS_DIR/daic_continue_summary.json` and rerun from preflight cell onward.
