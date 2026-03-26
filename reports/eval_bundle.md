# Evaluation Bundle

- Generated: `2026-03-26T23:46:52.999680+00:00`
- Git revision: `5865f90`
- Chat model: `Qwen/Qwen2.5-7B-Instruct`
- Extraction model: `CohereLabs/aya-expanse-32b`

## Seed Summary

- Profiles: `48`
- Conversations: `48`
- Languages: `{'en': 16, 'hi': 16, 'hinglish': 16}`
- Safety levels: `{'none': 34, 'review': 10, 'urgent': 4}`

## Processed Files

- `extractor_dev.jsonl`: `12` lines
- `extractor_test.jsonl`: `12` lines
- `extractor_train.jsonl`: `24` lines
- `follow_up_dev.jsonl`: `24` lines
- `follow_up_test.jsonl`: `36` lines
- `follow_up_train.jsonl`: `36` lines
- `safety_dev.jsonl`: `12` lines
- `safety_test.jsonl`: `12` lines
- `safety_train.jsonl`: `24` lines
- `splits.json`: `56` lines

## Reports

### heuristic

- Status: `ok`
- Overall: `{'covered_items': 16, 'coverage_completeness': 0.021, 'mae': 0.5, 'exact_match_rate': 0.625, 'macro_f1': 0.054, 'safety_precision': 1.0, 'safety_recall': 0.357}`

### checkpoint

- Status: `skipped`
- Reason: No checkpoint path provided.

### semantic_safety

- Status: `skipped`
- Reason: Semantic evaluation skipped by flag.

### llm_primary

- Status: `skipped`
- Reason: HF_TOKEN not configured.

### llm_baselines

- Status: `skipped`
- Reason: HF_TOKEN not configured.
