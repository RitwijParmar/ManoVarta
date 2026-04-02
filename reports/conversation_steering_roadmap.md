# Conversation Steering Roadmap

## Goal

Build ManoVarta as a multilingual mental-health **screening partner** that feels warm and natural while still producing structured PHQ-9 and GAD-7 evidence, confidence, and safety outputs. The assignment asks for English plus one other language, so the compliant product target remains **English + Hindi**, with **Hinglish** presented as a robustness layer rather than the second required language.

## Why The Planner Matters

The biggest product risk is not raw score prediction. It is whether the chatbot can decide the **next best move** naturally and safely:

- when to stay open-ended
- when to narrow into a symptom probe
- when to stop circling and move forward
- when to ask a safety question
- when to summarize rather than over-question

Recent work on counseling-style agents suggests that high-quality long-form interaction comes from explicit **state inference and topic control**, not just better next-turn generation. For ManoVarta, that means the product should rely on:

- a dialogue state graph
- topic-level confidence tracking
- a policy layer that chooses the next action
- a generator that phrases the selected action naturally

## Research Principles Behind The Product

### 1. State tracking beats free-form generation alone

- CAMI uses explicit state inference and topic exploration to improve counselor-like responses.
- CALM-IT shows that long conversations improve when the agent models evolving conversational state instead of treating each turn independently.

Implication for ManoVarta:

- keep the LLM for language and evidence extraction
- add a planner that explicitly tracks stage, topic, and confidence

## 2. Assessment should stay partly structured

A 2024 mental-health assessment study found that conversational systems benefit from keeping the **assessment portion structured**, because users perceive that phase as more credible. That does not mean a cold questionnaire; it means:

- warm opening
- natural exploration
- focused question at the right time
- structured scoring behind the scenes

Implication for ManoVarta:

- conversation should feel natural
- symptom coverage should still be explicit and measurable

## 3. Uncertainty and human fallback matter

Healthcare chatbot evaluation guidance emphasizes that good systems expose **trustworthiness**, not only fluency. Recent healthcare and mental-health work also shows that users trust systems more when there is:

- visible uncertainty or confidence
- bounded use claims
- a human fallback path

Implication for ManoVarta:

- confidence is a first-class output, not a hidden score
- safety must stay separate from the main LLM
- human escalation remains part of the product

## Current Gaps

### Gap 1. The old planner was item-first, not topic-first

The previous follow-up flow mostly picked the next unresolved questionnaire item. That works for scoring, but it does not feel like a natural conversation.

### Gap 2. Conversation stage was implicit

The runtime did not expose whether it was still building rapport, clarifying an ambiguous symptom area, or ready to summarize.

### Gap 3. Safety could interrupt too early

A review-level safety flag could push the chatbot into a self-harm check before rapport or symptom evidence justified it.

### Gap 4. Product evaluation is still more mature than product orchestration

The repo already has good extraction, scoring, and safety primitives. What was missing was the orchestration layer that makes them feel like one coherent product.

## What Was Implemented Now

The planner now exposes a real dialogue-policy layer:

- topic graph:
  - mood
  - sleep
  - energy and appetite
  - self-worth
  - focus and activation
  - anxiety
  - safety
- explicit stages:
  - rapport
  - exploration
  - clarification
  - safety
  - summary
- explicit next actions:
  - open question
  - symptom probe
  - clarify
  - risk check
  - summarize
  - handoff
- topic confidence and status:
  - pending
  - probing
  - stable
  - review
  - held back

The runtime now returns this state in the snapshot, and the response generator is prompted with:

- dialogue stage
- target topic
- next action
- planner rationale

This keeps the LLM aligned to a planned move instead of improvising from scratch.

## Recommended Product Architecture

### Layer 1. Voice and language interface

- text input stays available
- add speech-to-text for English and Hindi
- add text-to-speech for English and Hindi

### Layer 2. Dialogue planner

Responsibilities:

- maintain conversation stage
- select target topic
- hold back sensitive branches until appropriate
- escalate when safety requires it

### Layer 3. Aya evidence and scoring engine

Responsibilities:

- extract evidence snippets from transcript turns
- infer item scores `0-3`
- emit per-item confidence
- support English, Hindi, and Hinglish

### Layer 4. Safety supervisor

Responsibilities:

- detect self-harm or crisis cues
- override the normal planner when needed
- route to human review or urgent escalation

### Layer 5. Clinician summary layer

Responsibilities:

- show evidence quotes
- show item scores
- show confidence
- show unresolved topics
- show safety flags

## Training Plan For Aya

Continue fine-tuning Aya rather than starting over.

### Training mix

- 60-70% curated multilingual ManoVarta data
- 20-25% oversampled Hindi and Hinglish hard cases
- 10-20% DAIC-WOZ auxiliary English subset

### Hard cases to oversample

- deny-then-reveal patterns
- vague distress
- somatic phrasing in Hindi
- code-mixed Hinglish
- contradictory evidence across turns
- short user answers that need clarification
- emotional escalation

### Target format

Use a compact evidence-first target:

- `item_id`
- `value`
- `evidence_snippets`
- `confidence`
- `safety_level`

Avoid verbose note fields in the main training target. They cost tokens and make schema control harder.

### Evaluation

Primary evaluation:

- main multilingual held-out set

Secondary evaluation:

- DAIC-WOZ side report for English calibration

Do not replace the main multilingual benchmark with DAIC-WOZ.

## Product Roadmap

### Phase 1. Planner and graph control

Status: implemented in the runtime.

Next work:

- expose planner state in the web UI
- visualize topic confidence and unresolved branches
- log planner actions for review

### Phase 2. Aya continuation training

Objectives:

- improve Hindi and Hinglish calibration
- improve evidence extraction on hard cases
- preserve English quality with DAIC-WOZ auxiliary support

Deliverables:

- new adapter checkpoint
- multilingual held-out evaluation
- per-language error analysis

### Phase 3. Voice-capable demo

Objectives:

- speech-to-text
- text-to-speech
- bilingual voice flow

Deliverables:

- browser voice capture
- turn transcript logging
- replayable demo session

### Phase 4. Safety and escalation hardening

Objectives:

- strengthen review versus urgent separation
- add explicit escalation scripts
- wire official crisis routing

For U.S. deployment, route urgent crisis language to official support such as [988 Lifeline](https://988lifeline.org/get-help/).

### Phase 5. Evaluation aligned to assignment language

Report these metrics explicitly:

- `Disclosure Efficiency`
  - turns required before scores stabilize
- `Safety Accuracy`
  - crisis and review detection quality
- `Latency`
  - input-to-response time
- `Discourse Effectiveness`
  - coverage of required questionnaire topics without drift

Also report:

- item-level MAE
- exact match
- macro-F1
- coverage completeness
- English/Hindi/Hinglish split

## What “Perfect” Means For This Project

For ManoVarta, “perfect” does not mean pretending to be a therapist. It means:

- natural rapport without fluff
- adaptive symptom coverage
- evidence-first scoring
- visible confidence
- restrained safety behavior that still catches urgent risk
- bilingual usability
- clinician-readable output

That is the strongest path to a compliant, defensible, and genuinely strong project.

## References

- CAMI: [https://arxiv.org/abs/2502.02807](https://arxiv.org/abs/2502.02807)
- CALM-IT: [https://arxiv.org/abs/2601.10085](https://arxiv.org/abs/2601.10085)
- Assessment credibility study: [https://www.sciencedirect.com/science/article/pii/S1071581924000740](https://www.sciencedirect.com/science/article/pii/S1071581924000740)
- Mental-health assessment validity study: [https://www.sciencedirect.com/org/science/article/pii/S2291522222000419](https://www.sciencedirect.com/org/science/article/pii/S2291522222000419)
- Trust and human-fallback findings: [https://humanfactors.jmir.org/2025/1/e76377](https://humanfactors.jmir.org/2025/1/e76377)
- Clinician trust and uncertainty framing: [https://humanfactors.jmir.org/2025/1/e79658](https://humanfactors.jmir.org/2025/1/e79658)
- Healthcare conversation evaluation framework: [https://www.nature.com/articles/s41746-024-01074-z](https://www.nature.com/articles/s41746-024-01074-z)
- 988 official help page: [https://988lifeline.org/get-help/](https://988lifeline.org/get-help/)
