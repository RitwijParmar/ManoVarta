# Final Assignment Completion Report

- Generated: `2026-04-05T02:23:13Z`
- Shipped baseline tag: `shipped-baseline-2026-04-04`

## Requirement Status

- Multilingual text chat: `complete` (`English`, `Hindi`, plus `Hinglish` robustness support)
- Voice-capable agent: `complete`
- Patient profile onboarding: `complete`
- Clinical knowledge base: `complete`
- Task 1 smart screening: `complete`
- Task 2 LLM inference engine: `complete`
- Task 3 safety trigger system: `complete`
- Deployment assets in repo: `complete`
- Bonus implemented: `gamification, linguistic_personalization`

## Voice Capability

- Browser voice controls present: `True`
- Browser speech-to-text present: `True`
- Browser text-to-speech present: `True`
- Cloud speech-to-text route present: `True`
- Cloud text-to-speech route present: `True`
- Transcript-before-submit flow present: `True`
- Note: Voice now supports backend Google Cloud STT/TTS for English, Hindi, and Hinglish-oriented use, with browser speech kept as a fallback wrapper.

## Evaluation & Validation

### Disclosure Efficiency

- Stable item traces measured: `92`
- Average user turns to stable score: `2.283`
- Median user turns to stable score: `2.0`

### Safety Accuracy

- Precision: `1.0`
- Recall: `1.0`
- F1: `1.0`

### Latency

- Cold-start turn latency: `8256.38 ms`
- Warm average turn latency: `86.31 ms`
- Warm median turn latency: `95.24 ms`
- Warm p95 turn latency: `98.3 ms`

### Discourse Effectiveness

- Coverage completeness: `0.745`
- Exact match rate: `0.584`
- Macro-F1: `0.216`
- Parse failures: `0`

## Deployment

- Dockerfile: `True`
- Docker Compose demo stack: `True`
- Render blueprint: `True`
- Shipped bundle: `True`
- Public runtime URL: `https://manovarta-runtime-122722888597.us-east4.run.app`
- Live hybrid safety enabled: `True`
- Live cloud voice enabled: `True`
- Note: Repo includes local container deployment, cloud deployment configuration, and a live public runtime whose config is mirrored here.

## Bonus

- Implemented: `gamification, linguistic_personalization`
- Note: The product now combines adaptive nudges for richer narrative disclosure with backend personalization based on pacing, openness, and code-mix.

## Final Note

- None. The public runtime is live at https://manovarta-runtime-122722888597.us-east4.run.app.
