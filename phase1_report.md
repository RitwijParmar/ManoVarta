# ManoVarta: Multilingual Conversational AI Chatbot for Mental Health Screening

**Ritwij** and **Yash**  
Graduate NLP/AI Project  
ACL-style Phase 1 Report Draft

## Abstract

This Phase 1 proposal studies whether a text-first conversational system can support early mental health screening in a way that feels less rigid than a form while still remaining aligned with validated instruments. The target setting is English and Hindi screening support for mental health professionals, with PHQ-9 and GAD-7 used as the primary grounding frameworks. Instead of asking all questionnaire items in a fixed order, the proposed system aims to conduct a natural conversation, collect symptom evidence from open-ended user responses, map that evidence back to questionnaire items, and infer item-level scores with explicit confidence estimates. A separate safety module runs in parallel to flag crisis-sensitive language for human review.

The scope is intentionally limited. Phase 1 does not claim a clinically validated product, a therapy bot, or a diagnostic tool. The goal is to build a research foundation: define the task carefully, design a realistic pilot dataset, specify the architecture, choose a credible model stack, and establish an evaluation plan with meaningful baselines and ablations. The current data plan centers on a small seed set of synthetic patient-profile-guided conversations, paired with auxiliary public datasets for validation and robustness checks. Key risks include small pilot size, mismatch between public labels and questionnaire items, Hindi nuance and code-mixing, and the broader safety limits of open-ended mental health dialogue systems. The expected outcome of Phase 1 is a serious proposal and implementation plan for a later prototype and experiment cycle, not a completed screening system.

**Keywords:** multilingual dialogue, mental health screening, PHQ-9, GAD-7, Hindi NLP, evidence extraction, safety monitoring

## 1. Introduction

Many mental health screening workflows still rely on direct questionnaires such as PHQ-9 and GAD-7. These instruments are useful because they are validated, easy to score, and familiar to clinicians. At the same time, they can feel repetitive or impersonal in digital settings, especially when a user is already hesitant to talk about mood, sleep, worry, or hopelessness. A direct form can produce survey fatigue, minimal responses, or guarded wording. This is one reason conversational systems are appealing: some users may disclose symptoms more naturally when they are invited into a guided but open-ended exchange rather than a rigid checklist.

That said, moving from a questionnaire to a conversation is not just a user experience change. It creates a technical and methodological problem. Clinical screening depends on structured symptom coverage, but open dialogue is messy. A user may mention sleep problems without mentioning duration, may imply hopelessness indirectly, may mix languages, or may contradict earlier statements. A useful system therefore cannot be only “empathetic” or only “generative.” It has to preserve the structure of the screening task while still sounding conversational.

ManoVarta is proposed as a multilingual screening support system for English and Hindi that tries to balance those two goals. The project focuses on adaptive symptom elicitation through text conversation and on item-level reasoning over PHQ-9 and GAD-7. The intended audience is mental health professionals and researchers, not end users seeking diagnosis or therapy from an autonomous bot.

## 2. Problem Formulation

We frame the task as questionnaire-grounded conversational screening. Given a multi-turn text dialogue in English, Hindi, or Hindi-English code-mixed form, the system should:

1. interact in a rapport-aware but bounded way,
2. identify evidence snippets relevant to PHQ-9 and GAD-7 items,
3. infer item-level scores from 0 to 3 for each item,
4. maintain a confidence estimate for each inferred item, and
5. flag safety-sensitive language independently of the scoring process.

The output is not a diagnosis. It is a structured screening summary containing evidence spans, proposed item scores, confidence levels, unresolved items, and safety flags for human review.

The central design idea is confidence-based questioning. Instead of following a fixed script, the dialogue manager keeps track of which symptom items are already supported by evidence, which are weakly supported, and which remain unclear. If an item has low confidence or conflicting evidence, the system asks a targeted follow-up. If enough items reach stable confidence and sufficient coverage, the system stops probing and summarizes. In this proposal, an item is considered stably confident when the model confidence remains high and does not change much over successive turns, and when the item has at least one supporting or explicitly negating evidence span.

The project novelty is modest but concrete. We are not proposing a new clinical scale. The contribution is a modular research setup that keeps questionnaire alignment inside a natural bilingual conversation. In particular, the project emphasizes item-level evidence spans and confidence tracking, rather than only predicting one final depression or anxiety label from the whole transcript.

### 2.1 Example Task Instance

Table 1 gives a compact example of the kind of input-output behavior the project aims for.

| Component | Example |
| --- | --- |
| User utterance | "My sleep schedule is messed up and I can't focus on assignments." |
| Evidence spans | `sleep schedule is messed up` -> `PHQ-9 Q3 sleep`; `can't focus on assignments` -> `PHQ-9 Q7 concentration` |
| Proposed item scores | `phq_q3_sleep = 2`, `phq_q7_concentration = 2` |
| Confidence state | sleep: high, concentration: medium-high, low mood: unresolved |
| Next system action | ask a targeted follow-up about mood or fatigue rather than repeating a full questionnaire |

A corresponding structured output might look like this:

```json
{
  "evidence": [
    {"item": "phq_q3_sleep", "span": "sleep schedule is messed up", "score": 2},
    {"item": "phq_q7_concentration", "span": "can't focus on assignments", "score": 2}
  ],
  "confidence": {
    "phq_q3_sleep": 0.86,
    "phq_q7_concentration": 0.79,
    "phq_q2_low_mood": 0.31
  },
  "next_action": "follow_up_on_mood"
}
```

## 3. Research Questions

The project is organized around four research questions:

1. Can a rapport-aware multilingual conversation collect enough evidence to infer PHQ-9 and GAD-7 item-level scores with acceptable error relative to direct questionnaire scoring?
2. Does confidence-based follow-up improve symptom coverage and disclosure efficiency compared with a fixed scripted chatbot?
3. Does evidence-first scoring, where the model extracts supporting spans before assigning scores, produce more interpretable and more stable outputs than direct single-pass transcript scoring?
4. How much does performance change across English, Hindi, and code-mixed Hindi-English interactions, and which failure modes are most language-dependent?

## 4. Related Work

Conversational agents for mental health have been studied for both support and assessment, but the evidence base is still mixed. Systematic reviews by Gaffney et al. (2019) and Abd-Alrazaq et al. (2020) suggest that conversational agents can improve engagement and may reduce distress in some settings, but they also note limited evaluation quality, small studies, and unresolved safety questions. For this project, those reviews are useful mainly as grounding: feasibility is not the same as clinical reliability.

Closer to screening, Dosovitsky et al. (2021) studied a chatbot-administered PHQ-9 and reported encouraging psychometric properties. That result matters because it shows that users may be willing to complete screening through chat. However, it still reflects a questionnaire delivered by chatbot rather than an open-ended conversational inference system. ManoVarta differs in asking whether item scores can be inferred from natural dialogue while remaining traceable to explicit evidence.

The mental health NLP literature offers relevant methods but not a direct solution. Shared tasks such as CLPsych 2019 and CLPsych 2021 study suicidality and risk detection from online text, while DAIC-WOZ-style work examines depression from interview transcripts. Burdisso et al. (2024) is especially important because it shows how depression models can exploit interviewer prompt artifacts instead of patient language. More recent evidence-focused CLPsych work, such as Tran and Matsui (2024), reinforces the value of extracting supporting spans rather than predicting only a coarse label.

The multilingual setting remains under-served. Hindi symptom descriptions can be indirect, code-mixed, or written in different scripts. IndicBERT-related work and code-mixed Hindi-English resources such as HingBERT make a strong case for using Indic-sensitive encoders and for measuring language robustness directly instead of assuming English transfer will be enough (Kakwani et al., 2020; Nayak and Joshi, 2022). The gap we target is therefore fairly specific: bilingual, questionnaire-grounded, evidence-traceable screening dialogue with explicit safety monitoring.

## 5. Data Plan and Annotation Methodology

### 5.1 Seed pilot data

Phase 1 assumes a small but structured pilot dataset rather than a clinical corpus. The proposed seed set contains 40 synthetic patient profiles, each instantiated into two conversation variants, for a target of 80 conversations total. The planned split is:

| Language subset | Profiles | Conversations | Main use |
| --- | --- | --- | --- |
| English | 16 | 32 | core development and baseline comparison |
| Hindi | 16 | 32 | multilingual robustness and Hindi phrasing analysis |
| Code-mixed Hindi-English | 8 | 16 | stress test for mixed-language interaction |
| **Total** | **40** | **80** | **Phase 1 pilot dataset** |

Each profile will specify age band, occupation, social context, stressors, disclosure style, symptom severity pattern, and whether safety-sensitive cues are present. Conversation length is expected to be around 12 to 18 turns. The goal is not to generate polished benchmark data at scale, but to create a controlled pilot set that covers different symptom combinations and linguistic patterns.

Synthetic dialogue will be profile-guided and manually reviewed. We do not want model-generated text to become its own unverified ground truth. The workflow is therefore: create a patient profile, generate a candidate dialogue under rubric constraints, manually edit for plausibility and language naturalness, then annotate independently.

### 5.2 Public data for auxiliary validation

Public data will be used carefully and only where labels are relevant.

- `DAIC-WOZ` can support weak validation for depression-style interview transcripts, but it mainly provides PHQ-8 severity information rather than item-level PHQ-9 or GAD-7 labels.
- `CLPsych` and `eRisk` style datasets can support safety-trigger development and stress testing for high-risk language, but they are not equivalent to conversational screening data.
- General empathetic dialogue corpora may help with response-style sanity checks, but they should not be treated as mental health screening ground truth.

The key limitation is label mismatch. Public datasets often contain total severity scores, forum-level risk labels, or emotional support dialogue, not item-level PHQ-9 and GAD-7 scoring. For that reason, they are auxiliary resources, not substitutes for task-specific annotation.

### 5.3 Annotation scheme

Each conversation will receive:

- PHQ-9 item labels from 0 to 3
- GAD-7 item labels from 0 to 3
- evidence spans linked to specific items
- a conversation-level safety flag
- annotator notes about ambiguity, contradiction, or missing evidence
- confidence notes about why some items remain uncertain

Annotation will be double-coded by the two team members. Each annotator will independently assign item labels and evidence spans using a shared rubric. Disagreements will be resolved in a consensus pass. The consensus version becomes the frozen gold annotation for experiments.

### 5.4 Quality control

Because the dataset is small, annotation quality matters as much as model quality. We therefore plan to report:

- weighted Cohen's kappa for PHQ-9 and GAD-7 item labels,
- evidence span agreement using token- or span-level overlap,
- disagreement categories such as insufficient detail, temporal ambiguity, code-mixed phrasing, and conflicting statements.

The annotation design intentionally favors evidence spans over only final totals. A conversation with a correct total score but no interpretable item evidence is not sufficient for this project.

## 6. Proposed Architecture

The proposed system has three major layers.

### 6.1 Rapport-aware dialogue manager

This layer is responsible for natural interaction. It handles opening turns, language adaptation, follow-up strategy, and topic steering. Its job is not to produce unrestricted counseling dialogue. Instead, it keeps the conversation useful and humane while gradually covering the symptom space. It tracks which items appear unresolved and chooses follow-up questions accordingly.

### 6.2 Clinical evidence and scoring engine

After each user turn, the evidence engine identifies symptom-relevant snippets, maps them to PHQ-9 and GAD-7 items, proposes 0 to 3 item scores, and updates per-item confidence. It also records contradiction when later statements weaken earlier inferences. This layer is what keeps the conversation clinically structured. It should output evidence and scores together, not scores alone.

### 6.3 Safety trigger module

The safety module runs in parallel rather than waiting for the dialogue manager. It monitors for crisis-sensitive or escalation-sensitive language such as self-harm ideation, extreme hopelessness, imminent danger, or other high-risk signals. Its output is a safety state and escalation recommendation for human review. This module is intentionally separated from the symptom scorer so that safety does not depend on the main model's item-level reasoning being correct.

The overall orchestration can be implemented in LangGraph or an equivalent state-tracking framework. A graph-style controller is useful here because it makes state transitions explicit: receive user turn, update evidence, update confidence, check safety, decide whether to ask a follow-up, and produce the next response. This is easier to inspect than a single opaque prompt.

## 7. Model Choices and Rationale

The proposed model stack is modular on purpose.

| Component | Proposed Model | Role in the System | Rationale |
| --- | --- | --- | --- |
| Primary dialogue and evidence model | Aya Expanse 32B | Main bilingual conversation, evidence extraction, score proposal | Strong multilingual orientation, Hindi support, open weights, and good fit for cross-lingual text reasoning |
| Open comparison model | Mistral NeMo 12B | Main open baseline within the same pipeline | Smaller and cheaper multilingual model for realistic comparison |
| Optional second open baseline | Gemma 3 12B | Additional comparison for ablations | Useful open model family with broad multilingual coverage and manageable size |
| Safety / retrieval encoder | IndicBERT or similar Hindi-sensitive multilingual encoder | Parallel safety classification, cue retrieval, and language-sensitive matching | Better suited than generic English-centric encoders for Hindi and mixed-script inputs |
| Orchestration layer | LangGraph or equivalent | State tracking, routing, confidence updates, escalation logic | Makes the pipeline auditable and modular |

Aya Expanse 32B is the preferred primary model because multilingual performance is central to this project, not an afterthought. Mistral NeMo 12B is a strong open comparison model because it is lighter and more practical for repeated ablation runs. Gemma 3 12B is optional rather than mandatory; it is included to make the comparison less dependent on one alternative family.

A practical constraint is compute. Phase 1 does not assume full fine-tuning of Aya Expanse 32B. Early experiments may use prompting, limited batch evaluation, hosted inference, or quantized inference. If university hardware is limited, smaller baselines will handle most iteration, while Aya Expanse is used for carefully chosen evaluation subsets.

## 8. Evaluation Plan

The evaluation is designed around the actual claims of the proposal rather than generic chatbot quality.

Table 2 summarizes the main evaluation metrics.

| Metric | What it measures | Why it matters |
| --- | --- | --- |
| `Item-level MAE` | average absolute error over PHQ-9 and GAD-7 item scores | respects ordinal severity differences |
| `Macro-F1` | class-balanced item scoring performance over labels `0-3` | avoids over-crediting common low-severity labels |
| `Evidence support rate` | fraction of predicted scores backed by valid evidence spans | checks interpretability rather than only final correctness |
| `Safety recall / precision` | quality of crisis-sensitive flagging | recall is especially important in safety settings |
| `Disclosure efficiency` | how quickly unresolved items become stably confident | captures whether adaptive questioning is worthwhile |
| `Coverage completeness` | fraction of items resolved with evidence and stable confidence | prevents a pleasant but clinically incomplete dialogue |
| `Multilingual parity` | score gap across English, Hindi, and code-mixed subsets | makes bilingual performance visible |
| `Latency` | time per turn and per conversation | useful future deployment metric, but not a main Phase 1 claim |

The main point is to evaluate both quality and transparency. A model that gives plausible totals but poor item evidence should not be considered fully successful.

## 9. Baselines

Three baselines are necessary for the proposal to be credible.

Table 3 summarizes the baseline comparisons.

| Baseline | Main idea | Strength | Main limitation |
| --- | --- | --- | --- |
| Direct questionnaire | ask PHQ-9 and GAD-7 items directly in standard order | strongest questionnaire alignment | least conversational, may increase survey fatigue |
| Fixed scripted chatbot | conversational prompts, but fixed order and fixed coverage | easy to implement and compare | no uncertainty-aware follow-up |
| Single-pass transcript scoring | score all items from the final transcript in one shot | simple and cheap | weak interpretability and no live confidence tracking |

These baselines will be compared with the proposed evidence-first, confidence-tracking system. Model family comparisons across Aya Expanse, Mistral NeMo, and optionally Gemma 3 can then be run within the same architecture.

## 10. Compute Environment

The project is designed for a graduate-course setting rather than a dedicated clinical AI lab.

- Programming stack: Python 3.11, PyTorch, Hugging Face Transformers, PEFT, bitsandbytes, scikit-learn, pandas, and LangGraph.
- Language resources: Indic NLP tools, sentencepiece/tokenizer utilities, and a Hindi-sensitive encoder such as IndicBERT.
- Development environment: local workstation for annotation, data preparation, prompt iteration, and analysis.
- Model execution: university GPU server or cloud GPU access for model experiments.

A realistic hardware plan is:

- smaller ablations on a single high-memory GPU using 4-bit quantization,
- targeted Aya Expanse 32B evaluations through hosted inference or larger shared GPU infrastructure,
- no assumption of full supervised fine-tuning in Phase 1.

This compute plan is intentionally conservative. The project should not depend on expensive end-to-end retraining of every large model variant.

## 11. Milestone-Wise Plan

The project is split into three stages.

### Phase 1 / Milestone 1

Define the problem, review relevant literature, design the pilot dataset and annotation rubric, specify the architecture, define the evaluation plan, and prepare the report and presentation materials.

### Phase 2

Build the initial inference pipeline, confidence tracker, dialogue prototype, and safety classifier. Expand the dataset beyond the first pilot batch and test the first end-to-end runs.

### Phase 3

Integrate the full pipeline, run baseline comparisons and ablations, perform error analysis, and prepare the final report and demo.

## 12. Team Responsibilities

The team split is based on complementary responsibilities but still requires overlap in critical decisions.

- `Ritwij`: inference engine, scoring logic, evaluation setup, system integration, and final write-up consolidation.
- `Yash`: data design, annotation workflow, dialogue logic, architecture framing, and presentation preparation.

Shared responsibilities include rubric design, consensus annotation, ethics review, experiment interpretation, and final demo rehearsal. The split is meant to reduce duplication, not isolate modules completely.

## 13. Ethical Considerations and Limitations

This project has clear ethical and practical limits.

First, the system is a screening support tool, not a diagnostic or therapeutic replacement. Outputs must be framed as provisional and clinician-facing. Second, the Phase 1 dataset is small and largely synthetic. Even with careful profile design and manual review, synthetic conversations cannot capture the variation, ambiguity, guarded phrasing, or social context of real users. Third, public datasets are imperfect fits. Some use total scores instead of item labels, some focus on social media rather than dialogue, and some contain dataset artifacts that can mislead models.

Fourth, multilingual performance is not guaranteed by simply choosing a multilingual model. Hindi expressions of distress can be indirect, culture-specific, or code-mixed. Romanized Hindi and mixed-script writing are additional sources of ambiguity. Fifth, safety remains a serious concern. A conversational system can miss crisis language, over-interpret it, or respond inappropriately. For this reason, safety monitoring must run independently and human oversight remains mandatory.

There are also privacy concerns for any future real-user data collection. If later phases involve human participants, the project would require proper consent, storage controls, de-identification, and likely institutional review depending on the study design. Finally, scope control matters. Voice support, multimodal affect cues, and substance-use screening extensions such as CAGE-AID may be valuable later, but they are outside the core Phase 1 objective.

## 14. Conclusion

ManoVarta is proposed as a multilingual, text-first screening support system that aims to make mental health screening more conversational without losing the structure of validated instruments. The key technical idea is to combine a rapport-aware dialogue manager with an evidence-based scoring engine and a parallel safety module. The main research contribution is not a claim of clinical deployment, but a careful framework for studying item-level PHQ-9 and GAD-7 inference from English and Hindi conversation.

Phase 1 is therefore a foundation milestone. Its success should be judged by the clarity of the task definition, rigor of the data and annotation plan, credibility of the architecture, strength of the baselines and evaluation plan, and honesty about limitations. If that foundation is solid, later phases can test whether adaptive conversational elicitation offers a real advantage over direct or scripted screening methods.

## References

Abd-Alrazaq, A., Alajlani, M., Alalwan, A. A., Bewick, B. M., Gardner, P., and Househ, M. (2020). Effectiveness and Safety of Using Chatbots to Improve Mental Health: Systematic Review and Meta-Analysis. Journal of Medical Internet Research. Available at: https://pubmed.ncbi.nlm.nih.gov/32673216/

Burdisso, S. G., Reyes-Ramirez, H., Montenegro, D., and Errecalde, M. L. (2024). DAIC-WOZ: On the Validity of Using the Therapist's Prompts in Automatic Depression Detection from Clinical Interviews. Clinical NLP. Available at: https://aclanthology.org/2024.clinicalnlp-1.8/

Dosovitsky, G., Kim, E. J., and Bunge, E. L. (2021). Psychometric Properties of a Chatbot Version of the PHQ-9 With Adults and Older Adults. JMIR Aging. Available at: https://pmc.ncbi.nlm.nih.gov/articles/PMC8522018/

Kakwani, D., Kunchukuttan, A., Golla, S., Gokul, N. C., Bhattacharyya, A., Khapra, M. M., and Kumar, P. (2020). IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages. Findings of EMNLP. Available at: https://aclanthology.org/2020.findings-emnlp.445/

Kroenke, K., Spitzer, R. L., and Williams, J. B. W. (2001). The PHQ-9: Validity of a Brief Depression Severity Measure. Journal of General Internal Medicine. Available at: https://pubmed.ncbi.nlm.nih.gov/11556941/

Nayak, R., and Joshi, A. (2022). L3Cube-HingCorpus and HingBERT: A Code Mixed Hindi-English Dataset and BERT Language Models. arXiv. Available at: https://arxiv.org/abs/2204.08398

Pichowicz, A., Kotas, M., and Piotrowski, M. (2025). Performance of Mental Health Chatbot Agents in Detecting and Managing Suicidal Ideation. Scientific Reports. Available at: https://www.nature.com/articles/s41598-025-17242-4

Spitzer, R. L., Kroenke, K., Williams, J. B. W., and Lowe, B. (2006). A Brief Measure for Assessing Generalized Anxiety Disorder: The GAD-7. Archives of Internal Medicine. Available at: https://pubmed.ncbi.nlm.nih.gov/16717171/

Zirikly, A., Atkinson, M., Kamath, S., and Resnik, P. (2019). CLPsych 2019 Shared Task: Predicting the Degree of Suicide Risk in Reddit Posts. Proceedings of CLPsych. Available at: https://aclanthology.org/W19-3003/

## Model and Tool Sources

Cohere. Aya Expanse model documentation. Available at: https://docs.cohere.com/v2/docs/aya-expanse

Google. Gemma documentation and model resources. Available at: https://ai.google.dev/gemma/docs/core and https://huggingface.co/google/gemma-3-12b-it

LangChain. LangGraph documentation. Available at: https://langchain-ai.github.io/langgraph/

Mistral AI. Mistral NeMo 12B official model page. Available at: https://docs.mistral.ai/models/mistral-nemo-12b-24-07
