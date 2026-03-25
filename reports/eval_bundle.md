# Evaluation Bundle

- Generated: `2026-03-25T23:26:01.411395+00:00`
- Git revision: `7934573`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`

## Seed Summary

- Profiles: `12`
- Conversations: `12`
- Languages: `{'en': 4, 'hi': 4, 'hinglish': 4}`
- Safety levels: `{'none': 8, 'review': 3, 'urgent': 1}`

## Processed Files

- `extractor_dev.jsonl`: `3` lines
- `extractor_test.jsonl`: `3` lines
- `extractor_train.jsonl`: `6` lines
- `follow_up_dev.jsonl`: `3` lines
- `follow_up_test.jsonl`: `3` lines
- `follow_up_train.jsonl`: `6` lines
- `safety_dev.jsonl`: `3` lines
- `safety_test.jsonl`: `3` lines
- `safety_train.jsonl`: `6` lines
- `splits.json`: `20` lines

## Reports

### heuristic

- Status: `ok`
- Overall: `{'covered_items': 15, 'coverage_completeness': 0.078, 'mae': 0.467, 'exact_match_rate': 0.667, 'macro_f1': 0.194, 'safety_precision': 1.0, 'safety_recall': 1.0}`

### checkpoint

- Status: `skipped`
- Reason: No checkpoint path provided.

### semantic_safety

- Status: `skipped`
- Reason: Semantic evaluation skipped by flag.

### llm_primary

- Status: `ok`
- Overall: `{'covered_items': 0, 'coverage_completeness': 0.0, 'mae': None, 'exact_match_rate': None, 'macro_f1': 0.0, 'safety_precision': 0.0, 'safety_recall': 0.0}`
- Model: `CohereLabs/aya-expanse-32b`

### llm_baselines

- Status: `ok`
