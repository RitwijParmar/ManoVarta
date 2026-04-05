# Best Current System Report

- Generated: `2026-04-05T02:23:02.149446+00:00`
- Git revision: `15abf2e`
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

- Coverage completeness: `0.745`
- MAE: `0.482`
- Exact match: `0.584`
- Macro-F1: `0.216`
- Safety precision: `1.0`
- Safety recall: `1.0`

## Delta Vs Extractor Baseline

- `coverage_completeness`: `-0.168`
- `mae`: `+0.039`
- `exact_match_rate`: `+0.022`
- `macro_f1`: `-0.056`
- `safety_precision`: `+1.000`
- `safety_recall`: `+1.000`

## Local Default Safety Checkpoint

- Status: `ok`
- Accuracy: `0.6071`
- Macro-F1: `0.4369`
- Model path: `outputs/local_safety_boost/safety-indicbert-best`

## Recommendation

- Ship default: `hybrid_runtime`
- Hybrid runtime preserved zero parse failures while pushing safety recall to 1.0 in the latest live runtime endpoint evaluation.
- The promoted local safety checkpoint can now be auto-discovered by the repo without a private env file.
- The pure extractor checkpoints remain useful benchmarks, but the safer runtime stack is the better default for demos and guarded screening.

## Known Gaps

- English is now the weakest language slice in the live runtime evaluation at coverage 0.727.
- Live runtime coverage still trails the best offline extractor baseline, so hosted extraction reliability remains the next coverage bottleneck.
- Production inference still depends on hosted Hugging Face models rather than a fully self-hosted extractor stack.

## Sources

- `aya_baseline_json`: `reports/aya_colab_eval_a100_20260328.json`
- `hybrid_summary_source`: `/Users/ritwij/Documents/multilingualChatbot/reports/live_runtime_eval_20260404.json`
- `hybrid_summary_mirror`: `reports/live_runtime_eval_20260404.json`
