# Gap And Improvement Scope Assessment

## Purpose

This document identifies the main gaps between the current ManoVarta prototype and a strong final product for the multilingual mental-health screening project. It also scopes the improvement work so we can use the current system efficiently instead of restarting from scratch.

## Current Strengths

The repo already has strong foundations:

- multilingual text-first screening support for English, Hindi, and Hinglish
- PHQ-9 and GAD-7 item mapping
- evidence-first extraction and scoring
- hybrid heuristic + LLM extraction path
- separate safety checks
- DAIC-WOZ ingestion support for auxiliary English supervision
- held-out evaluation artifacts
- a new dialogue graph planner with topic state, stage, and next-action policy

This means the project is no longer missing the basic architecture. The remaining work is mostly about:

- product completeness
- assignment compliance polish
- stronger training data and evaluation
- better runtime experience

## Gap Summary

### P0 Gaps: Required for a strong, compliant product

1. Voice capability is still incomplete
- The assignment explicitly asks for a voice-capable conversational agent.
- The README mentions a browser voice wrapper, but the final product path still needs a robust English/Hindi STT and TTS flow.

2. Aya continuation training has not been completed with the new compact target mix
- The best extractor result is Aya, but the final planned continuation run on:
  - multilingual curated data
  - oversampled Hindi/Hinglish hard cases
  - optional DAIC English auxiliary data
  has not yet been completed end-to-end.

3. The planner is implemented in runtime, but not yet surfaced cleanly in the web product
- The backend now exposes dialogue stage, topic, next action, and held-back items.
- The web experience does not yet fully present this state as part of a polished product.

4. Assignment metrics still need product-facing reporting
- We must explicitly report:
  - Disclosure Efficiency
  - Safety Accuracy
  - Latency
  - Discourse Effectiveness
- The repo has useful evaluation components, but the final reporting still needs to be aligned to those exact terms.

### P1 Gaps: High-value improvements for quality and trust

5. Confidence is computed, but not yet fully productized
- Confidence drives planning already.
- The user-facing or clinician-facing interface still needs a confidence view:
  - resolved areas
  - low-confidence areas
  - review-required areas

6. Safety escalation copy and routing need final hardening
- The system already has safety logic.
- It still needs a finalized escalation flow:
  - review vs urgent scripts
  - crisis interruption behavior
  - human review handoff
  - official 988 wording for U.S. use

7. Hinglish should be framed as robustness, not core compliance
- This is not a technical gap, but a presentation gap.
- The compliant scope should remain:
  - English
  - Hindi
- Hinglish should be positioned as:
  - real-world robustness
  - code-mixed support
  - bonus usability layer

### P2 Gaps: Bonus product polish

8. Clinician summary view needs better polish
- The repo can already export structured summaries.
- The final product should show:
  - evidence snippets
  - item scores
  - confidence
  - unresolved topics
  - safety state

9. Linguistic personalization is still shallow
- The planner supports language and topic control.
- The product could be improved by mirroring:
  - user pacing
  - verbosity
  - code-mix level
  - directness versus softness

10. Gamified or disclosure-support nudges are not yet implemented
- This is a bonus-only path.
- It should stay subtle and supportive, not gimmicky.

## Architectural Gap Analysis

### What is now solved

The biggest old architectural gap was that follow-up selection behaved like a checklist. That has now been improved through the new dialogue graph planner:

- topic graph
- topic confidence
- dialogue stage
- target topic
- next action
- hold-back logic for sensitive safety questions

This means the project is no longer missing its core Task 1 backbone.

### What still needs to be strengthened

The architecture still needs a cleaner full-stack story:

1. `Planner`
- already present and functional
- needs stronger UI integration and logging

2. `Inference engine`
- Aya is the right main path
- needs continuation fine-tuning and new evaluation

3. `Safety supervisor`
- present
- needs stricter product scripts and final escalation UX

4. `Voice layer`
- conceptually present
- still needs final integrated implementation

5. `Presentation layer`
- must show planner-guided interaction as a feature, not hide it

## Data And Model Gaps

### Current data strengths

- curated multilingual synthetic set exists
- Hindi and Hinglish are already represented
- contradictions and safety-sensitive language are already included
- DAIC-WOZ support exists for English auxiliary supervision

### Current data weaknesses

1. Hindi and Hinglish hard cases still need stronger oversampling
- deny-then-reveal
- somatic phrasing
- short evasive replies
- contradictory turns
- indirect distress language
- mixed-language ambiguity

2. DAIC-WOZ should remain auxiliary
- It helps English calibration.
- It should not dominate the multilingual identity of the system.

3. Voice data path is underdeveloped
- The assignment expects audio recordings too.
- The current system is stronger on text than on bilingual voice data handling.

## Evaluation Gaps

### What we already have

- multilingual held-out evaluation artifacts
- extractor metrics like coverage, MAE, exact match, macro-F1
- safety metrics in existing reports

### What is still missing

1. Assignment-language evaluation packaging
- We need a final report that explicitly names:
  - Disclosure Efficiency
  - Safety Accuracy
  - Latency
  - Discourse Effectiveness

2. Conversation-policy evaluation
- The new planner should also be evaluated on:
  - whether it stays on topic
  - whether it asks too many questions in one area
  - whether it over-triggers safety
  - whether it reaches stable scores faster

3. Voice-path evaluation
- STT latency
- TTS latency
- transcription robustness for Hindi and Hinglish

## Productization Gaps

### Product story is strong but not fully polished

The strongest product story is:

- a multilingual screening partner
- not a therapist
- not a diagnostic replacement
- evidence-first scoring
- confidence-aware adaptive questioning
- separate safety supervision
- clinician-friendly summary

This story is already consistent technically.

What remains is polish:

- stronger landing/demo copy
- visible confidence and coverage states
- clear “human review” and “urgent escalation” UX
- integrated voice demo path

## Improvement Scope

### Phase A. Must-do scope

1. Finish Aya continuation training
- train on:
  - curated multilingual set
  - oversampled Hindi/Hinglish hard cases
  - optional capped DAIC English subset
- re-evaluate on the multilingual held-out set

2. Productize planner outputs
- show current topic
- show confidence state
- show unresolved branches
- expose why the next question is being asked

3. Complete voice capability
- STT for English and Hindi
- TTS for English and Hindi
- transcript logging for evaluation

4. Finalize assignment-aligned evaluation bundle
- explicitly compute and present:
  - Disclosure Efficiency
  - Safety Accuracy
  - Latency
  - Discourse Effectiveness

### Phase B. High-value scope

5. Safety UX hardening
- urgent interruption copy
- review handoff copy
- human escalation flow
- official crisis resources

6. Clinician summary polish
- more readable evidence panels
- clearer confidence/risk presentation
- exportable session summaries

7. Better language adaptation
- use Hinglish as style adaptation, not a compliance axis
- preserve English/Hindi as the official system languages

### Phase C. Bonus scope

8. Personalization layer
- pace matching
- verbosity matching
- code-mix matching

9. Disclosure nudges
- gentle prompts to encourage richer narratives

10. Analytics and audit logs
- planner action logs
- topic coverage history
- escalation traceability

## Recommended Next Task Order

1. Aya continuation training and held-out re-evaluation
2. Planner state integration into the web product
3. Voice-capable browser demo
4. Assignment-aligned final evaluation/reporting
5. Safety and clinician-summary polish

## Bottom Line

The project is no longer missing its core architecture. The biggest remaining work is not inventing a new system; it is finishing and polishing the one already built:

- strengthen Aya with targeted continuation training
- complete the voice path
- expose the planner cleanly in the product
- align evaluation to the assignment wording
- tighten safety and summary UX

That is the most efficient path to a strong final product.
