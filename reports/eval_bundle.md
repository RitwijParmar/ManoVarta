# Evaluation Bundle

- Generated: `2026-03-26T23:58:17.452258+00:00`
- Git revision: `195b64b`
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
- `follow_up_dev.jsonl`: `96` lines
- `follow_up_test.jsonl`: `144` lines
- `follow_up_train.jsonl`: `120` lines
- `safety_dev.jsonl`: `48` lines
- `safety_test.jsonl`: `48` lines
- `safety_train.jsonl`: `84` lines
- `splits.json`: `56` lines

## Reports

### heuristic

- Status: `ok`
- Overall: `{'covered_items': 63, 'coverage_completeness': 0.022, 'mae': 0.492, 'exact_match_rate': 0.635, 'macro_f1': 0.058, 'safety_precision': 1.0, 'safety_recall': 0.377}`

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
