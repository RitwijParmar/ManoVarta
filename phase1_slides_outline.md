# ManoVarta PowerPoint-Ready Slide Plan

This version is designed to be directly transferable into a PowerPoint deck. Each slide is intentionally light on text and includes a suggested visual so the presentation stays clear and self-contained.

## Slide 1: Title

**Goal**  
Introduce the project and set expectations.

**On-Slide Content**

- ManoVarta
- Multilingual Conversational AI for Mental Health Screening
- English + Hindi | Text-first | Phase 1 proposal

**Suggested Visual**  
A simple three-block banner: `conversation -> evidence -> clinician summary`.

**Speaker Notes**  
Open with the one-sentence pitch: this is a bilingual screening support system that tries to make symptom elicitation more conversational while still staying grounded in PHQ-9 and GAD-7. Mention immediately that it is not a therapy bot or diagnosis system.

## Slide 2: Why This Problem

**Goal**  
Show the motivation without overcrowding the slide.

**On-Slide Content**

| Direct form problem | Why conversation may help |
| --- | --- |
| survey fatigue | more natural disclosure |
| guarded answers | room for follow-up |
| rigid item order | adaptive symptom coverage |

**Suggested Visual**  
A side-by-side comparison table with an icon for each row.

**Speaker Notes**  
Do not read the table line by line. Use it as a visual anchor and explain that the research question is whether conversation can improve disclosure without losing the structure clinicians need.

## Slide 3: Objective and Scope

**Goal**  
Make the project boundaries explicit.

**On-Slide Content**

| In scope | Out of scope for Phase 1 |
| --- | --- |
| English + Hindi text chat | voice assistant |
| PHQ-9 and GAD-7 grounding | therapy or diagnosis |
| item-level score inference | production deployment |

**Suggested Visual**  
A clean two-column scope table with green and gray sections.

**Speaker Notes**  
This slide matters because it keeps the proposal realistic. The strongest academic proposal here is one that is narrow and testable.

## Slide 4: Research Questions

**Goal**  
Present the academic core of the project.

**On-Slide Content**

1. Can natural dialogue recover PHQ-9 and GAD-7 item scores?
2. Does confidence-based follow-up improve coverage?
3. Is performance stable across English, Hindi, and Hinglish?

**Suggested Visual**  
Numbered callout boxes or a three-card layout.

**Speaker Notes**  
You can mention the evidence-first question verbally here even if it is not another full bullet on the slide. Keep the slide itself clean.

## Slide 5: Example Conversation to Structured Output

**Goal**  
Use one concrete example so the audience immediately understands the task.

**On-Slide Content**

**Conversation snippet**  
User: "My sleep schedule is messed up and I can't focus on assignments."

**Expected structured output**

| Evidence span | Item | Score |
| --- | --- | --- |
| sleep schedule is messed up | PHQ-9 sleep | 2 |
| can't focus on assignments | PHQ-9 concentration | 2 |

**Suggested Visual**  
A left-to-right pipeline: chat bubble -> highlighted spans -> two item score cards.

**Speaker Notes**  
This should be the slide you spend the most explanation on. Walk through how one natural utterance becomes evidence, a score proposal, and a follow-up decision.

## Slide 6: Data Plan

**Goal**  
Show that the pilot dataset is substantial but still believable.

**On-Slide Content**

| Subset | Conversations |
| --- | --- |
| English | 32 |
| Hindi | 32 |
| Hinglish | 16 |

- 40 synthetic patient profiles
- 80 total conversations
- public datasets only for auxiliary validation and safety checks

**Suggested Visual**  
A small bar chart or stacked bar showing the three language subsets.

**Speaker Notes**  
Stress that this is pilot data, not a clinical corpus. The point is controlled coverage and careful annotation, not inflated scale.

## Slide 7: Annotation Workflow

**Goal**  
Show rigor in the data methodology.

**On-Slide Content**

`profile design -> dialogue drafting -> double annotation -> consensus review`

**Suggested Visual**  
A four-step horizontal process diagram. Add tiny labels under each step: `PHQ/GAD labels`, `evidence spans`, `safety flag`.

**Speaker Notes**  
This slide is useful because it makes the proposal feel like a real research plan instead of only an architecture idea.

## Slide 8: System Architecture

**Goal**  
Explain the three-layer system clearly.

**On-Slide Content**

- Rapport-aware dialogue manager
- Evidence and scoring engine
- Parallel safety trigger module

**Suggested Visual**  
Use the simplified Mermaid architecture from [architecture_diagram_mermaid.md](/Users/ritwij/Documents/multilingualChatbot/architecture_diagram_mermaid.md).

**Speaker Notes**  
Point to the parallel safety path explicitly. That design choice is important because safety should not depend on the main scoring model being correct.

## Slide 9: Model Stack

**Goal**  
Justify the model choices in one glance.

**On-Slide Content**

| Component | Model |
| --- | --- |
| main dialogue + evidence | Aya Expanse 32B |
| open comparison | Mistral NeMo 12B |
| optional second baseline | Gemma 3 12B |
| safety encoder | IndicBERT-style model |

**Suggested Visual**  
A compact four-row model stack table.

**Speaker Notes**  
Keep the explanation practical: Aya is chosen for multilingual strength, Mistral NeMo for a realistic open comparison, and the encoder is separated for Hindi-sensitive safety monitoring.

## Slide 10: Evaluation Plan

**Goal**  
Show that success is measurable.

**On-Slide Content**

| Metric | Why it matters |
| --- | --- |
| item-level MAE / macro-F1 | score quality |
| evidence support rate | interpretability |
| safety recall / precision | risk detection |
| disclosure efficiency | conversational usefulness |

**Suggested Visual**  
A metric table with icons or a 2x2 dashboard layout.

**Speaker Notes**  
Define disclosure efficiency verbally as how quickly uncertain symptom items become confidently resolved.

## Slide 11: Baselines and Ablations

**Goal**  
Make the experiment design feel serious.

**On-Slide Content**

| Comparison set | Purpose |
| --- | --- |
| direct questionnaire | strongest structured baseline |
| fixed scripted chatbot | conversation without adaptivity |
| single-pass transcript scoring | no evidence-first reasoning |
| no confidence / no safety | ablation checks |

**Suggested Visual**  
A comparison matrix with checkmarks for `adaptive`, `evidence-first`, and `safety-aware`.

**Speaker Notes**  
The main message is that the project is evaluating design choices, not only showcasing one model.

## Slide 12: Risks and Ethics

**Goal**  
Show that the team understands the limits.

**On-Slide Content**

- small pilot data
- synthetic vs real-world gap
- Hindi nuance and code-mixing
- human oversight required for safety

**Suggested Visual**  
A four-row risk table with one mitigation per risk.

**Speaker Notes**  
This slide should sound candid, not defensive. Acknowledge safety, privacy, and clinical-boundary concerns plainly.

## Slide 13: Milestones and Team Split

**Goal**  
Close with execution and ownership.

**On-Slide Content**

| Phase | Main output |
| --- | --- |
| Phase 1 | proposal + data/eval design |
| Phase 2 | prototype pipeline + pilot expansion |
| Phase 3 | experiments + demo + final report |

Ritwij: inference, evaluation, integration  
Yash: data, annotation, dialogue, architecture

**Suggested Visual**  
A three-step timeline plus two role cards.

**Speaker Notes**  
End with a concrete next step, such as finalizing the annotation rubric and creating the first pilot batch of conversations. That leaves the audience with momentum instead of just a summary.

## Slide 14: Selected References

**Goal**  
Keep the deck self-contained without turning the talk into a bibliography reading.

**On-Slide Content**

- Kroenke et al. (2001) - PHQ-9
- Spitzer et al. (2006) - GAD-7
- Dosovitsky et al. (2021) - chatbot PHQ-9
- Abd-Alrazaq et al. (2020) - mental health chatbot review
- Burdisso et al. (2024) - DAIC-WOZ evaluation caution
- Kakwani et al. (2020) - IndicNLPSuite
- Zirikly et al. (2019) - suicide-risk shared task

**Suggested Visual**  
A simple reference list slide using the template styling only. No extra graphics needed.

**Speaker Notes**  
You do not need to spend time reading this slide during the talk. It is mainly for submission completeness and for giving the deck a visible reference trail.

## Presentation Reminders

- Keep most slides to one visual plus two or three short points.
- Use Slide 5 and Slide 8 as your anchor slides; those are the best places to slow down.
- Do not read tables aloud cell by cell. Use them as evidence while you explain the bigger point.
- If time is short, compress Slides 7 and 9 into Slides 6 and 8 rather than cramming more text onto each slide.
