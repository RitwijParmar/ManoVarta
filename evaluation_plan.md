# ManoVarta Evaluation Plan

## 1. Evaluation Goal

The proposed evaluation should answer a narrow research question: does a multilingual conversational screening pipeline recover questionnaire-aligned symptom information better than simpler alternatives, and does it do so in a transparent and safety-aware way?

This plan is written for Phase 1, so it defines tasks and comparisons without pretending the experiments are already complete.

## 2. Exact Task Definitions

### Task A: Item-Level Evidence Extraction

Input: a partial or complete conversation transcript.  
Output: evidence spans linked to specific PHQ-9 or GAD-7 items.

Success means the system identifies text that actually supports or contradicts a questionnaire item, rather than hallucinating evidence from the profile or from generic mental health language.

### Task B: Item-Level Score Inference

Input: conversation transcript plus extracted evidence.  
Output: PHQ-9 and GAD-7 item scores from 0 to 3.

This is the core scoring task. The model should infer item scores, not only a total depression or anxiety label.

### Task C: Safety Trigger Detection

Input: each conversation turn, processed incrementally.  
Output: `none`, `review`, or `urgent` safety state, plus supporting cues when available.

This task is evaluated separately from symptom scoring because a safe system should not rely on the main model alone to catch crisis-sensitive language.

### Task D: Conversational Efficiency and Coverage

Input: the live dialogue state across turns.  
Output: coverage progress, stable confidence status, and stop-or-continue decisions.

This task measures whether adaptive dialogue is actually helping the system reach useful coverage with fewer unnecessary turns.

## 3. Proposed Data Splits

The synthetic pilot set is small, so leakage control matters.

- Unit of split: patient profile, not conversation.
- Proposed split: 24 profiles train, 8 profiles dev, 8 profiles test.
- With two conversations per profile, that corresponds to 48 train, 16 dev, and 16 test conversations.
- Language balancing should be approximate across splits, with at least some Hindi and code-mixed examples in dev and test.

Public datasets should not be merged blindly into the main item-level evaluation split. They should be used only for:

- auxiliary validation,
- safety stress testing,
- weak supervision experiments clearly marked as such.

## 4. Metrics

## 4.1 Item-Level MAE

Definition: average absolute difference between predicted and gold item scores across all 16 questionnaire items.

Why it matters: MAE reflects how far the predicted severity is from the gold label and is easy to interpret for ordinal scores.

## 4.2 Macro-F1

Definition: macro-averaged F1 across the four score classes `0, 1, 2, 3`, computed either per item and then averaged or across pooled item-label instances.

Why it matters: this guards against a model that performs well only on common low-severity classes.

## 4.3 Evidence Support Rate

Definition: percentage of non-zero predicted item scores that are backed by at least one accepted evidence span.

Why it matters: the project claims interpretable, evidence-traceable screening. This metric checks whether the system behaves that way.

## 4.4 Safety Recall and Safety Precision

Definition:

- `Safety recall`: fraction of gold safety-positive conversations correctly flagged.
- `Safety precision`: fraction of system safety flags that are correct.

Why it matters: recall is especially important because missing a high-risk case is costly, but precision still matters to avoid constant over-flagging.

## 4.5 Disclosure Efficiency

Operational definition: the number of questionnaire items that move from unresolved to stable confidence per assistant turn.

A second reporting version should also be included:

- average number of assistant turns required to reach at least 80% stable item coverage.

Why it matters: adaptive dialogue should ideally gather useful evidence faster than a fixed script.

## 4.6 Coverage Completeness

Definition: the fraction of all 16 PHQ-9 and GAD-7 items that have both:

- at least one supporting or explicitly negating evidence span, and
- stable confidence by conversation end.

Why it matters: a pleasant conversation is not enough if many symptom items remain unresolved.

## 4.7 Multilingual Consistency / Parity

Definition: absolute difference in item-level MAE and macro-F1 between:

- English vs Hindi,
- English vs code-mixed,
- Hindi vs code-mixed.

Why it matters: the project is explicitly bilingual. A strong English-only model with weak Hindi performance would not satisfy the project goal.

## 4.8 Latency

Definition: average wall-clock time per turn and per completed conversation.

Why it matters: this is a future integration metric rather than the main Phase 1 research metric. It is still useful to track once a prototype exists.

## 5. What Counts as Stable Confidence

For this proposal, an item is considered to have stable confidence when all three conditions hold:

1. the current item confidence is at least `0.75`,
2. the confidence changes by less than `0.10` over the last two updates,
3. the item has at least one accepted evidence span or an explicit negating span.

If contradictory evidence appears later, the item returns to unresolved status until the contradiction is settled.

This definition is intentionally simple and should be revised after the first pilot analysis if it proves too strict or too loose.

## 6. Baselines

### Baseline 1: Direct Questionnaire

The system asks PHQ-9 and GAD-7 items directly in standard form and records the answers. This is the cleanest comparison for score accuracy and questionnaire completeness.

### Baseline 2: Fixed Scripted Chatbot

The system uses a predetermined set of conversational prompts in a fixed order. It may sound less rigid than a form, but it does not adapt based on uncertainty or coverage.

### Baseline 3: Single-Pass Transcript Scoring

The model reads the final transcript once and predicts all item scores directly, without confidence tracking and without requiring evidence extraction first.

## 7. Experimental Comparisons

The main experimental matrix should compare:

1. direct questionnaire baseline vs fixed scripted baseline vs proposed adaptive pipeline,
2. Aya Expanse 32B vs Mistral NeMo 12B within the same adaptive pipeline,
3. optional Gemma 3 12B comparison if compute allows,
4. English vs Hindi vs code-mixed subsets,
5. synthetic test split vs auxiliary public-data stress tests.

The most important comparison is not only model family. It is whether the adaptive, evidence-first design outperforms simpler alternatives on coverage and interpretability.

## 8. Ablation Plan

### Ablation A: Without Confidence Tracking

Remove the per-item confidence state and use a fixed symptom coverage order instead.

Question answered: does uncertainty-aware follow-up actually help, or is a simpler scripted order enough?

### Ablation B: Without Safety Module

Disable the parallel safety trigger and rely only on the main conversational model.

Question answered: how many safety-sensitive cases are missed when safety is not separated from the main pipeline?

This ablation should be used for offline evaluation only. It should not be considered an acceptable deployed configuration.

### Ablation C: Direct Prompting vs Evidence-First Scoring

Compare:

- direct transcript-to-score prompting, and
- evidence extraction followed by score assignment.

Question answered: does forcing explicit evidence improve transparency and stability, even if it slightly increases latency?

## 9. Annotation Quality Checks

The evaluation is only meaningful if the labels are reliable. Before reporting main model results, the team should report:

- weighted kappa for item labels,
- evidence span overlap agreement,
- count of cases requiring consensus resolution,
- most frequent sources of disagreement.

If agreement is too low on some items, those items should be called out explicitly in the report rather than hidden inside an average.

## 10. Error Analysis Plan

When experiments begin, error analysis should be organized into the following buckets:

- missing evidence because the user phrased symptoms indirectly,
- score inflation from vague negative language,
- confusion between depression and anxiety items,
- Hindi idioms and code-mixed wording not handled well,
- contradictions across turns,
- safety misses or false alarms.

This analysis will be especially important because the dataset is small and average metrics alone may be misleading.

## 11. Minimum Claim Threshold for Later Phases

The project should only claim an advantage for adaptive conversation if it shows at least most of the following:

- equal or better item-level error than the fixed scripted chatbot,
- better disclosure efficiency or coverage completeness,
- evidence spans that human annotators judge as mostly valid,
- safety recall that remains high under English and Hindi conditions.

If those conditions are not met, the final report should present the system as an exploratory prototype rather than a demonstrated improvement.
