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


def test_scoring_picks_up_live_english_worry_loop_and_sleep_badly_phrasing():
    turns = [
        Turn(turn_id=1, speaker="user", text="I have been sleeping badly and worrying a lot for the last two weeks.", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I wake up around 3 or 4, feel exhausted all day, and my mind keeps looping even when I try to stop it.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].value >= 2
    assert snapshot.items["phq_q4_fatigue"].value >= 2
    assert snapshot.items["gad_q2_control_worry"].value >= 2


def test_scoring_picks_up_live_hindi_worry_loop_and_sleep_badly_phrasing():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Pichhle do hafton se meri neend kharab hai aur dimaag mein chinta chalti rehti hai.",
            language_tag="hi",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="Raat ko 3 baje aankh khul jaati hai, din bhar thakan rehti hai, aur dimaag ko rokne ki koshish karun tab bhi soch chalti rehti hai.",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].value >= 2
    assert snapshot.items["phq_q4_fatigue"].value >= 2
    assert snapshot.items["gad_q2_control_worry"].value >= 2


def test_scoring_picks_up_later_turn_interest_guilt_and_focus_phrasing():
    turns = [
        Turn(turn_id=1, speaker="user", text="Sleep has been bad and my mind keeps looping.", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I have also lost interest in music, feel guilty that I am disappointing people, and it is harder to focus in class.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Ab gaane sunne ya doston se baat karne ka mann nahi karta, khud par guilt hota hai, aur dhyan bhi kam lagta hai.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q1_anhedonia"].value >= 2
    assert snapshot.items["phq_q6_worthlessness"].value >= 1
    assert snapshot.items["phq_q7_concentration"].value >= 1


def test_scoring_captures_live_probe_wording_across_english_hindi_and_hinglish():
    english_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="For the last two weeks my sleep keeps breaking and I feel tired all day. I drag through work and even small tasks feel hard to start.",
            language_tag="en",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="A lot of it is worry about whether I will keep my job. Once it starts, my mind keeps running and I find it hard to calm down.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="It is mostly mental, not body tension. I can sometimes distract myself, but the worry comes back and the low motivation stays through the day.",
            language_tag="en",
        ),
        Turn(
            turn_id=4,
            speaker="user",
            text="What else do you want to know? I also have less interest in things and I have been pulling away from people a bit.",
            language_tag="en",
        ),
    ]
    english_snapshot = ConversationScorer().analyze(english_turns, "en", SafetyMonitor().assess(english_turns))
    assert english_snapshot.items["phq_q3_sleep"].value >= 2
    assert english_snapshot.items["phq_q4_fatigue"].value >= 2
    assert english_snapshot.items["gad_q2_control_worry"].value >= 2
    assert english_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert english_snapshot.items["phq_q1_anhedonia"].value >= 1

    hindi_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="नींद बार बार टूटती है और दिन भर आलस रहता है। किसी काम में मन नहीं लगता और शुरू करने से पहले ही मन हट जाता है।",
            language_tag="hi",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="ज्यादा चिंता भविष्य और नौकरी को लेकर रहती है। शरीर में उतना तनाव नहीं होता, केवल दिमाग चलता रहता है।",
            language_tag="hi",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="हां तो क्या जानना है आपको? बात यही है कि यह दिन भर रहता है और दिमाग को शांत करना मुश्किल होता है।",
            language_tag="hi",
        ),
        Turn(
            turn_id=4,
            speaker="user",
            text="थोड़ा आलस भी रहता है और पहले जिन चीजों में मन लगता था उनमें अब रुचि कम हो गई है।",
            language_tag="hi",
        ),
    ]
    hindi_snapshot = ConversationScorer().analyze(hindi_turns, "hi", SafetyMonitor().assess(hindi_turns))
    assert hindi_snapshot.items["phq_q3_sleep"].value >= 2
    assert hindi_snapshot.items["phq_q4_fatigue"].value >= 2
    assert hindi_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hindi_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert hindi_snapshot.items["phq_q1_anhedonia"].value >= 1

    hinglish_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sleep break hoti rehti hai aur next day pura tired feel hota hai. Kaam start karne ka bilkul mann nahi karta.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="Main zyada future aur job ko lekar worry karta hoon. Body tension utna nahi hota, but dimaag rukta hi nahi.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Ab aap aur kya jaana chahte ho? Ye din bhar background mein chalta rehta hai and motivation low rehti hai.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=4,
            speaker="user",
            text="Thoda interest bhi kam ho gaya hai, logon se distance bana leta hoon, aur kabhi kabhi bas bed se uthna heavy lagta hai.",
            language_tag="hinglish",
        ),
    ]
    hinglish_snapshot = ConversationScorer().analyze(hinglish_turns, "hinglish", SafetyMonitor().assess(hinglish_turns))
    assert hinglish_snapshot.items["phq_q3_sleep"].value >= 2
    assert hinglish_snapshot.items["phq_q4_fatigue"].value >= 1
    assert hinglish_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hinglish_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert hinglish_snapshot.items["phq_q1_anhedonia"].value >= 1


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
    assert snapshot.items["gad_q7_afraid"].value >= 1


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


def test_scoring_picks_up_english_nervous_relaxing_irritability_and_self_harm_cues():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has stress looked like lately?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="My jaw stays tight all day and I notice I am clenching my hands before difficult calls.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="By the time I get home I am snappy for no good reason and cannot really switch off.",
            language_tag="en",
        ),
        Turn(
            turn_id=4,
            speaker="user",
            text="Sometimes it feels like everyone would be better off without me around and I could just disappear.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["gad_q1_nervous"].value >= 2
    assert snapshot.items["gad_q4_trouble_relaxing"].value >= 2
    assert snapshot.items["gad_q6_irritability"].value >= 1
    assert snapshot.items["phq_q9_self_harm"].value >= 1


def test_scoring_separates_english_worry_control_from_excessive_worry_and_relaxing():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has been feeling hardest over the last couple of weeks?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Sleep is messy because my brain keeps replaying comments from my advisor, and some days I realize it is late afternoon and I still have not eaten properly.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Mostly that I am wasting everyone's time and maybe I was never cut out for this in the first place.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["gad_q2_control_worry"].value == 2
    assert snapshot.items["gad_q3_excessive_worry"].value == 2
    assert snapshot.items["gad_q4_trouble_relaxing"].value == 1


def test_scoring_captures_english_multi_domain_worry_and_relaxing_cues():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What do you find yourself worrying about most once you get home?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="By the time I get home I am snappy for no good reason, replay whole conversations, and cannot really switch off.",
            language_tag="en",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Mostly that I am going to say the wrong thing, get written up, and suddenly not be able to cover rent.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["gad_q2_control_worry"].value == 2
    assert snapshot.items["gad_q3_excessive_worry"].value == 2
    assert snapshot.items["gad_q4_trouble_relaxing"].value == 2
