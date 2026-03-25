# ManoVarta Phase 1 Package

This folder contains the Phase 1 / Milestone 1 proposal package for:

**ManoVarta: Multilingual Conversational AI Chatbot for Mental Health Screening**

The package is written as a research-oriented student proposal, not as a completed system report. The project scope is intentionally limited to a text-first bilingual screening support tool grounded in PHQ-9 and GAD-7.

## Files Included

- `phase1_report_acl.docx`  
  Submission-style ACL-formatted report file generated from the report draft for Word/Google Docs use.

- `ManoVarta_Phase1_Presentation.pptx`  
  PowerPoint presentation generated from the slide plan with styled slides, tables, and diagrams.

- `ManoVarta_Phase1_Presentation_UBTemplate.pptx`  
  Improved presentation rebuilt on the formal UB widescreen template, with stronger charts, clearer slide structure, and better visual hierarchy. This is the recommended deck to use.

- `phase1_report.md`  
  Main Phase 1 report draft with problem formulation, research questions, data plan, architecture, baselines, evaluation, milestones, responsibilities, ethics, and limitations.

- `phase1_slides_outline.md`  
  PowerPoint-ready slide plan with lean on-slide content, suggested visuals, and speaker notes designed to avoid overcrowded slides.

- `architecture_diagram_mermaid.md`  
  Detailed and simplified Mermaid architecture diagrams plus component explanations.

- `data_schema.md`  
  Proposed pilot dataset schema, annotation protocol, and compact synthetic examples.

- `evaluation_plan.md`  
  Task definitions, metrics, baselines, ablations, and experimental design notes.

- `milestone_plan.md`  
  Phase breakdown across Milestones 1 to 3, with role split for Ritwij and Yash.

- `end_to_end_roadmap.md`  
  Practical build roadmap for turning the proposal into a text-first, deployable, end-to-end prototype with later voice support, deployment options, improvements, and gap analysis.

- `references.md`  
  Curated literature list with short relevance notes for each source.

## Core Assumptions Used Across All Files

- Languages: English + Hindi, with code-mixed Hinglish treated as an explicit subset
- Scope: text-first only; voice is future work
- Screening anchors: PHQ-9 and GAD-7
- Extension scope: CAGE-AID is optional future work, not part of the core milestone
- Pilot data: 40 synthetic patient profiles expanded into 80 conversations
- Pilot language split: 32 English, 32 Hindi, 16 code-mixed
- System design: dialogue manager + evidence/scoring engine + parallel safety module
- Preferred models: Aya Expanse 32B, Mistral NeMo 12B, optional Gemma 3 12B, IndicBERT-style safety encoder

## What This Phase Accomplishes

Phase 1 establishes the research foundation:

- a clearly scoped problem statement,
- a realistic pilot data and annotation plan,
- a modular architecture,
- a baseline and ablation strategy,
- a milestone-level execution plan,
- a grounded but careful related-work framing.
- a presentation structure that is example-driven and easy to turn into a class slide deck.
- submission-style `.docx` and `.pptx` assets that are ready for final review.

## What Still Remains for Phase 2

Phase 2 should turn the proposal into an early working prototype by:

- implementing the state-tracked dialogue flow,
- building evidence extraction and item scoring,
- adding the confidence tracker,
- implementing the safety trigger module,
- expanding and annotating the pilot dataset.

## What Should Be Manually Customized Before Submission

- Replace or confirm course-specific metadata such as team names, instructor format, week numbers, and title page style.
- Decide whether the presentation should stay at 13 slides or be compressed to match the class time limit.
- Review the Hindi and Hinglish sample text so it matches the team’s preferred register and spelling conventions.
- Add any institution-specific ethics or IRB language required by the course.
- If the instructor expects formal citation style inside the report itself, convert the author-year mentions into the required bibliography format.

## Final Reminder on Scope

The proposal is intentionally careful. It does not claim a deployed mental health system, clinical validation, or autonomous therapy capability. The strongest version of this Phase 1 submission is one that looks credible, testable, and honest about limits.
