# Architecture

ManoVarta is structured as a controller-led conversational screening stack rather than a single prompt chain.

## Core layers

1. Web client
   - Browser chat UI
   - Browser voice controls
   - Live PHQ-9 / GAD-7 progress display
2. API runtime
   - FastAPI session management
   - Runtime config inspection
   - Async scoring queue integration
3. Dialogue planner
   - Topic sequencing
   - Follow-up selection
   - Fatigue / repetition control
   - Summary and safety routing
4. Scoring engine
   - Heuristic evidence extraction
   - Hybrid merge with remote extractor output
   - PHQ-9 / GAD-7 item state updates
5. Safety stack
   - Rules
   - Local safety checkpoint
   - Review / urgent escalation path
6. Model backends
   - Vertex/Gemini for live conversational phrasing and analysis
   - Remote trained Aya extractor for evidence-heavy structured scoring

## Why this split exists

Early end-to-end prompting sounded fluent but under-covered the screening graph and repeated itself too often. The current split keeps conversation control inside the application and uses models only for the roles where they perform best.

## Current live pattern

- Live reply path: `gemini-3-flash-preview`
- Live analysis path: `gemini-3-pro-preview`
- Extraction path: remote trained Aya
- Safety path: local checkpoint + rules

## Main design principle

The application decides what information is still missing. The models help phrase, interpret, and score, but they do not own the entire workflow.
