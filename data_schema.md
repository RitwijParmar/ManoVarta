# ManoVarta Data Schema and Annotation Plan

## Goal

The Phase 1 dataset is a pilot seed set for questionnaire-grounded conversational screening. It is not intended to be a large clinical corpus. The schema below is designed so that each conversation supports:

- multilingual dialogue analysis,
- item-level PHQ-9 and GAD-7 scoring,
- evidence-span annotation,
- safety review,
- future error analysis.

## 1. Conversation-Level Schema

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Unique conversation identifier |
| `patient_id` | string | Synthetic patient/profile identifier |
| `language` | enum | `en`, `hi`, or `hinglish` |
| `age` | integer | Approximate age or age band midpoint |
| `occupation` | string | Short occupation label |
| `background_profile` | object | Family, work/study context, location type, relevant life events |
| `symptom_profile` | object | Intended symptom pattern used to guide generation |
| `conversation_turns` | list | Ordered turns with speaker labels |
| `evidence_spans` | list | Annotated text spans linked to questionnaire items |
| `phq9_item_labels` | object | Item-wise scores from 0 to 3 |
| `gad7_item_labels` | object | Item-wise scores from 0 to 3 |
| `safety_flag` | object | Safety status, risk cues, and escalation note |
| `annotator_notes` | string | Notes on ambiguity, contradiction, or special context |
| `confidence_notes` | object | Item uncertainty, contradictions, and why follow-up may still be needed |
| `generation_source` | string | `synthetic_profile_guided` or public-data-derived auxiliary note |
| `review_status` | enum | `draft`, `double_annotated`, `consensus_final` |

## 2. Nested Turn Schema

Each item in `conversation_turns` should follow this structure:

| Field | Type | Description |
| --- | --- | --- |
| `turn_id` | integer | Turn number |
| `speaker` | enum | `assistant` or `user` |
| `text` | string | Raw turn text |
| `language_tag` | enum | Dominant language for that turn |
| `normalized_text` | string | Optional normalized form for analysis |
| `notes` | string | Optional note on tone, hesitation, code-mixing, or ambiguity |

## 3. Evidence Span Schema

Each item in `evidence_spans` should follow this structure:

| Field | Type | Description |
| --- | --- | --- |
| `span_id` | string | Unique evidence identifier |
| `questionnaire` | enum | `PHQ9` or `GAD7` |
| `item_id` | string | Item key such as `phq_q3_sleep` or `gad_q2_control_worry` |
| `turn_id` | integer | Turn where the evidence appears |
| `text_span` | string | Exact supporting text span |
| `polarity` | enum | `present`, `absent`, or `uncertain` |
| `score_hint` | integer | Suggested score contribution from 0 to 3 |
| `annotator` | string | Initial annotator ID |
| `rationale` | string | Short justification for why the span supports the item |

## 4. PHQ-9 and GAD-7 Label Keys

### PHQ-9

- `phq_q1_anhedonia`
- `phq_q2_low_mood`
- `phq_q3_sleep`
- `phq_q4_fatigue`
- `phq_q5_appetite`
- `phq_q6_worthlessness`
- `phq_q7_concentration`
- `phq_q8_psychomotor`
- `phq_q9_self_harm`

### GAD-7

- `gad_q1_nervous`
- `gad_q2_control_worry`
- `gad_q3_excessive_worry`
- `gad_q4_trouble_relaxing`
- `gad_q5_restlessness`
- `gad_q6_irritability`
- `gad_q7_fear_awful`

## 5. Annotation Process

### Step 1: Profile creation

Create a patient profile with:

- age and occupation,
- preferred language,
- stressors and context,
- symptom severity pattern,
- disclosure style,
- whether safety-sensitive cues are present.

### Step 2: Conversation drafting

Generate a candidate conversation from the profile using a constrained prompt or manual drafting. Keep the dialogue natural, but make sure there is enough information for later item-level annotation. Then manually revise for plausibility and language quality.

### Step 3: Independent double annotation

Both annotators independently assign:

- PHQ-9 item scores,
- GAD-7 item scores,
- evidence spans,
- safety flag,
- confidence notes.

### Step 4: Consensus resolution

Annotators compare disagreements and resolve them by discussion. A consensus version is stored as the final gold label set. If disagreement persists, the item is marked for adjudication and the conversation can be excluded from the main evaluation split until resolved.

### Step 5: Quality tracking

Report:

- weighted kappa for item labels,
- span overlap agreement,
- number of unresolved or low-confidence cases,
- frequent disagreement categories.

## 6. Annotation Guidelines

- Evidence spans should be as short as possible while still understandable.
- Do not label only from the profile; annotate from the actual conversation text.
- If a user contradicts an earlier statement, note both spans and explain which one is stronger or more recent.
- Use `uncertain` polarity when a symptom is hinted at but not clearly present.
- `phq_q9_self_harm` and safety flags should be treated conservatively and reviewed carefully.
- Code-mixed turns should preserve the original wording; do not force translation into artificial formal Hindi or English.

## 7. Compact Synthetic Example Records

### Example 1: English

```json
{
  "conversation_id": "MB-C001",
  "patient_id": "MB-P001",
  "language": "en",
  "age": 23,
  "occupation": "graduate student",
  "background_profile": {
    "context": "moved cities for university, deadlines increasing",
    "living_situation": "shared apartment",
    "support_system": "talks occasionally to one close friend"
  },
  "symptom_profile": {
    "depression_level": "mild_to_moderate",
    "anxiety_level": "moderate",
    "safety_signal": "none"
  },
  "conversation_turns": [
    {"turn_id": 1, "speaker": "assistant", "text": "How have the last couple of weeks felt for you?", "language_tag": "en"},
    {"turn_id": 2, "speaker": "user", "text": "Mostly drained. My sleep schedule is messed up and I keep falling behind on assignments.", "language_tag": "en"},
    {"turn_id": 3, "speaker": "assistant", "text": "When you say falling behind, is it more about focus, energy, or both?", "language_tag": "en"},
    {"turn_id": 4, "speaker": "user", "text": "Both, honestly. I stare at the screen and nothing sticks.", "language_tag": "en"}
  ],
  "evidence_spans": [
    {
      "span_id": "E1",
      "questionnaire": "PHQ9",
      "item_id": "phq_q3_sleep",
      "turn_id": 2,
      "text_span": "My sleep schedule is messed up",
      "polarity": "present",
      "score_hint": 2,
      "annotator": "Yash",
      "rationale": "Direct sleep disturbance statement"
    },
    {
      "span_id": "E2",
      "questionnaire": "PHQ9",
      "item_id": "phq_q7_concentration",
      "turn_id": 4,
      "text_span": "I stare at the screen and nothing sticks",
      "polarity": "present",
      "score_hint": 2,
      "annotator": "Ritwij",
      "rationale": "Clear concentration difficulty"
    }
  ],
  "phq9_item_labels": {
    "phq_q1_anhedonia": 1,
    "phq_q2_low_mood": 1,
    "phq_q3_sleep": 2,
    "phq_q4_fatigue": 2,
    "phq_q5_appetite": 0,
    "phq_q6_worthlessness": 0,
    "phq_q7_concentration": 2,
    "phq_q8_psychomotor": 0,
    "phq_q9_self_harm": 0
  },
  "gad7_item_labels": {
    "gad_q1_nervous": 1,
    "gad_q2_control_worry": 1,
    "gad_q3_excessive_worry": 2,
    "gad_q4_trouble_relaxing": 1,
    "gad_q5_restlessness": 0,
    "gad_q6_irritability": 1,
    "gad_q7_fear_awful": 0
  },
  "safety_flag": {"level": "none", "cues": []},
  "annotator_notes": "Need one more turn to separate fatigue from concentration more cleanly.",
  "confidence_notes": {"high_confidence_items": ["phq_q3_sleep", "phq_q7_concentration"], "low_confidence_items": ["phq_q2_low_mood"]},
  "generation_source": "synthetic_profile_guided",
  "review_status": "consensus_final"
}
```

### Example 2: Hindi

```json
{
  "conversation_id": "MB-C014",
  "patient_id": "MB-P010",
  "language": "hi",
  "age": 34,
  "occupation": "school teacher",
  "background_profile": {
    "context": "family caregiving responsibilities and long commute",
    "living_situation": "lives with spouse and in-laws",
    "support_system": "limited private time to talk"
  },
  "symptom_profile": {
    "depression_level": "mild",
    "anxiety_level": "moderate_to_high",
    "safety_signal": "none"
  },
  "conversation_turns": [
    {"turn_id": 1, "speaker": "assistant", "text": "Pichhle do hafton mein sabse zyada kis baat ne pareshan kiya?", "language_tag": "hi"},
    {"turn_id": 2, "speaker": "user", "text": "Dimag hamesha chalta rehta hai. Raat ko bhi soch band nahi hoti.", "language_tag": "hi"},
    {"turn_id": 3, "speaker": "assistant", "text": "Kya is wajah se neend ya aaraam par bhi asar pada hai?", "language_tag": "hi"},
    {"turn_id": 4, "speaker": "user", "text": "Haan, neend toot toot ke aati hai aur subah se hi ghabrahat rehti hai.", "language_tag": "hi"}
  ],
  "evidence_spans": [
    {
      "span_id": "E1",
      "questionnaire": "GAD7",
      "item_id": "gad_q2_control_worry",
      "turn_id": 2,
      "text_span": "soch band nahi hoti",
      "polarity": "present",
      "score_hint": 3,
      "annotator": "Ritwij",
      "rationale": "Difficulty controlling worry"
    },
    {
      "span_id": "E2",
      "questionnaire": "PHQ9",
      "item_id": "phq_q3_sleep",
      "turn_id": 4,
      "text_span": "neend toot toot ke aati hai",
      "polarity": "present",
      "score_hint": 2,
      "annotator": "Yash",
      "rationale": "Fragmented sleep"
    }
  ],
  "phq9_item_labels": {
    "phq_q1_anhedonia": 0,
    "phq_q2_low_mood": 1,
    "phq_q3_sleep": 2,
    "phq_q4_fatigue": 1,
    "phq_q5_appetite": 0,
    "phq_q6_worthlessness": 0,
    "phq_q7_concentration": 1,
    "phq_q8_psychomotor": 0,
    "phq_q9_self_harm": 0
  },
  "gad7_item_labels": {
    "gad_q1_nervous": 2,
    "gad_q2_control_worry": 3,
    "gad_q3_excessive_worry": 2,
    "gad_q4_trouble_relaxing": 2,
    "gad_q5_restlessness": 1,
    "gad_q6_irritability": 1,
    "gad_q7_fear_awful": 1
  },
  "safety_flag": {"level": "none", "cues": []},
  "annotator_notes": "Need care with 'ghabrahat' because it may map to anxiety, panic, or somatic stress depending on context.",
  "confidence_notes": {"high_confidence_items": ["gad_q2_control_worry", "phq_q3_sleep"], "low_confidence_items": ["phq_q2_low_mood", "gad_q7_fear_awful"]},
  "generation_source": "synthetic_profile_guided",
  "review_status": "consensus_final"
}
```

### Example 3: Hinglish / Code-Mixed

```json
{
  "conversation_id": "MB-C031",
  "patient_id": "MB-P021",
  "language": "hinglish",
  "age": 27,
  "occupation": "software tester",
  "background_profile": {
    "context": "night shifts and recent breakup",
    "living_situation": "stays alone in rented flat",
    "support_system": "mostly online friends"
  },
  "symptom_profile": {
    "depression_level": "moderate",
    "anxiety_level": "moderate",
    "safety_signal": "review_needed"
  },
  "conversation_turns": [
    {"turn_id": 1, "speaker": "assistant", "text": "Aaj kal emotionally sabse heavy kya lag raha hai?", "language_tag": "hinglish"},
    {"turn_id": 2, "speaker": "user", "text": "Honestly mann nahi lagta. Kaam kar leta hoon but bas mechanically.", "language_tag": "hinglish"},
    {"turn_id": 3, "speaker": "assistant", "text": "Aur jab aap akela feel karte ho, tab thoughts kis direction mein jaate hain?", "language_tag": "hinglish"},
    {"turn_id": 4, "speaker": "user", "text": "Kabhi kabhi lagta hai sab pointless hai, but I am not planning to hurt myself.", "language_tag": "hinglish"}
  ],
  "evidence_spans": [
    {
      "span_id": "E1",
      "questionnaire": "PHQ9",
      "item_id": "phq_q1_anhedonia",
      "turn_id": 2,
      "text_span": "mann nahi lagta",
      "polarity": "present",
      "score_hint": 2,
      "annotator": "Yash",
      "rationale": "Reduced interest / engagement"
    },
    {
      "span_id": "E2",
      "questionnaire": "PHQ9",
      "item_id": "phq_q9_self_harm",
      "turn_id": 4,
      "text_span": "sab pointless hai, but I am not planning to hurt myself",
      "polarity": "uncertain",
      "score_hint": 1,
      "annotator": "Ritwij",
      "rationale": "Hopelessness present; direct self-harm intent denied"
    }
  ],
  "phq9_item_labels": {
    "phq_q1_anhedonia": 2,
    "phq_q2_low_mood": 2,
    "phq_q3_sleep": 1,
    "phq_q4_fatigue": 1,
    "phq_q5_appetite": 0,
    "phq_q6_worthlessness": 1,
    "phq_q7_concentration": 1,
    "phq_q8_psychomotor": 0,
    "phq_q9_self_harm": 0
  },
  "gad7_item_labels": {
    "gad_q1_nervous": 1,
    "gad_q2_control_worry": 1,
    "gad_q3_excessive_worry": 1,
    "gad_q4_trouble_relaxing": 1,
    "gad_q5_restlessness": 0,
    "gad_q6_irritability": 1,
    "gad_q7_fear_awful": 1
  },
  "safety_flag": {
    "level": "review",
    "cues": ["pointlessness / hopelessness language", "self-harm denial should still be reviewed once"]
  },
  "annotator_notes": "Code-mixed denial statement should not be auto-treated as no-risk without review.",
  "confidence_notes": {"high_confidence_items": ["phq_q1_anhedonia"], "low_confidence_items": ["phq_q9_self_harm", "phq_q6_worthlessness"]},
  "generation_source": "synthetic_profile_guided",
  "review_status": "consensus_final"
}
```

## 8. Notes for Later Phases

- Real-user data, if collected later, should use the same schema so synthetic and real subsets remain comparable.
- Public auxiliary datasets should be stored separately and clearly marked as weak-label or safety-only resources.
- If voice is added later, audio metadata should be stored in a parallel schema rather than mixed into the Phase 1 text schema.
