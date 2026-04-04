# Best Current System Report

- Generated: `2026-04-04T19:20:06.806618+00:00`
- Git revision: `cf6ade9`
- Public runtime URL: `https://manovarta-runtime-122722888597.us-east4.run.app`

## Default Runtime

- Provider: `huggingface`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`
- Hybrid safety enabled: `True`
- Rule safety monitor enabled: `True`
- Local safety checkpoint: `outputs/local_safety_boost/safety-indicbert-best`

## Live Deployment Runtime

- Provider: `huggingface`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`
- Hybrid safety enabled: `True`
- Cloud voice enabled: `True`
- Local safety checkpoint enabled: `True`

## Extractor Baseline

- Coverage completeness: `0.913`
- MAE: `0.443`
- Exact match: `0.562`
- Macro-F1: `0.272`
- Safety precision: `0.0`
- Safety recall: `0.0`

## Hybrid Runtime Validation

- Coverage completeness: `0.804`
- MAE: `0.28`
- Exact match: `0.733`
- Macro-F1: `0.344`
- Safety precision: `0.333`
- Safety recall: `1.0`

## Delta Vs Extractor Baseline

- `coverage_completeness`: `-0.109`
- `mae`: `-0.163`
- `exact_match_rate`: `+0.171`
- `macro_f1`: `+0.072`
- `safety_precision`: `+0.333`
- `safety_recall`: `+1.000`

## Local Default Safety Checkpoint

- Status: `ok`
- Accuracy: `0.6071`
- Macro-F1: `0.4369`
- Model path: `outputs/local_safety_boost/safety-indicbert-best`

## Recommendation

- Ship default: `hybrid_runtime`
- Hybrid runtime preserved zero parse failures while pushing safety recall to 1.0 in the completed Colab validation.
- The promoted local safety checkpoint can now be auto-discovered by the repo without a private env file.
- The pure extractor checkpoints remain useful benchmarks, but the safer runtime stack is the better default for demos and guarded screening.

## Known Gaps

- Safety precision is still low, so the stack remains conservative and will over-trigger review flags.
- Hinglish coverage remains the weakest language slice in the hybrid runtime evaluation.

## Sources

- `aya_baseline_json`: `reports/aya_colab_eval_a100_20260328.json`
- `hybrid_summary_source`: `https://files.catbox.moe/mt0f2k.json`
- `hybrid_summary_mirror`: `reports/hybrid_runtime_validation_colab_20260404.json`
