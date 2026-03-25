# ManoVarta Milestone Plan

## Project Framing

This project is divided into three phases so that the scope stays realistic for a graduate course. Phase 1 is the proposal and design milestone. Phase 2 is the first implementation milestone. Phase 3 is the experiment, integration, and final presentation milestone.

If the course calendar uses different dates, the week numbers below can be adjusted without changing the role split.

## 1. Milestone Overview

| Phase | Suggested Weeks | Main Goal | Core Outputs |
| --- | --- | --- | --- |
| Phase 1 / Milestone 1 | Weeks 1-3 | Define the project foundation | proposal, literature review, data plan, annotation rubric, architecture, evaluation plan, slide deck |
| Phase 2 | Weeks 4-8 | Build the first working research prototype | inference pipeline, confidence tracker, dialogue prototype, safety classifier, pilot dataset expansion |
| Phase 3 | Weeks 9-12 | Run experiments and integrate the system | baseline comparisons, ablations, error analysis, final demo, final report |

## 2. Phase 1 / Milestone 1

### Scope

- problem formulation and scope control
- literature review and related work grounding
- pilot data design
- annotation rubric and schema
- architecture design
- evaluation plan and baselines
- proposal report and presentation deck

### Deliverables

- `phase1_report.md`
- `phase1_slides_outline.md`
- `architecture_diagram_mermaid.md`
- `data_schema.md`
- `evaluation_plan.md`
- `references.md`
- `README_phase1.md`

### Ownership

- `Ritwij`: model stack rationale, inference framing, baselines, evaluation section, report consolidation
- `Yash`: data design, annotation workflow, dialogue strategy, architecture framing, presentation structure
- `Shared`: research questions, ethical limits, milestone narrative, final editing pass

### Exit Criteria

- the project scope is clearly limited to text-first bilingual screening support,
- PHQ-9 and GAD-7 are defined as the core evaluation anchors,
- the data and annotation plan looks credible for a student project,
- the presentation and report tell the same story.

## 3. Phase 2

### Scope

- implement the initial state-tracked dialogue pipeline
- build evidence extraction and item scoring logic
- add per-item confidence updates
- add a parallel safety trigger classifier
- expand the pilot dataset beyond the first seed batch

### Concrete Tasks

- set up the LangGraph-style orchestration flow
- define the JSON conversation state format
- implement first-pass evidence extraction prompts or modules
- implement PHQ-9 and GAD-7 item score prediction
- build a lightweight safety pipeline with IndicBERT-style encoder or equivalent
- create the first annotated pilot subset for development testing

### Ownership

- `Ritwij`: inference engine, scoring functions, evaluation harness, logging, integration
- `Yash`: conversation templates, annotation execution, language variation checks, architecture refinements, presentation updates
- `Shared`: prompt iteration, annotation consensus, pilot error review

### Exit Criteria

- a runnable prototype exists,
- conversations can be logged turn by turn,
- item scores and confidence can be produced,
- safety flags can be generated independently,
- at least a small pilot set is ready for development experiments.

## 4. Phase 3

### Scope

- integrate the components into one end-to-end system
- run comparisons against baselines
- run planned ablations
- analyze English, Hindi, and code-mixed behavior
- prepare final course report and demo

### Concrete Tasks

- compare adaptive dialogue against direct questionnaire and fixed scripted baselines
- compare evidence-first scoring against single-pass transcript scoring
- run no-confidence and no-safety ablations offline
- perform item-level and language-level error analysis
- prepare final demo with clear scope caveats

### Ownership

- `Ritwij`: experiment execution, metrics, result tables, integration stability, final report assembly
- `Yash`: qualitative analysis, data quality review, dialogue examples, presentation polishing, demo structure
- `Shared`: interpretation of results, discussion section, ethics and limitation updates, final rehearsal

### Exit Criteria

- the team can demonstrate the full proposed pipeline,
- baseline and ablation comparisons are documented,
- limitations are clearly discussed,
- final deliverables are internally consistent.

## 5. Responsibility Split by Workstream

| Workstream | Lead | Support |
| --- | --- | --- |
| Data design and patient profiles | Yash | Ritwij |
| Annotation protocol and consensus workflow | Yash | Ritwij |
| Dialogue manager logic | Yash | Ritwij |
| Evidence extraction and item scoring | Ritwij | Yash |
| Evaluation metrics and experiment harness | Ritwij | Yash |
| Safety module integration | Ritwij | Yash |
| Architecture explanation and diagrams | Yash | Ritwij |
| Final report integration | Ritwij | Yash |
| Presentation / deck flow | Yash | Ritwij |

## 6. Collaboration Points

The following tasks should be done jointly even though one person leads them:

- finalize the annotation rubric before large-scale pilot creation,
- review the first Hindi and code-mixed examples together,
- agree on what counts as sufficient evidence for each questionnaire item,
- review safety-trigger examples before any demo,
- align the final presentation with the final report wording.

## 7. Known Risks and Mitigation

| Risk | Why It Matters | Proposed Mitigation |
| --- | --- | --- |
| Small pilot dataset | Results may be noisy or brittle | keep claims modest, emphasize pilot nature, use item-level error analysis |
| Synthetic data realism | Generated dialogue may sound too clean | manually revise conversations and document realism limits |
| Public label mismatch | Weak labels may distort evaluation | use public data only for auxiliary checks, not as main ground truth |
| Hindi and code-mixed ambiguity | Performance may drop outside English | include code-mixed examples early and track parity metrics |
| Compute limits for 32B model | Large-model iteration may be slow | use Aya selectively and run most iterations on smaller open baselines |

## 8. What Should Be Finished Before Submission of Phase 1

- all proposal documents should be consistent on scope and numbers,
- pilot data size and language split should be clearly stated,
- the three-layer architecture should be easy to explain verbally,
- baselines and ablations should be easy to justify in class,
- the team should replace any placeholder course details with final names or dates.
