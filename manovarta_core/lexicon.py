from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class PhraseRule:
    item_id: str
    questionnaire: str
    phrases: Tuple[str, ...]
    score_hint: int
    rationale: str


RULES: List[PhraseRule] = [
    PhraseRule("phq_q1_anhedonia", "PHQ9", ("don't enjoy anything", "nothing feels enjoyable", "mann hi nahi karta", "man nahi karta", "kuch accha nahi lagta"), 2, "reduced interest"),
    PhraseRule("phq_q2_low_mood", "PHQ9", ("feel low", "feel down", "empty most days", "blank feel hota", "udaas rehta", "bahut udaas", "khali khali lagta"), 2, "low mood"),
    PhraseRule("phq_q3_sleep", "PHQ9", ("can't sleep", "sleep schedule is messed up", "keep waking up", "sleep break hoti", "neend nahi aati", "neend toot", "sone mein dikkat"), 2, "sleep trouble"),
    PhraseRule("phq_q4_fatigue", "PHQ9", ("always tired", "drained all day", "no energy", "thakawat rehti", "hamesha thaka", "bilkul energy nahi"), 2, "fatigue"),
    PhraseRule("phq_q5_appetite", "PHQ9", ("not eating much", "eating too much", "appetite is off", "bhook nahi lagti", "zyada khana", "khane ka mann nahi"), 2, "appetite change"),
    PhraseRule("phq_q6_worthlessness", "PHQ9", ("feel like a burden", "feel useless", "it's my fault", "main bojh hoon", "khud ko bekaar lagta", "sab meri galti"), 3, "worthlessness"),
    PhraseRule("phq_q7_concentration", "PHQ9", ("can't focus", "nothing sticks", "mind keeps drifting", "dhyan nahi lagta", "focus nahi hota", "dimag tikta nahi"), 2, "concentration trouble"),
    PhraseRule("phq_q8_psychomotor", "PHQ9", ("moving slowly", "talking slowly", "so restless i pace", "bahut bechain ho jata", "ek jagah tik nahi pata"), 1, "psychomotor change"),
    PhraseRule("phq_q9_self_harm", "PHQ9", ("don't want to live", "want to disappear", "hurt myself", "mar jana chahta", "khatam kar doon", "jeene ka mann nahi"), 3, "self-harm concern"),
    PhraseRule("gad_q1_nervous", "GAD7", ("always on edge", "feel anxious", "constantly nervous", "ghabrahat rehti", "bahut tension rehta", "andar se ghabrahat"), 2, "nervousness"),
    PhraseRule("gad_q2_control_worry", "GAD7", ("can't stop worrying", "mind won't stop", "thoughts won't stop", "worry doesn't stop", "soch band nahi hoti", "fikar rukti nahi", "worry control nahi hota"), 3, "worry control"),
    PhraseRule("gad_q3_excessive_worry", "GAD7", ("worry about everything", "keep thinking about every outcome", "har chiz ki chinta", "har baat ka darr", "sab cheezon ki fikar"), 2, "excessive worry"),
    PhraseRule("gad_q4_trouble_relaxing", "GAD7", ("can't relax", "can't switch off", "never feel settled", "aaraam nahi milta", "relax nahi kar pata", "chain nahi milta"), 2, "trouble relaxing"),
    PhraseRule("gad_q5_restlessness", "GAD7", ("can't sit still", "keep pacing", "restless all evening", "bechain rehta", "chain se baith nahi pata"), 2, "restlessness"),
    PhraseRule("gad_q6_irritability", "GAD7", ("snapping at people", "getting irritated easily", "choti baat par gussa", "jaldi irritate ho jata"), 1, "irritability"),
    PhraseRule("gad_q7_fear_awful", "GAD7", ("something bad will happen", "waiting for the worst", "lagta hai kuch bura hoga", "dar lagta hai sab kharab ho jayega"), 2, "fear of awful outcome"),
]

RULE_INDEX: DefaultDict[str, List[PhraseRule]] = defaultdict(list)
for rule in RULES:
    RULE_INDEX[rule.item_id].append(rule)

NEGATION_CUES = (
    "not",
    "don't",
    "dont",
    "never",
    "no",
    "nahi",
    "nahin",
    "nahi hai",
    "bilkul nahi",
)

HIGH_INTENSITY_CUES = (
    "every day",
    "all day",
    "most days",
    "constantly",
    "always",
    "hamesha",
    "roz",
    "lagatar",
    "har din",
    "bahut zyada",
)

LOW_INTENSITY_CUES = (
    "sometimes",
    "once in a while",
    "kabhi kabhi",
    "thoda",
    "thodi si",
)

UNCERTAINTY_CUES = (
    "maybe",
    "i guess",
    "sort of",
    "not sure",
    "shayad",
    "lagta hai",
)


def rules_for_item(item_id: str) -> Iterable[PhraseRule]:
    return RULE_INDEX[item_id]
