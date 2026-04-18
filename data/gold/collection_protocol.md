# Collection Protocol

## Purpose

This protocol defines the minimum collection setup for a bilingual gold dataset that is strong enough to support the assignment claim.

## Minimum dataset target

- `30` English sessions
- `30` Hindi sessions
- balanced mix of lower-symptom, moderate, and higher-risk narratives
- varied ages and occupations when feasible

## Required fields at collection time

- session id
- participant id or pseudonymous profile id
- language
- age band or age in years
- occupation
- living situation
- support system summary
- consent confirmation
- audio recording path
- transcript path

## Session format

Each session should include:

1. short onboarding/profile capture
2. open narrative start
3. adaptive follow-up dialogue
4. closure

The conversation does not need to read out the official questionnaires verbatim, but the transcript must contain enough evidence to score the clinical items.

## Audio requirements

- one audio file per session
- clear link between audio filename and session id
- preserve the original language of speech
- if ASR is used to create transcripts, keep both the raw audio and corrected transcript

## Transcript requirements

Each transcript should preserve:

- speaker turns
- timestamps when possible
- disfluencies only when they affect meaning
- code-mixed wording rather than forced translation

## Ethics note

Do not include direct identifiers.
Use pseudonymous session ids.
Store consent separately from model-training assets when possible.

## Recommended immediate next step

Start with a small pilot pack:

- `5` English sessions
- `5` Hindi sessions

Run the full annotation + adjudication workflow on that pilot before collecting the remaining `25 + 25`.
