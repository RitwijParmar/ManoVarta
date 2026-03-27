# ManoVarta Complete End-to-End Roadmap

## 1. Purpose

This document turns the Phase 1 proposal into a practical execution roadmap for the full course project. The aim is to build a credible research prototype, not a clinical product. The final system should be able to:

- conduct bounded multilingual screening dialogue in English, Hindi, and limited Hinglish,
- infer PHQ-9 and GAD-7 item-level scores from conversation rather than direct form answers alone,
- attach evidence spans to predicted scores,
- track confidence and unresolved items,
- run safety monitoring in parallel,
- support optional voice input and output as a wrapper over the text system,
- and run as a deployed class demo with clear limitations.

The guiding principle is simple: keep the core text-first screening pipeline strong, interpretable, and measurable. Everything else should support that goal rather than distract from it.

## 2. Final Project Goal

The final project should deliver a working vertical slice with six linked capabilities:

1. multilingual chat interaction,
2. dialogue state tracking,
3. evidence extraction,
4. PHQ-9 and GAD-7 item scoring,
5. parallel safety flagging,
6. clinician-style structured summary.

Voice should be added only after the text pipeline works reliably.

## 3. What the Final Project Should and Should Not Claim

### In scope

- text-first multilingual screening support,
- adaptive follow-up based on confidence and missing coverage,
- evidence-based item scoring,
- multilingual evaluation,
- a deployable research demo,
- optional voice interface.

### Out of scope

- diagnosis,
- therapy or emotional counseling,
- autonomous crisis intervention,
- real patient deployment,
- claims of clinical validation,
- self-hosting very large models on free cloud credits.

## 4. Recommended Final Stack

Because the team will not self-host a large model, the engineering stack should stay simple and modular.

### Core stack

- frontend: `Next.js` or a lightweight React app,
- runtime backend: `FastAPI`,
- admin and annotation backend: `Django`,
- dialogue orchestration: `LangGraph`,
- database: `PostgreSQL`,
- object/file storage: cloud blob storage,
- optional cache / queue: `Redis`,
- speech input: managed speech-to-text service,
- speech output: managed text-to-speech service,
- main research model: `Aya Expanse 32B` for offline evaluation or limited hosted runs,
- demo inference model: `Mistral NeMo 12B`, another smaller deployable model, or hosted API inference,
- safety / retrieval encoder: `IndicBERT` or similar Hindi-sensitive multilingual encoder.

### Why this stack is a good fit

- `FastAPI` is a good runtime layer for chat, scoring, safety, and voice endpoints.
- `Django` is a good operations layer for annotation workflow, admin review, exports, and logs.
- `LangGraph` is a good fit for multi-turn state tracking with explicit transitions.
- Managed speech services are more suitable than self-hosted Whisper for a class project because they reduce audio-pipeline and GPU complexity.
- External or hosted inference keeps the deployment realistic even if the research stack uses larger models.

## 5. Final Product Definition

### User input

- text chat in English, Hindi, or Hinglish,
- optional push-to-talk voice input later.

### Internal processing

- dialogue manager decides what to ask next,
- evidence extraction identifies symptom-relevant spans,
- scoring engine maps spans to PHQ-9 and GAD-7 items,
- confidence tracker decides what is resolved and what still needs follow-up,
- safety module independently checks every turn.

### Final output

- assistant reply,
- item-level PHQ-9 and GAD-7 scores,
- evidence spans,
- confidence values,
- unresolved items,
- safety status,
- concise clinician-style summary.

## 6. Quality Bar

The final project should not be judged only by whether the demo runs. It should meet a minimum quality bar:

- no item score should be returned without at least one evidence span or an explicit negating span,
- unresolved items must remain unresolved instead of being forced into confident labels,
- safety should run independently of the main scoring engine,
- English, Hindi, and Hinglish performance should be reported separately,
- voice should be evaluated separately from text,
- all deployment claims should match what is actually implemented.

If one part has to be cut for time, cut polish before cutting evidence tracing, safety separation, or multilingual evaluation.

## 7. System Architecture

The final system should be implemented in five modules.

### 7.1 Frontend

Responsibilities:

- user chat interface,
- optional microphone input,
- visible transcript,
- safe fallback message if backend fails,
- optional hidden debug panel for demo mode.

### 7.2 Dialogue Orchestrator

Responsibilities:

- store conversation state,
- track which PHQ-9 and GAD-7 items are resolved, weakly supported, contradicted, or unresolved,
- select next follow-up question,
- enforce bounded conversational behavior,
- terminate gracefully when enough evidence has been gathered.

### 7.3 Evidence and Scoring Engine

Responsibilities:

- extract evidence spans from new user turns,
- associate spans with PHQ-9 and GAD-7 items,
- infer 0-3 item scores,
- track contradictions,
- update confidence state.

### 7.4 Safety Trigger Module

Responsibilities:

- run on every turn independently,
- detect self-harm references, hopelessness escalation, crisis language, or urgent review needs,
- output one of `none`, `review`, or `urgent`,
- provide supporting cues for review.

### 7.5 Reporting Layer

Responsibilities:

- show item scores,
- show evidence spans,
- show confidence by item,
- list unresolved items,
- show safety status,
- export a summary for demo or analysis.

## 8. Data Roadmap

The project now uses a layered data strategy instead of treating every synthetic conversation as equally strong evidence.

### 8.1 Current repository state

| Layer | Purpose | Size | Annotation Level |
| --- | --- | --- | --- |
| Curated core | main reviewed set for error analysis and reporting | 48 conversations | 24 consensus final + 24 double annotated |
| Silver robustness set | broader training and prompt-stress pool | 132 conversations | draft labels carried forward from curated source |
| Total text corpus | current working dataset | 180 conversations | mixed quality by design |

Current language distribution:

- `60` English
- `60` Hindi
- `60` Hinglish

Current safety distribution:

- `127` none
- `37` review
- `16` urgent

This is a stronger project state than the earlier tiny seed set, but it is still a synthetic pilot corpus. The curated core should be treated as the higher-trust evaluation slice, while the silver layer should be treated as a robustness-oriented development slice.

### 8.2 Why the corpus is split this way

The main risk in synthetic mental-health dialogue is not only size but uniformity. A flat `180`-conversation corpus generated in one style would look larger without becoming more useful. The current `48 + 132` structure is more honest:

- the curated core preserves closer manual control over wording, evidence spans, and label logic,
- the silver layer adds conversational messiness without pretending every sample has the same review quality,
- training and ablation work can use both layers,
- final metrics and close error analysis should lean more heavily on the curated core.

### 8.3 Next optional stretch target

If more time remains after the main demo is stable, the best extension is not another blind jump in count. It is to expand the curated core toward `60` reviewed profiles while keeping the silver layer clearly separated.

## 9. Data Nuance Expansion Plan

The final data should not differ only in language. It should also differ in user behavior, symptom style, and conversational difficulty.

### 9.1 Nuance dimensions to cover

Each profile should be tagged across multiple dimensions.

| Dimension | Values to Include |
| --- | --- |
| Disclosure style | open, guarded, hesitant, evasive, inconsistent |
| Symptom directness | explicit, indirect, metaphorical, minimized |
| Severity | minimal, mild, moderate, moderately severe, severe |
| Temporal clarity | precise, vague, changing across turns |
| Functional impact | clear academic/work impact, mild impact, unclear impact |
| Emotional tone | flat, worried, irritable, tired, detached |
| Contradiction pattern | none, minor contradiction, major contradiction |
| Language form | English, Hindi, Hinglish, mixed register |
| Social context | student, employed adult, caregiver, isolated, family conflict |
| Safety intensity | none, passive concern, review-level, urgent |
| Cultural phrasing | direct symptom mention, idiomatic expression, stigma-influenced language |
| Response style | long narrative, short answers, fragmented, off-topic |

### 9.2 Specific nuance types to add

The expanded set should deliberately include:

- indirect depression wording such as tiredness without immediately naming sadness,
- anxiety expressed through body symptoms, restlessness, or dread rather than the word "anxiety",
- socially masked responses where the user says "I'm fine" and only later reveals difficulty,
- mixed depression-anxiety narratives with overlap,
- academic, work, and family stress contexts,
- culture-shaped Hindi phrasing that does not translate neatly into literal English symptom labels,
- Hinglish turns where the emotional word and the functional word appear in different languages,
- turn-level contradictions such as "sleep is okay" followed later by "actually I barely sleep before exams",
- low-engagement users who require several careful follow-ups,
- safety-related phrasing that is ambiguous at first and becomes clearer later.

The current silver set operationalizes this with three main variant families:

- `guarded_minimize`: downplays severity early, reveals details later,
- `functional_masking`: focuses on work, study, or family obligations before emotional content,
- `temporal_self_correction`: states one thing first and revises it later in the conversation.

### 9.3 What to avoid

- repetitive template-like conversations,
- literal English-to-Hindi translation as the only Hindi data source,
- users who always answer helpfully and completely,
- unrealistic overuse of explicit questionnaire language,
- perfectly clean and fully cooperative transcripts.

## 10. Annotation Roadmap

The annotation strategy should stay asymmetric:

- curated-core conversations are the main place for double annotation and consensus,
- silver conversations should usually inherit the source labels and then receive spot checks,
- disagreements in the silver layer should trigger either promotion back into a reviewed queue or exclusion from final headline metrics.

### 10.1 Annotation outputs per conversation

Each final annotated conversation should include:

- PHQ-9 item scores,
- GAD-7 item scores,
- evidence spans linked to items,
- contradiction notes if present,
- confidence notes,
- safety state,
- annotator comments on ambiguity,
- final consensus status.

### 10.2 Annotation workflow

1. design profile with nuance tags  
2. generate or draft conversation  
3. manual plausibility edit  
4. annotator A labels spans and items  
5. annotator B labels spans and items independently  
6. compare disagreements  
7. resolve in consensus pass  
8. freeze gold record  
9. flag difficult cases for future error analysis

### 10.3 Annotation quality controls

- weekly calibration on 5-10 shared conversations,
- weighted kappa for item labels,
- span-overlap checks for evidence,
- disagreement logging by type,
- language-specific review for Hindi and Hinglish,
- separate review for all safety-positive cases.

### 10.4 Annotation tooling plan

Use Django for:

- annotator login,
- conversation review,
- evidence-span editing,
- item-score entry,
- disagreement comparison,
- export of final gold records.

## 11. Confidence and Resolution Logic

Confidence needs a concrete operational definition rather than only a narrative one.

### 11.1 Proposed confidence states

- `resolved_high`
- `resolved_medium`
- `weak_support`
- `contradicted`
- `unresolved`

### 11.2 Stable confidence definition

An item is stable only when all of the following hold:

1. confidence is at or above threshold,
2. at least one accepted supporting or negating span exists,
3. no unresolved contradiction remains,
4. confidence has not shifted substantially across the last two updates.

### 11.3 Improvement to add

Allow the system to explicitly abstain on low-evidence items. This is better than forcing a misleading confident score.

## 12. Safety Roadmap

Safety should be treated as a separate subsystem, not a side note.

### 12.1 Minimum safety behavior

- evaluate every user turn,
- trigger `review` or `urgent` independently of symptom scoring,
- display a clear human-review message,
- log the turn and supporting cues,
- never suppress a safety alert because the main scorer is uncertain.

### 12.2 Safety improvements to add

- rule-based backup patterns,
- encoder-based or classifier support,
- curated safety examples in English, Hindi, and Hinglish,
- offline review of false negatives and false positives,
- explicit demo flow for what happens after a safety trigger.

## 13. Build Roadmap by Phase

The roadmap below assumes the team already completed Phase 1 proposal work.

### Phase A: Specification Freeze

Goal:
- finalize the exact behavior of the system before heavy implementation.

Tasks:
- freeze item keys and output schema,
- freeze conversation state schema,
- define confidence update rules,
- define safety states,
- define stop conditions for dialogue,
- finalize evaluation split logic.

Outputs:
- one stable runtime JSON schema,
- one stable annotation rubric,
- one stable clinician-summary format.

Exit criteria:
- no major naming changes still pending,
- both team members agree on the schema and annotation rules.

### Phase B: Data Expansion and Annotation Setup

Goal:
- build the richer dataset before tuning the system too aggressively to a tiny seed set.

Tasks:
- expand profiles from `40` to `60`,
- assign nuance tags to every profile,
- generate 3 variants per profile,
- manually revise all gold-set candidates,
- build Django annotation workflow,
- start double annotation.

Outputs:
- expanded conversation pool,
- annotation interface,
- first 30-40 gold finalized records.

Exit criteria:
- expanded data looks varied rather than templated,
- gold annotation pipeline is running end to end.

### Phase C: Text-First Runtime Prototype

Goal:
- produce a working conversation-to-summary system in text mode.

Tasks:
- build FastAPI endpoints,
- implement LangGraph state object,
- store turn history,
- build evidence extraction step,
- build item scoring step,
- build confidence updater,
- build safety API path,
- connect a simple frontend.

Outputs:
- working text chat prototype,
- structured internal state after each turn,
- evidence and score output.

Exit criteria:
- user can chat in text,
- system returns evidence, scores, confidence, and safety state.

### Phase D: Baselines and Ablations

Goal:
- make the project scientifically credible.

Tasks:
- implement direct questionnaire baseline,
- implement fixed scripted chatbot baseline,
- implement single-pass transcript scoring baseline,
- run no-confidence ablation,
- run no-safety ablation,
- compare evidence-first scoring against direct scoring.

Outputs:
- baseline comparison tables,
- ablation results,
- first error analysis notes.

Exit criteria:
- baselines are runnable and comparable on the same evaluation set.

### Phase E: Data-Driven Iteration

Goal:
- improve the model behavior based on errors rather than intuition alone.

Tasks:
- review low-confidence cases,
- review span extraction failures,
- review Hindi and Hinglish errors,
- review contradiction-handling failures,
- improve prompts, constraints, and routing logic,
- improve safety fallback patterns.

Outputs:
- updated prompts and scoring rules,
- documented failure categories,
- cleaner multilingual behavior.

Exit criteria:
- obvious repeated failures are reduced,
- multilingual parity is at least tracked explicitly.

### Phase F: Deployment-Ready App

Goal:
- move from a prototype to a stable class-demo system.

Tasks:
- separate frontend, FastAPI, and Django deployment concerns,
- add session persistence,
- add exportable summary,
- add logging and error handling,
- add environment-based model configuration,
- add demo-safe fallback responses.

Outputs:
- stable deployed text-first demo,
- admin panel for review and annotation,
- export and logging path.

Exit criteria:
- no local-only manual steps are needed for the demo.

### Phase G: Voice Wrapper

Goal:
- add voice as a wrapper over the text system without changing the core logic.

Tasks:
- add push-to-talk frontend,
- route audio to managed speech-to-text,
- display transcript before submission,
- run the normal text pipeline,
- optionally read back the assistant response,
- log ASR transcript separately from typed input.

Outputs:
- voice-enabled demo path,
- matched audio/transcript evaluation subset.

Exit criteria:
- voice works without changing the internal text pipeline.

### Phase H: Final Experiment and Demo Hardening

Goal:
- prepare the final report and class presentation.

Tasks:
- rerun metrics on the final gold set,
- evaluate text-only vs voice-wrapped behavior,
- prepare one strong example, one hard example, and one failure example,
- prepare a clinician-summary screenshot,
- write limitation-focused discussion honestly.

Outputs:
- final results tables,
- final demo script,
- final report updates,
- final slides.

Exit criteria:
- the report, demo, and deployment all tell the same story.

## 14. Detailed Weekly Timeline

This can be adjusted to your course calendar, but the sequence should stay similar.

### Weeks 1-2 after Phase 1

- freeze schema,
- freeze confidence logic,
- finalize 60 profile templates,
- define nuance tags,
- set up Django annotation models.

### Weeks 3-4

- generate and revise conversation variants,
- complete first 40-50 annotated conversations,
- implement FastAPI runtime skeleton,
- integrate LangGraph state management.

### Weeks 5-6

- complete first working text prototype,
- finish at least half of the gold subset,
- implement evidence extraction and item scoring,
- implement safety trigger path.

### Weeks 7-8

- run baselines,
- run first ablations,
- review multilingual failures,
- improve prompts and confidence routing.

### Weeks 9-10

- deploy text-first demo,
- add Django admin and export tools,
- finalize gold set,
- prepare error analysis.

### Weeks 11-12

- add voice wrapper,
- evaluate ASR impact,
- stabilize demo,
- finalize presentation and report.

## 15. Gaps and How to Fill Them

| Gap | Why It Matters | How to Fill It |
| --- | --- | --- |
| Synthetic realism gap | model may overfit to clean data | add guarded, indirect, contradictory, and low-engagement conversations; manually revise final gold set |
| Label mismatch in public data | public datasets do not map cleanly to PHQ-9/GAD-7 items | use public data only for auxiliary validation and safety stress tests |
| Hindi and Hinglish nuance gap | bilingual claims are weak without real variation | write native-feeling examples, separate evaluation by language, keep a Hinglish-specific subset |
| Confidence too vague | adaptive questioning becomes arbitrary | define explicit confidence states and thresholds; log unresolved items clearly |
| Safety under-specification | risky behavior may be hidden in demo mode | keep safety separate, add backup rules, review all positive cases manually |
| Evidence quality gap | scores without evidence weaken the project | require span-backed scoring and track evidence support rate |
| Deployment realism gap | demo may not match proposal claims | use smaller or hosted inference, do not claim large-model hosting |
| Voice scope creep | voice can delay the actual research core | add voice only after the text pipeline and gold evaluation set are stable |
| Annotation consistency gap | metrics become unreliable | use double annotation, weekly calibration, disagreement tracking, and consensus review |

## 16. Azure Deployment Plan

Because the team will not host a large model directly, Azure is sufficient for the final course project if used in a realistic way.

### What Azure should host

- frontend,
- FastAPI runtime service,
- Django admin service,
- PostgreSQL or another small managed data store,
- speech-to-text,
- text-to-speech,
- logs and monitoring.

### What Azure should not be assumed to host for free

- large open models at 12B-32B scale,
- full training or fine-tuning pipelines for large multilingual models,
- unlimited speech experimentation without cost tracking.

### Recommended Azure layout

- frontend: static web hosting or a simple web app deployment,
- FastAPI: Azure Container Apps or App Service,
- Django: separate Azure Container App or App Service,
- database: managed PostgreSQL if budget allows,
- storage: Blob Storage,
- speech: Azure Speech,
- secrets: Key Vault if needed,
- model inference: hosted external API or separate inference service.

### Why Azure is sufficient

- it is enough for a deployed demo,
- it is enough for voice input and spoken output,
- it is enough for admin and annotation tooling,
- it is enough for runtime orchestration and session logging.

### Azure caution

Azure is sufficient for the app and voice layers, but not a reason to increase model size or scope. Keep inference realistic and keep spending bounded.

## 17. Voice Plan

Voice should remain an interface layer, not the center of the project.

### Preferred implementation order

1. text-first system works,  
2. managed speech-to-text is added,  
3. transcript confirmation is shown,  
4. text pipeline runs unchanged,  
5. optional text-to-speech response is added.

### Preferred speech approach

For the final demo, prefer:

1. `Azure Speech` if the team deploys on Azure,
2. `Google Cloud Speech-to-Text` if the team deploys on GCP,
3. API-based transcription if the rest of the stack already uses it,
4. local Whisper only for offline tests or comparison.

### Voice evaluation requirements

- compare typed transcript vs ASR transcript on the same cases,
- keep at least `24-30` matched audio/text conversations,
- include English, Hindi, and Hinglish audio,
- record whether ASR changed item scores or evidence spans.

## 18. Concrete Improvements to Add

These are the highest-value improvements for making the final project stronger.

### Must-have

- explicit `unresolved` state,
- explicit contradiction handling,
- evidence span highlighting,
- multilingual parity reporting,
- conservative safety fallback rules,
- clinician-style summary view,
- stronger Hindi and Hinglish data variety,
- separate voice evaluation.

### Strong if time allows

- caching and retry logic,
- annotation disagreement dashboard,
- one-click export of JSON summary,
- session replay for error analysis,
- limited user profile variation by disclosure style in the frontend demo.

### Nice-to-have stretch items

- limited retrieval over symptom guidance notes,
- light user testing with classmates,
- finer-grained ASR analysis for Hinglish.

## 19. Team Split

### Ritwij lead

- FastAPI runtime backend,
- evidence extraction and item scoring,
- evaluation harness,
- integration,
- deployment backend,
- final results write-up.

### Yash lead

- profile design,
- nuance tagging,
- annotation workflow,
- Django admin and data operations support,
- dialogue phrasing and user-experience flow,
- demo narrative and presentation.

### Shared responsibilities

- gold annotation consensus,
- Hindi and Hinglish review,
- safety rubric,
- final deployment checks,
- final presentation rehearsal.

## 20. Definition of Done

The project is complete when all of the following are true:

- a user can complete a text-based screening conversation,
- the system produces item-level PHQ-9 and GAD-7 scores,
- each non-zero score has evidence support or explicit documented negation,
- unresolved items are visible,
- safety flags are generated independently,
- the system is deployed,
- the team can show one English example and one Hindi or Hinglish example,
- baselines and at least core ablations have been run,
- the final report clearly states limitations and does not oversell.

## 21. Final Recommendation

The best final version of ManoVarta is not the one with the most components. It is the one that is:

- text-first,
- evidence-backed,
- multilingual in a real rather than nominal sense,
- honest about unresolved uncertainty,
- conservative about safety,
- and realistic about deployment.

Do not spend your best effort on model hosting theatrics. Spend it on data quality, evidence quality, multilingual nuance, and a clean end-to-end demo.
