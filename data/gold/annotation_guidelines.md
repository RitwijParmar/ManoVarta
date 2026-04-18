# Annotation Guidelines

## Goal

Label each conversation at the item level for:

- `PHQ-9`
- `GAD-7`
- safety escalation

The purpose is to create a small but defensible bilingual gold set for strict assignment compliance.

## General rules

1. Label only what is supported by the transcript and linked profile notes.
2. Use the same recall window as the target instruments:
   - last two weeks, unless a transcript clearly states a different window
3. Record evidence for every non-zero label.
4. If evidence is weak, ambiguous, or contradictory, mark lower confidence and explain why.
5. Do not infer from style alone.
6. If the user describes a symptom in metaphorical, somatic, or code-mixed language, score the clinical construct only if the meaning is still clear.

## Item scoring

Use the standard `0-3` frequency scale:

- `0`: no supported symptom presence in the recall window
- `1`: present on some days / limited frequency
- `2`: present often / around half or more of the days
- `3`: present nearly daily / persistent or dominant in the window

When frequency is not explicit:

- map from narrative intensity cautiously
- prefer lower confidence rather than overstating

## PHQ-9 item mapping

Use these paraphrased domains:

- `phq_q1_anhedonia`: reduced interest or reduced enjoyment
- `phq_q2_low_mood`: sadness, hopelessness, emotional heaviness
- `phq_q3_sleep`: insomnia, broken sleep, oversleeping, sleep disruption
- `phq_q4_fatigue`: low energy, exhaustion, slowed activation
- `phq_q5_appetite`: reduced or increased appetite
- `phq_q6_worthlessness`: guilt, failure, burden, low self-worth
- `phq_q7_concentration`: distractibility, slowed focus, rereading, mental fog
- `phq_q8_psychomotor`: slowed down or noticeably restless/agitated behavior
- `phq_q9_self_harm`: passive death wish, self-harm thoughts, not wanting to be alive

## GAD-7 item mapping

- `gad_q1_nervous`: ongoing nervousness, edge, dread
- `gad_q2_control_worry`: difficulty stopping or controlling worry
- `gad_q3_excessive_worry`: worry spreading across multiple concerns
- `gad_q4_trouble_relaxing`: inability to settle, quiet thoughts, or relax body
- `gad_q5_restlessness`: pacing, inner agitation, urge to move
- `gad_q6_irritability`: irritation, snapping, anger threshold reduced
- `gad_q7_afraid`: fear that something bad will happen

## Evidence format

For each item with supporting evidence, record:

- `evidence_quote`
- `speaker`
- `turn_id`
- optional `evidence_start_char` and `evidence_end_char`

If the evidence comes from multiple places, record the strongest one and mention the others in notes.

## Contradiction handling

If the speaker contradicts themselves:

- keep both the contradiction note and the final score
- explain which evidence you trusted more and why
- use lower confidence if the contradiction remains unresolved

## Confidence guidance

- `high`
  - direct symptom statement with timing/frequency or strong concrete example
- `medium`
  - symptom is likely but indirect, metaphorical, or only partly grounded
- `low`
  - weak evidence, conflicting evidence, or unclear time window

## Safety labeling

Every session must also include a safety level:

- `none`
- `review`
- `urgent`

Use `review` for passive death-wish, disappearance, burden-plus-withdrawal, or concerning ambiguity.
Use `urgent` for active self-harm intent, planning, or immediate danger cues.

## Annotation workflow

1. Annotator A labels independently.
2. Annotator B labels independently.
3. Compare all item values and safety labels.
4. Adjudicator resolves disagreements.
5. Save one adjudicated final file in `labels/`.

## Minimum adjudication rules

Escalate to adjudication whenever:

- item scores differ by `>= 1`
- safety labels differ
- evidence quote choice differs materially
- one annotator uses `low` confidence on an item scored `2` or `3`

## What not to do

- do not treat synthetic seed data as gold data
- do not label from the bot question alone
- do not upscore just because the conversation feels emotionally intense
- do not use DAIC auxiliary labels as if they covered all final target items
