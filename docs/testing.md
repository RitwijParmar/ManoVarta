# Testing

## Main test groups

- `tests/test_dialogue.py`
  - Planner logic
  - Follow-up control
  - Repetition and fatigue behavior
- `tests/test_api.py`
  - Session endpoints
  - Runtime config exposure
  - Live chat behavior
- `tests/test_llm.py`
  - Extractor / responder behavior
  - Rescue and verifier logic
- `tests/test_scoring.py`
  - Evidence collection
  - Item scoring
- `tests/test_engine.py`
  - Hybrid merge behavior

## Typical focused runs

```bash
python3 -m pytest -q tests/test_dialogue.py
python3 -m pytest -q tests/test_api.py
python3 -m pytest -q tests/test_llm.py
```

## What matters most

The most failure-prone areas have been:

- branch persistence after user pushback
- live PHQ/GAD coverage updates
- Hindi / Hinglish evidence recovery
- deployment drift between good and bad live revisions

## Recommended validation pattern

1. Run focused local regressions first.
2. Deploy to a fresh revision without changing the model stack.
3. Check `/runtime/config`.
4. Run short English and Hindi live chat probes.
5. Only then trust the public behavior change.
