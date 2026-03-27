# ManoVarta Data Nuance Strategy

## Purpose

This note explains how nuance is added to the synthetic screening corpus without simply inflating the sample count. The goal is to make the dataset harder and more realistic in ways that matter for conversational screening: guarded disclosure, mixed language use, indirect symptom wording, contradiction across turns, and subtle safety cues.

## Current corpus design

The working corpus now has two layers:

- `48` curated conversations tied to `48` profiles
- `132` silver variants derived from the curated set
- `180` total conversations
- balanced language distribution: `60` English, `60` Hindi, `60` Hinglish

This split is deliberate. The curated layer is the stronger reviewed subset. The silver layer is meant to widen behavioral coverage without pretending every added sample has the same annotation strength.

## Why nuance matters here

The project is not trying to classify neat survey answers. It is trying to infer PHQ-9 and GAD-7 aligned item signals from open conversation. That means the dataset has to cover more than severity labels. It also has to cover how people actually disclose, hedge, correct themselves, switch languages, or avoid direct symptom words.

## Research grounding

The current nuance choices are guided by the project's reference set:

- `Dosovitsky, Kim, and Bunge (2021)` supports the idea that chatbot-based screening is worth studying, but it does not remove the need for natural language variation. That motivates moving beyond clean questionnaire-style answers.
- `Burdisso et al. (2024)` is a caution that mental-health models can overfit interview structure and prompt artifacts. That is one reason the corpus deliberately varies response style, disclosure timing, and follow-up shape.
- `Kakwani et al. (2020)` motivates using Hindi-sensitive resources instead of assuming English transfer will be enough.
- `Nayak and Joshi (2022)` motivates treating Hinglish as a real code-mixed setting rather than noisy Hindi or noisy English.
- `Zirikly et al. (2019)` and `Pichowicz, Kotas, and Piotrowski (2025)` motivate including safety expressions that are not always explicit from the first turn.

## Nuance dimensions used in the corpus

Each profile or variant should differ along several axes, not just language:

- disclosure timing: open, guarded, delayed, deny-then-reveal
- symptom framing: direct, indirect, somatic, functional, metaphorical
- contradiction style: consistent, minor revision, clear self-correction
- language behavior: monolingual English, monolingual Hindi, Hinglish with affect/context code-switching
- engagement style: narrative, short answers, fragmented, low-effort
- context: exams, debt, job pressure, caregiving, breakup, relocation, hostel isolation, family conflict
- safety expression: none, passive disappearance, burden language, explicit self-harm mention

## How the silver variants are built

The silver variants are not random paraphrases. They preserve the original symptom evidence and label structure while changing disclosure behavior.

Three main variant families are used:

- `guarded_minimize`
  The user initially downplays distress or says they are "managing," then reveals stronger symptoms after a follow-up.

- `functional_masking`
  The user foregrounds work, studies, family duty, or tiredness before naming emotional difficulty.

- `temporal_self_correction`
  The user gives an incomplete or minimizing answer early and corrects it later, which forces the scorer to handle contradiction and recency.

## Hindi and Hinglish additions

The expanded set adds language-specific patterns rather than only translating English examples:

- Hindi somatic wording such as body heaviness, restlessness, or "dimag band nahi hota"
- stigma-shaped Hindi phrasing where distress is described indirectly
- Hinglish turns where emotional content and functional content appear in different languages
- code-mixed clarification turns where the user becomes more direct after rapport improves

## Safety additions

Safety variation is also deliberate. The corpus now includes:

- passive disappearance language
- burden-oriented wording
- hopeless future framing
- ambiguous review-level cues that become clearer later
- a smaller set of urgent direct statements

This matters because a screening tool should not rely only on explicit self-harm phrasing.

## Rules for future additions

- avoid literal English-to-Hindi translation as the main source of Hindi data
- avoid making every user cooperative and emotionally articulate
- avoid adding silver variants that change the underlying symptom label without explicit review
- keep the curated layer separate from the silver layer in evaluation reporting
- prefer adding new disclosure styles and contexts over repeating the same symptom pattern with different names

## Architecture impact

The current architecture already fits this richer data reasonably well:

- the dialogue planner can keep asking unresolved high-priority items,
- the hybrid scorer can surface contradictions,
- the safety module stays parallel to the main scorer.

The two architecture refinements still worth keeping in mind are:

- a more explicit coverage planner that tracks which PHQ-9 and GAD-7 items still need evidence,
- a stricter abstain or human-review gate when contradiction remains unresolved.
