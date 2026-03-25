# Selected References for Phase 1

This version is intentionally narrower than the earlier long list. For a student Phase 1 proposal, a smaller set of clearly relevant references usually reads better than an overextended bibliography.

## 1. Core Screening Foundations

### Kroenke, Spitzer, and Williams (2001)

The PHQ-9: Validity of a Brief Depression Severity Measure. Available at: https://pubmed.ncbi.nlm.nih.gov/11556941/

Why it matters: This is the main grounding reference for depression screening in the project. It gives the item structure that ManoVarta tries to infer from conversation instead of asking only as a rigid form.

### Spitzer et al. (2006)

A Brief Measure for Assessing Generalized Anxiety Disorder: The GAD-7. Available at: https://pubmed.ncbi.nlm.nih.gov/16717171/

Why it matters: This is the anxiety counterpart to PHQ-9 and is central to the scoring design. It anchors the project in a validated screening framework rather than an ad hoc label scheme.

### Dosovitsky, Kim, and Bunge (2021)

Psychometric Properties of a Chatbot Version of the PHQ-9 With Adults and Older Adults. Available at: https://pmc.ncbi.nlm.nih.gov/articles/PMC8522018/

Why it matters: This is probably the most directly relevant screening-chatbot paper for the proposal. It does not solve open-ended inference, but it supports the idea that chatbot-based screening is worth studying.

## 2. Related Work Most Relevant to Our Task

### Abd-Alrazaq et al. (2020)

Effectiveness and Safety of Using Chatbots to Improve Mental Health: Systematic Review and Meta-Analysis. Available at: https://pubmed.ncbi.nlm.nih.gov/32673216/

Why it matters: One broad review is enough here. It helps justify the project while also keeping the claims modest, especially around effectiveness and safety.

### Burdisso et al. (2024)

DAIC-WOZ: On the Validity of Using the Therapist's Prompts in Automatic Depression Detection from Clinical Interviews. Available at: https://aclanthology.org/2024.clinicalnlp-1.8/

Why it matters: This is an important cautionary paper for evaluation. It shows that transcript-based mental health models can exploit prompt artifacts instead of truly reasoning over patient language.

### Zirikly et al. (2019)

CLPsych 2019 Shared Task: Predicting the Degree of Suicide Risk in Reddit Posts. Available at: https://aclanthology.org/W19-3003/

Why it matters: This is a useful safety reference because it shows how risk-sensitive text classification has been framed and evaluated in mental health NLP.

### Pichowicz, Kotas, and Piotrowski (2025)

Performance of Mental Health Chatbot Agents in Detecting and Managing Suicidal Ideation. Available at: https://www.nature.com/articles/s41598-025-17242-4

Why it matters: This paper is useful for the safety section because it focuses directly on how mental-health-oriented chatbot systems behave around suicidal ideation.

## 3. Multilingual and Hindi-Relevant References

### Kakwani et al. (2020)

IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages. Available at: https://aclanthology.org/2020.findings-emnlp.445/

Why it matters: This is the clearest grounding reference for the Hindi side of the project. It supports the decision to use an Indic-sensitive encoder rather than assuming English transfer is enough.

### Nayak and Joshi (2022)

L3Cube-HingCorpus and HingBERT: A Code Mixed Hindi-English Dataset and BERT Language Models. Available at: https://arxiv.org/abs/2204.08398

Why it matters: Since the proposal explicitly includes Hinglish as a target condition, this is a strong reference for why code-mixed text needs to be treated as a real modeling problem.

## 4. Model and Tool Sources Used in the Proposal

These are not "related work" papers in the same sense as the items above, but they are the right sources to cite when explaining the implementation stack.

### Aya Expanse 32B

Aya Expanse model documentation. Available at: https://docs.cohere.com/v2/docs/aya-expanse  
Optional model card: https://huggingface.co/CohereForAI/aya-expanse-32b

Why it matters: This is the primary multilingual dialogue and evidence model proposed in the system. The official documentation is the safest source for its multilingual scope and deployment details.

### Mistral NeMo 12B

Mistral NeMo 12B official model page. Available at: https://docs.mistral.ai/models/mistral-nemo-12b-24-07

Why it matters: This is the main open comparison model in the proposal. It is worth citing directly because the project explicitly uses it as a baseline within the same pipeline.

### Gemma 3 12B

Gemma 3 model overview and official model card source. Available at: https://ai.google.dev/gemma/docs/core  
Model card: https://huggingface.co/google/gemma-3-12b-it

Why it matters: Gemma 3 12B is an optional second baseline in the proposal. These official sources are the best references for capabilities, sizes, and access points.

### LangGraph

LangGraph documentation / workflow orchestration reference. Available at: https://langchain-ai.github.io/langgraph/

Why it matters: LangGraph is not the scientific contribution, but it is the proposed orchestration layer for explicit state tracking. It is fine to cite this as an implementation reference in the methodology section or appendix.

## 5. Short Citation Set for the Report

If you want the report to look more natural and less overloaded, these are enough for the main text:

1. Kroenke et al. (2001)
2. Spitzer et al. (2006)
3. Dosovitsky et al. (2021)
4. Abd-Alrazaq et al. (2020)
5. Burdisso et al. (2024)
6. Kakwani et al. (2020)
7. Nayak and Joshi (2022)
8. Zirikly et al. (2019)

Then cite the model/tool sources only where the architecture or model stack is discussed.
