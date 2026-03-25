from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class QuestionnaireItem:
    item_id: str
    questionnaire: str
    label: str
    focus: str
    priority: int


PHQ9_ITEMS: List[QuestionnaireItem] = [
    QuestionnaireItem("phq_q1_anhedonia", "PHQ9", "Reduced interest", "loss of interest or pleasure", 3),
    QuestionnaireItem("phq_q2_low_mood", "PHQ9", "Low mood", "sadness, hopelessness, or emptiness", 3),
    QuestionnaireItem("phq_q3_sleep", "PHQ9", "Sleep", "sleep disturbance or oversleeping", 2),
    QuestionnaireItem("phq_q4_fatigue", "PHQ9", "Fatigue", "low energy or tiredness", 2),
    QuestionnaireItem("phq_q5_appetite", "PHQ9", "Appetite", "eating too much or too little", 2),
    QuestionnaireItem("phq_q6_worthlessness", "PHQ9", "Worthlessness", "guilt, shame, or feeling like a burden", 3),
    QuestionnaireItem("phq_q7_concentration", "PHQ9", "Concentration", "focus or decision trouble", 2),
    QuestionnaireItem("phq_q8_psychomotor", "PHQ9", "Psychomotor", "moving or speaking too slowly or feeling keyed up", 1),
    QuestionnaireItem("phq_q9_self_harm", "PHQ9", "Self-harm", "self-harm or suicidal thinking", 5),
]

GAD7_ITEMS: List[QuestionnaireItem] = [
    QuestionnaireItem("gad_q1_nervous", "GAD7", "Nervousness", "feeling anxious, on edge, or uneasy", 3),
    QuestionnaireItem("gad_q2_control_worry", "GAD7", "Control worry", "difficulty stopping or controlling worry", 3),
    QuestionnaireItem("gad_q3_excessive_worry", "GAD7", "Excessive worry", "worrying about many things", 2),
    QuestionnaireItem("gad_q4_trouble_relaxing", "GAD7", "Relaxing", "difficulty relaxing or settling down", 2),
    QuestionnaireItem("gad_q5_restlessness", "GAD7", "Restlessness", "restlessness or pacing", 2),
    QuestionnaireItem("gad_q6_irritability", "GAD7", "Irritability", "being more irritable or snappy", 1),
    QuestionnaireItem("gad_q7_fear_awful", "GAD7", "Something awful", "fear that something bad will happen", 2),
]

ITEM_INDEX: Dict[str, QuestionnaireItem] = {
    item.item_id: item for item in [*PHQ9_ITEMS, *GAD7_ITEMS]
}


def all_items() -> Iterable[QuestionnaireItem]:
    return ITEM_INDEX.values()


def grouped_items() -> Dict[str, List[QuestionnaireItem]]:
    return {"PHQ9": PHQ9_ITEMS, "GAD7": GAD7_ITEMS}
