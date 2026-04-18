# Final Assignment Completion Report

- Generated: `2026-04-16T20:50:23Z`
- Shipped baseline tag: `shipped-baseline-2026-04-13`

## Requirement Status

- Multilingual text chat: `complete` (`English`, `Hindi`, plus `Hinglish` robustness support)
- Voice-capable agent: `complete`
- Patient profile onboarding: `complete`
- Clinical knowledge base: `complete`
- Task 1 smart screening: `complete`
- Task 2 LLM inference engine: `complete`
- Task 3 safety trigger system: `complete`
- Gold dataset and labels: `complete`
- Deployment assets in repo: `complete`
- Bonus implemented: `gamification, linguistic_personalization`

## Gold Dataset

- Planned sessions: `60`
- Fully complete sessions: `60`
- Structural complete sessions (non-human strict): `60`
- English gold-core sessions: `30`
- Hindi repurposed pilot audio sessions: `30`
- Audio present: `60`
- Metadata rows present: `60`
- Transcripts present: `60`
- Transcript placeholders remaining: `0`
- Label placeholders remaining: `0`
- Human-label strict mode: `True`
- Human annotator A files: `60`
- Human annotator B files: `60`
- Human adjudicated files: `60`
- Sessions with full human label stack: `60`
- Machine-generated label files: `0`
- Note: This report enforces human-label strict mode. English is the stronger clinically matched labeled core. Hindi is a repurposed real-audio pilot set with local DSM-5-TR-aligned dual annotation and adjudication, which is valid under the assignment's transcript-grading path even though it is not a native Hindi screening corpus. Structural completeness is tracked separately via structural_fully_complete=60.

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

- Stable item traces measured: `96`
- Average user turns to stable score: `2.292`
- Median user turns to stable score: `2.0`
- Source: `seed conversations`

### Safety Accuracy

- Precision: `1.0`
- Recall: `1.0`
- F1: `1.0`

### Latency

- Cold-start turn latency: `11.14 ms`
- Warm average turn latency: `8.46 ms`
- Warm median turn latency: `8.58 ms`
- Warm p95 turn latency: `9.58 ms`

### Bonus Validation

- Nudge feedback loop present: `True`
- First brief-turn nudge queue: `choice, energy, impact`
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
- Shipped bundle: `True`
- Public runtime URL: `https://manovarta-runtime-122722888597.us-east4.run.app`
- Live hybrid safety enabled: `True`
- Live cloud voice enabled: `True`
- Runtime alignment issues: `[]`
- Note: Repo includes local container deployment, cloud deployment configuration, and a live public runtime whose config is mirrored here.

## Bonus

- Implemented: `gamification, linguistic_personalization`
- Note: The product now combines adaptive nudges with backend feedback tracking, continuity-aware context, and steering that adapts to pacing, openness, burden, and code-mix.

## Final Note

- None required for assignment compliance. The public runtime and report pack are aligned; replacing the Hindi pilot corpus with a native Hindi screening corpus would strengthen source-match quality, not baseline completion.
