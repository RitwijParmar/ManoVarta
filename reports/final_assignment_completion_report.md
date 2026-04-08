# Final Assignment Completion Report

- Generated: `2026-04-08T08:38:35Z`
- Shipped baseline tag: `shipped-baseline-2026-04-04`

## Requirement Status

- Multilingual text chat: `complete` (`English`, `Hindi`, plus `Hinglish` robustness support)
- Voice-capable agent: `complete`
- Patient profile onboarding: `complete`
- Clinical knowledge base: `complete`
- Task 1 smart screening: `complete`
- Task 2 LLM inference engine: `complete`
- Task 3 safety trigger system: `complete`
- Deployment assets in repo: `partial`
- Bonus implemented: `gamification, linguistic_personalization`

## Voice Capability

- Browser voice controls present: `True`
- Browser speech-to-text present: `True`
- Browser text-to-speech present: `True`
- Cloud speech-to-text route present: `True`
- Cloud text-to-speech route present: `True`
- Transcript-before-submit flow present: `False`
- Note: Voice now supports backend Google Cloud STT/TTS for English, Hindi, and Hinglish-oriented use, with browser speech kept as a fallback wrapper.

## Evaluation & Validation

### Disclosure Efficiency

- Stable item traces measured: `96`
- Average user turns to stable score: `2.292`
- Median user turns to stable score: `2.0`

### Safety Accuracy

- Precision: `1.0`
- Recall: `1.0`
- F1: `1.0`

### Latency

- Cold-start turn latency: `7.0 ms`
- Warm average turn latency: `8.77 ms`
- Warm median turn latency: `9.73 ms`
- Warm p95 turn latency: `10.34 ms`

### Bonus Validation

- Nudge feedback loop present: `True`
- First brief-turn nudge queue: `anxiety, example, impact`
- Nudged touched-item delta in smoke validation: `3`
- Nudge words added: `17`
- Nudge evidence gain: `3`
- Nudge resolved-item gain: `0`
- Nudge outcome: `helpful`
- Style checks: `{'brief_guarded_guided': True, 'hindi_continuity_note': True, 'hinglish_code_mix_high': True}`
- Note: Validation uses local API smoke sessions plus stored nudge events to confirm that nudges feed back into dialogue state, increase narrative detail, and that continuity and code-mix cues reach the planner for English, Devanagari Hindi, and Hinglish turns.

### Discourse Effectiveness

- Coverage completeness: `0.783`
- Exact match rate: `0.639`
- Macro-F1: `0.251`
- Parse failures: `0`

## Deployment

- Dockerfile: `True`
- Docker Compose demo stack: `True`
- Render blueprint: `True`
- Shipped bundle: `False`
- Public runtime URL: `https://manovarta-runtime-122722888597.us-east4.run.app`
- Live hybrid safety enabled: `True`
- Live cloud voice enabled: `True`
- Note: Repo includes local container deployment, cloud deployment configuration, and a live public runtime whose config is mirrored here.

## Bonus

- Implemented: `gamification, linguistic_personalization`
- Note: The product now combines adaptive nudges with backend feedback tracking, continuity-aware context, and steering that adapts to pacing, openness, burden, and code-mix.

## Final Note

- None. The public runtime is live at https://manovarta-runtime-122722888597.us-east4.run.app.
