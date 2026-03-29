# Evaluation Bundle

- Generated: `2026-03-29T05:52:42.746565+00:00`
- Git revision: `99c7f2e`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`

## Seed Summary

- Profiles: `48`
- Conversations: `180`
- Languages: `{'en': 60, 'hi': 60, 'hinglish': 60}`
- Safety levels: `{'none': 127, 'review': 37, 'urgent': 16}`

## Processed Files

- `extractor_dev.jsonl`: `48` lines
- `extractor_test.jsonl`: `48` lines
- `extractor_train.jsonl`: `84` lines
- `extractor_train_best.jsonl`: `140` lines
- `follow_up_dev.jsonl`: `96` lines
- `follow_up_test.jsonl`: `144` lines
- `follow_up_train.jsonl`: `120` lines
- `safety_dev.jsonl`: `80` lines
- `safety_test.jsonl`: `84` lines
- `safety_train.jsonl`: `126` lines
- `splits.json`: `56` lines

## Reports

### heuristic

- Status: `ok`
- Overall: `{'covered_items': 63, 'coverage_completeness': 0.022, 'mae': 0.492, 'exact_match_rate': 0.635, 'macro_f1': 0.058, 'safety_precision': 1.0, 'safety_recall': 0.604}`

### checkpoint

- Status: `skipped`
- Reason: No checkpoint path provided.

### aya_colab_a100

- Status: `ok`
- Overall: `{'covered_items': 336, 'coverage_completeness': 0.913, 'mae': 0.443, 'exact_match_rate': 0.562, 'macro_f1': 0.272, 'safety_precision': 0.0, 'safety_recall': 0.0}`

### semantic_safety

- Status: `skipped`
- Reason: Semantic evaluation skipped by flag.

### llm_primary

- Status: `ok`
- Overall: `{'covered_items': 0, 'coverage_completeness': 0.0, 'mae': None, 'exact_match_rate': None, 'macro_f1': 0.0, 'safety_precision': 0.0, 'safety_recall': 0.0}`
- Model: `CohereLabs/aya-expanse-32b`

### llm_baselines

- Status: `ok`
