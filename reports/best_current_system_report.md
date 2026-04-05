# Best Current System Report

- Generated: `2026-04-05T04:14:17.884196+00:00`
- Git revision: `f29f89c`
- Public runtime URL: `https://manovarta-runtime-122722888597.us-east4.run.app`

## Default Runtime

- Provider: `local`
- Chat model: `/models/qwen2.5-0.5b-instruct`
- Extraction model: `/models/qwen2.5-0.5b-instruct`
- Hybrid safety enabled: `True`
- Rule safety monitor enabled: `True`
- Local safety checkpoint: `/tmp/manovarta_local_safety_checkpoint/59e9264e860d`

## Live Deployment Runtime

- Provider: `local`
- Chat model: `/models/qwen2.5-0.5b-instruct`
- Extraction model: `/models/qwen2.5-0.5b-instruct`
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

- Coverage completeness: `0.783`
- MAE: `0.424`
- Exact match: `0.639`
- Macro-F1: `0.251`
- Safety precision: `1.0`
- Safety recall: `1.0`

## Delta Vs Extractor Baseline

- `coverage_completeness`: `-0.130`
- `mae`: `-0.019`
- `exact_match_rate`: `+0.077`
- `macro_f1`: `-0.021`
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

- Hindi is now the weakest language slice in the live runtime evaluation at coverage 0.719.
- Live runtime coverage still trails the best offline extractor baseline, so hosted extraction reliability remains the next coverage bottleneck.

## Sources

- `aya_baseline_json`: `reports/aya_colab_eval_a100_20260328.json`
- `hybrid_summary_source`: `/Users/ritwij/Documents/multilingualChatbot/reports/live_runtime_eval_20260404.json`
- `hybrid_summary_mirror`: `reports/live_runtime_eval_20260404.json`
