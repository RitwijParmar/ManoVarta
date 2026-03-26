# Evaluation Bundle

- Generated: `2026-03-26T01:49:38.306116+00:00`
- Git revision: `28ed406`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`

## Seed Summary

- Profiles: `36`
- Conversations: `36`
- Languages: `{'en': 12, 'hi': 12, 'hinglish': 12}`
- Safety levels: `{'none': 26, 'review': 7, 'urgent': 3}`

## Processed Files

- `extractor_dev.jsonl`: `9` lines
- `extractor_test.jsonl`: `9` lines
- `extractor_train.jsonl`: `18` lines
- `follow_up_dev.jsonl`: `18` lines
- `follow_up_test.jsonl`: `18` lines
- `follow_up_train.jsonl`: `24` lines
- `safety_dev.jsonl`: `9` lines
- `safety_test.jsonl`: `9` lines
- `safety_train.jsonl`: `18` lines
- `splits.json`: `44` lines

## Reports

### heuristic

- Status: `ok`
- Overall: `{'covered_items': 16, 'coverage_completeness': 0.028, 'mae': 0.5, 'exact_match_rate': 0.625, 'macro_f1': 0.067, 'safety_precision': 1.0, 'safety_recall': 0.4}`

### checkpoint

- Status: `skipped`
- Reason: No checkpoint path provided.

### semantic_safety

- Status: `skipped`
- Reason: Semantic evaluation skipped by flag.

### llm_primary

- Status: `ok`
- Overall: `{'covered_items': 8, 'coverage_completeness': 0.014, 'mae': 0.125, 'exact_match_rate': 0.875, 'macro_f1': 0.022, 'safety_precision': 0.0, 'safety_recall': 0.0}`
- Model: `CohereLabs/aya-expanse-32b`

### llm_baselines

- Status: `ok`
