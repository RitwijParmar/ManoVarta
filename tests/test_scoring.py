from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn


def test_scoring_keeps_local_symptom_context():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How have things felt lately?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I feel drained all day and my sleep schedule is messed up.",
            language_tag="en",
        ),
    ]

    safety = SafetyMonitor().assess(turns)
    snapshot = ConversationScorer().analyze(turns, "en", safety)

    assert snapshot.items["phq_q3_sleep"].value == 2
    assert snapshot.items["phq_q4_fatigue"].value == 3
    assert snapshot.items["phq_q9_self_harm"].value is None


def test_scoring_picks_up_hindi_worry_and_sleep():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="Pichhle do hafton mein sabse zyada kya pareshan kar raha hai?", language_tag="hi"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Dimag hamesha chalta rehta hai aur raat ko soch band nahi hoti.",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Neend toot toot ke aati hai.",
            language_tag="hi",
        ),
    ]

    safety = SafetyMonitor().assess(turns)
    snapshot = ConversationScorer().analyze(turns, "hi", safety)

    assert snapshot.items["gad_q2_control_worry"].value == 3
    assert snapshot.items["phq_q3_sleep"].value == 2


def test_scoring_abstains_on_unresolved_contradiction():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How has your sleep been?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I don't keep waking up at night.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Actually before exams I keep waking up and my sleep schedule is messed up.",
            language_tag="en",
        ),
    ]

    safety = SafetyMonitor().assess(turns)
    snapshot = ConversationScorer().analyze(turns, "en", safety)

    sleep_item = snapshot.items["phq_q3_sleep"]
    assert sleep_item.status == "abstained"
    assert sleep_item.value is None
    assert sleep_item.review_recommended is True
    assert "phq_q3_sleep" in snapshot.coverage.abstained_items
    assert "phq_q3_sleep" in snapshot.coverage.review_items


def test_scoring_picks_up_hindi_appetite_and_self_worth_cues():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="Rozmarra din ka sabse mushkil hissa kya lag raha hai?", language_tag="hi"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Subah se thakan rehti hai, bhook bhi pehle jaisi nahi hai aur bas samay dekhkar kuch kha leti hoon.",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Kai baar lagta hai ki main itni kamzor kyon pad rahi hoon aur baaki sab mujhse behtar sambhal lete hain.",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q5_appetite"].value == 2
    assert snapshot.items["phq_q6_worthlessness"].value >= 2


def test_scoring_picks_up_devanagari_hindi_concentration_anxiety_and_self_blame():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="इन दिनों सबसे भारी क्या लग रहा है?", language_tag="hi"),
        Turn(
            turn_id=2,
            speaker="user",
            text="दिन भर जैसे सिर भरा-भरा रहता है और मन किसी चीज़ में टिकता नहीं। छाती में घबराहट रहती है।",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="कई बार लगता है कि अगर मैं थोड़ी और संभली हुई होती तो घर का माहौल इतना बोझिल नहीं होता।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q7_concentration"].value >= 1
    assert snapshot.items["gad_q1_nervous"].value >= 2
    assert snapshot.items["phq_q6_worthlessness"].value >= 2


def test_scoring_picks_up_devanagari_hindi_review_and_urgent_cues():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="कभी ऐसा लगता है कि कहीं दूर चले जाएँ?", language_tag="hi"),
        Turn(
            turn_id=2,
            speaker="user",
            text="कभी-कभी लगता है बस कहीं निकल जाऊँ जहाँ कोई मुझे जानता ही न हो। ऐसा सोचकर डर भी लगता है।",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="दो बार मैंने सोचा कि दुकान की दवाइयाँ एक साथ खा लूँ।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q9_self_harm"].value >= 2
    assert snapshot.items["gad_q7_fear_awful"].value >= 1


def test_scoring_picks_up_hinglish_worry_relaxing_and_restlessness():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="Aajkal sabse zyada kya chal raha hai?", language_tag="hinglish"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Shift khatam hone ke baad bhi brain running mode mein rehta hai aur off day pe bhi body relaxed nahi hoti.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Kabhi itni bechaini hoti hai ki room mein idhar-udhar chakkar lagata rehta hoon, aur choti si baat pe irritation aa jati hai.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["gad_q2_control_worry"].value >= 2
    assert snapshot.items["gad_q4_trouble_relaxing"].value >= 2
    assert snapshot.items["gad_q5_restlessness"].value >= 2
    assert snapshot.items["gad_q6_irritability"].value >= 1
