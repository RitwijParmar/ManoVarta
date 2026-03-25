# ManoVarta Architecture Diagram

This file contains two Mermaid diagrams:

1. a detailed research architecture for the report, and
2. a cleaner simplified version for slides.

Both versions keep the same core idea: a multilingual dialogue pipeline with a rapport-aware manager, an evidence-based scoring engine, and a parallel safety module.

## Detailed Version

```mermaid
flowchart TD
    A["User message (English / Hindi / Hinglish)"] --> B["Input normalization and language ID"]
    B --> C["Conversation state store"]
    B --> D["Parallel safety trigger module"]
    C --> E["Rapport-aware dialogue manager"]
    C --> F["Clinical evidence and scoring engine"]

    E --> E1["Coverage tracker"]
    E --> E2["Follow-up policy"]
    E --> E3["Response composer"]

    F --> F1["Evidence span extractor"]
    F1 --> F2["PHQ-9 item mapper"]
    F1 --> F3["GAD-7 item mapper"]
    F2 --> F4["Item score proposal (0-3)"]
    F3 --> F4
    F4 --> F5["Confidence tracker"]
    F5 --> C

    D --> D1["Risk cue retrieval / encoder scoring"]
    D1 --> D2["Safety level: none / review / urgent"]
    D2 --> C
    D2 --> H["Human review / escalation path"]

    C --> G["Stop-or-continue decision"]
    G -->|continue| E
    E3 --> I["Assistant follow-up or summary"]
    I --> A

    G -->|enough coverage + stable confidence| J["Clinician-facing screening summary"]
    F5 --> J
    D2 --> J
```

## Simplified Slide Version

```mermaid
flowchart LR
    U["User"] --> M["Rapport-aware dialogue manager"]
    U --> S["Safety trigger module"]
    M --> E["Evidence and scoring engine"]
    E --> O["PHQ-9 / GAD-7 item scores + confidence"]
    S --> O
    O --> R["Clinician-facing summary / escalation"]
```

## Component Notes

### 1. Input normalization and language ID

This step standardizes text, handles script variation where possible, and records whether the turn is primarily English, Hindi, or code-mixed. It should be lightweight and auditable.

### 2. Rapport-aware dialogue manager

This module decides how the system should respond conversationally. It keeps track of which symptoms have already been covered, what still needs clarification, and when to stop asking questions. The goal is supportive but bounded dialogue, not free-form counseling.

### 3. Clinical evidence and scoring engine

This module turns raw user statements into structured symptom evidence. It identifies relevant snippets, maps them to PHQ-9 and GAD-7 items, proposes item-level scores, and updates confidence after each turn.

### 4. Confidence tracker

The confidence tracker stores how certain the system is about each item. If confidence is low or contradictory evidence appears, the dialogue manager should prefer follow-up questions. If confidence becomes stable across items, the conversation can close.

### 5. Safety trigger module

This module runs independently of the main scoring path. It monitors for crisis-sensitive language and should be optimized for recall. It can trigger review even if the symptom scoring engine is uncertain.

### 6. Clinician-facing summary

The final output is a structured screening artifact, not a diagnosis. It should include item scores, confidence levels, supporting evidence, unresolved items, and any safety escalation flags.

## Why This Diagram Fits the Proposal

- It shows the three required layers explicitly.
- It makes safety parallel rather than downstream.
- It supports evidence-first scoring instead of hidden one-shot prediction.
- It is simple enough to paste into a Markdown report or slide deck later.
