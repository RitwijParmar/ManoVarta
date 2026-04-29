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


def test_scoring_picks_up_real_hindi_sleep_delay_and_low_interest_variants():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="नींद का पैटर्न बदल गया है, नींद काफी देर से आती है और कुछ दिनों से कम आती है। किसी काम में मन नहीं लगता है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q3_sleep"].evidence_span_ids
    assert snapshot.items["phq_q1_anhedonia"].status == "resolved"


def test_scoring_picks_up_hindi_broken_sleep_and_broken_body_opening():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="नींद बिगड़ गई है, देर से नींद आती है और सुबह उठकर शरीर टूटा सा लगता है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}


def test_scoring_picks_up_hinglish_sleep_pattern_off_and_drained_opening():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sleep ka pattern off hai, late soti hoon aur din bhar drained rehti hoon.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}


def test_scoring_picks_up_hindi_present_vs_future_sadness_phrasing():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="मैं कभी सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है, लेकिन वर्तमान देखता हूं तो उदासी आती है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q2_low_mood"].status == "resolved"


def test_scoring_does_not_treat_hinglish_fatigue_self_report_as_uncertain():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q4_fatigue"].status == "resolved"
    assert snapshot.items["phq_q4_fatigue"].value >= 2


def test_scoring_picks_up_hindi_attention_and_self_blame_variants():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="भूख भी कम हो जाती है और ध्यान भी टिकता नहीं। अपने आप पर भी गुस्सा आता है कि मैं कुछ कर क्यों नहीं पा रहा।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q7_concentration"].status == "resolved"
    assert snapshot.items["phq_q6_worthlessness"].status == "resolved"


def test_scoring_picks_up_short_cross_item_hindi_summary_phrase():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="उदासी और किसी काम से मन हट जाना",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q1_anhedonia"].status == "resolved"
    assert snapshot.items["phq_q2_low_mood"].status == "resolved"


def test_scoring_resolves_hindi_no_desire_to_start_work_even_with_danda():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="घबराहट जैसा नहीं है, कोई काम शुरू करने का मन नहीं करता।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q1_anhedonia"].status == "resolved"


def test_scoring_resolves_english_delay_starting_and_guilt_as_interest_and_self_view():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="It is not really panic exactly. I keep delaying starting things and then feel guilty.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q1_anhedonia"].status == "resolved"
    assert snapshot.items["phq_q6_worthlessness"].status == "resolved"


def test_scoring_resolves_direct_hindi_sleep_functioning_cluster():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="नींद देर से आती है, नींद कम आती है, सुबह उठकर शरीर भारी लगता है, कई बार खाना छोड़ देता हूं, ध्यान टूट जाता है, और अपने ऊपर झुंझलाहट होती है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q4_fatigue"].status == "resolved"
    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q7_concentration"].status == "resolved"
    assert snapshot.items["phq_q6_worthlessness"].status == "resolved"


def test_scoring_resolves_direct_hinglish_focus_appetite_and_body_slow_cluster():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Meals skip ho jate hain, bhook pe dhyan nahi rehta, same line baar baar padhni padti hai, aur shaam tak body slow ho jati hai.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q7_concentration"].status == "resolved"
    assert snapshot.items["phq_q8_psychomotor"].status == "resolved"


def test_scoring_resolves_direct_english_appetite_self_view_and_body_slow_cluster():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="I eat because I have to, skip meals without noticing, feel frustrated with myself, and my body feels slow by evening.",
            language_tag="en",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "en", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q6_worthlessness"].status == "resolved"
    assert snapshot.items["phq_q8_psychomotor"].status == "resolved"


def test_scoring_picks_up_hinglish_burden_phrase():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Kabhi lagta hai main sabke liye burden ban raha hoon.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q6_worthlessness"].status == "resolved"
    assert snapshot.items["phq_q6_worthlessness"].value >= 2


def test_scoring_picks_up_hinglish_low_energy_patchy_sleep_and_delayed_meals_variants():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Past few days body heavy lag rahi hai and uthne ka mann nahi karta.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="Sleep thodi patchy hai but main issue low energy hai.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=3,
            speaker="user",
            text="Meals delay ho jate hain and focus bhi toot jata hai.",
            language_tag="hinglish",
        ),
        Turn(
            turn_id=4,
            speaker="user",
            text="Mind slow start hota hai but panic jaisa nahi hota.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q5_appetite"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q7_concentration"].status in {"resolved", "partial"}


def test_scoring_keeps_hinglish_fatigue_present_when_worry_is_downplayed():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Worry utni nahi hai, bas thakan aur udasi zyada lagti hai.",
            language_tag="hinglish",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q2_low_mood"].status in {"resolved", "partial"}
    assert snapshot.items["gad_q2_control_worry"].value in {None, 0}


def test_scoring_picks_up_hindi_appetite_and_attention_break_variants():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="भूख भी थोड़ी गड़बड़ है और काम पर ध्यान टूटता है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q7_concentration"].status == "resolved"


def test_scoring_picks_up_drag_through_day_and_screen_reread_variants():
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Even when I finally sleep, I still drag through the day and skip meals sometimes.",
            language_tag="en",
        ),
        Turn(
            turn_id=2,
            speaker="user",
            text="काम पर ध्यान नहीं टिकता और एक ही चीज़ बार-बार पढ़नी पड़ती है।",
            language_tag="hi",
        ),
    ]

    snapshot = ConversationScorer().analyze(turns, "hi", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q4_fatigue"].status == "resolved"
    assert snapshot.items["phq_q5_appetite"].status == "resolved"
    assert snapshot.items["phq_q7_concentration"].status == "resolved"


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


def test_scoring_captures_human_style_long_conversation_phrasing_across_languages():
    scorer = ConversationScorer()

    english_turns = [
        Turn(turn_id=1, speaker="user", text="I've been dragging myself through the day and sleep has been broken for the last couple of weeks.", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="By the afternoon my body feels heavy and my mind is slow to get going again.", language_tag="en"),
        Turn(turn_id=3, speaker="user", text="I still get work done but everything feels flat underneath.", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="The worry is mostly about work and whether I'll mess up my future.", language_tag="en"),
        Turn(turn_id=5, speaker="user", text="I do not want to hurt myself. I just want the thoughts to slow down.", language_tag="en"),
    ]
    english_snapshot = scorer.analyze(english_turns, "en", SafetyMonitor().assess(english_turns))
    assert english_snapshot.coverage.touched_items >= 5
    assert english_snapshot.items["phq_q3_sleep"].value >= 2
    assert english_snapshot.items["phq_q4_fatigue"].value >= 2
    assert english_snapshot.items["phq_q1_anhedonia"].value >= 1
    assert english_snapshot.items["gad_q2_control_worry"].value >= 2
    assert english_snapshot.items["gad_q3_excessive_worry"].value >= 1

    hindi_turns = [
        Turn(turn_id=1, speaker="user", text="पिछले दो हफ्तों से रात में नींद टूटती रहती है और सुबह शुरू होने में बहुत समय लगता है।", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="दिन में आलस रहता है और काम शुरू करने से पहले ही मन हट जाता है।", language_tag="hi"),
        Turn(turn_id=3, speaker="user", text="जो चीज़ें पहले अच्छी लगती थीं अब उनमें बहुत कम महसूस होता है।", language_tag="hi"),
        Turn(turn_id=4, speaker="user", text="चिंता ज़्यादातर नौकरी और भविष्य को लेकर रहती है।", language_tag="hi"),
        Turn(turn_id=5, speaker="user", text="खुद को नुकसान पहुंचाने का मन नहीं है, बस दिमाग शांत नहीं होता।", language_tag="hi"),
    ]
    hindi_snapshot = scorer.analyze(hindi_turns, "hi", SafetyMonitor().assess(hindi_turns))
    assert hindi_snapshot.coverage.touched_items >= 5
    assert hindi_snapshot.safety.level == "none"
    assert hindi_snapshot.items["phq_q3_sleep"].value >= 2
    assert hindi_snapshot.items["phq_q4_fatigue"].value >= 2
    assert hindi_snapshot.items["phq_q1_anhedonia"].value >= 1
    assert hindi_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hindi_snapshot.items["gad_q3_excessive_worry"].value >= 1

    hinglish_turns = [
        Turn(turn_id=1, speaker="user", text="Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.", language_tag="hinglish"),
        Turn(turn_id=2, speaker="user", text="Day ke end tak body heavy lagti hai aur focus toot jata hai.", language_tag="hinglish"),
        Turn(turn_id=3, speaker="user", text="Jo cheezein pehle achhi lagti thi ab flat feel hoti hain.", language_tag="hinglish"),
        Turn(turn_id=4, speaker="user", text="Worry zyada work aur future ke around rehti hai.", language_tag="hinglish"),
        Turn(turn_id=5, speaker="user", text="Mind ko quiet karna tough hota hai, body tension utni badi baat nahi.", language_tag="hinglish"),
        Turn(turn_id=6, speaker="user", text="Mujhe hurt karne ka plan nahi hai, bas thoughts rukte nahi.", language_tag="hinglish"),
    ]
    hinglish_snapshot = scorer.analyze(hinglish_turns, "hinglish", SafetyMonitor().assess(hinglish_turns))
    assert hinglish_snapshot.coverage.touched_items >= 6
    assert hinglish_snapshot.safety.level == "none"
    assert hinglish_snapshot.items["phq_q3_sleep"].value >= 2
    assert hinglish_snapshot.items["phq_q4_fatigue"].value >= 2
    assert hinglish_snapshot.items["phq_q7_concentration"].value >= 1
    assert hinglish_snapshot.items["phq_q1_anhedonia"].value >= 1
    assert hinglish_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hinglish_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert hinglish_snapshot.items["gad_q4_trouble_relaxing"].value >= 1


def test_scoring_captures_dense_human_style_followups_across_languages():
    scorer = ConversationScorer()

    english_turns = [
        Turn(turn_id=1, speaker="user", text="By the afternoon my body feels heavy, my appetite is off, and lunch just slips.", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="When I fall behind I get pretty harsh on myself and feel like I am letting people down.", language_tag="en"),
        Turn(turn_id=3, speaker="user", text="Focus breaks a lot, so I reread the same line and small tasks take forever.", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="The worry jumps between work mistakes, money, and what that means for my future.", language_tag="en"),
        Turn(turn_id=5, speaker="user", text="Mostly it is hard to quiet my mind; the body tension is there but smaller.", language_tag="en"),
        Turn(turn_id=6, speaker="user", text="Some evenings I feel restless and snappy even though I know nobody is doing anything wrong.", language_tag="en"),
        Turn(turn_id=7, speaker="user", text="I do not want to hurt myself or die, I just want a working summary.", language_tag="en"),
    ]
    english_snapshot = scorer.analyze(english_turns, "en", SafetyMonitor().assess(english_turns))
    assert english_snapshot.items["phq_q5_appetite"].value >= 2
    assert english_snapshot.items["phq_q6_worthlessness"].value >= 2
    assert english_snapshot.items["phq_q7_concentration"].value >= 1
    assert english_snapshot.items["gad_q2_control_worry"].value >= 2
    assert english_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert english_snapshot.items["gad_q4_trouble_relaxing"].value >= 1
    assert english_snapshot.items["gad_q5_restlessness"].value >= 1
    assert english_snapshot.items["gad_q6_irritability"].value >= 1
    assert english_snapshot.items["phq_q9_self_harm"].status == "resolved"

    hindi_turns = [
        Turn(turn_id=1, speaker="user", text="दिन चढ़ते-चढ़ते आलस बढ़ जाता है, भूख भी कम हो जाती है और कई बार खाना छूट जाता है।", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="पीछे रह जाऊँ तो मैं खुद को बहुत कोसता हूँ और लगता है मैं सब पर बोझ बन रहा हूँ।", language_tag="hi"),
        Turn(turn_id=3, speaker="user", text="ध्यान बार-बार टूटता है, एक ही लाइन दोबारा पढ़नी पड़ती है और छोटे काम भी लंबे लगते हैं।", language_tag="hi"),
        Turn(turn_id=4, speaker="user", text="चिंता काम, पैसों और भविष्य के बीच घूमती रहती है।", language_tag="hi"),
        Turn(turn_id=5, speaker="user", text="ज़्यादा दिमाग को शांत करना मुश्किल होता है; शरीर वाला हिस्सा है लेकिन उतना बड़ा नहीं।", language_tag="hi"),
        Turn(turn_id=6, speaker="user", text="कुछ शामों में बेचैनी और चिड़चिड़ापन दोनों बढ़ जाते हैं।", language_tag="hi"),
        Turn(turn_id=7, speaker="user", text="खुद को नुकसान पहुंचाने का मन नहीं है, बस अभी तक का सार चाहिए।", language_tag="hi"),
    ]
    hindi_snapshot = scorer.analyze(hindi_turns, "hi", SafetyMonitor().assess(hindi_turns))
    assert hindi_snapshot.items["phq_q5_appetite"].value >= 2
    assert hindi_snapshot.items["phq_q6_worthlessness"].value >= 2
    assert hindi_snapshot.items["phq_q7_concentration"].value >= 1
    assert hindi_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hindi_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert hindi_snapshot.items["gad_q4_trouble_relaxing"].value >= 1
    assert hindi_snapshot.items["gad_q5_restlessness"].value >= 1
    assert hindi_snapshot.items["gad_q6_irritability"].value >= 1
    assert hindi_snapshot.items["phq_q9_self_harm"].status == "resolved"

    hinglish_turns = [
        Turn(turn_id=1, speaker="user", text="Day chadhte chadhte aalas badh jata hai, appetite bhi down ho jaati hai aur lunch miss ho jata hai.", language_tag="hinglish"),
        Turn(turn_id=2, speaker="user", text="Peeche reh jaun to main khud par kaafi harsh ho jata hoon aur burden jaisa feel hota hai.", language_tag="hinglish"),
        Turn(turn_id=3, speaker="user", text="Focus toot jata hai, same line dobara padhni padti hai, aur small tasks slow lagte hain.", language_tag="hinglish"),
        Turn(turn_id=4, speaker="user", text="Worry work mistakes, paise, aur future ke beech jump karti rehti hai.", language_tag="hinglish"),
        Turn(turn_id=5, speaker="user", text="Mind ko quiet karna tough hota hai; body side hai but smaller lagti hai.", language_tag="hinglish"),
        Turn(turn_id=6, speaker="user", text="Kuch evenings mein restlessness aur irritability dono badh jaate hain.", language_tag="hinglish"),
        Turn(turn_id=7, speaker="user", text="Khud ko hurt karne ka plan nahi hai, bas abhi ka working summary chahiye.", language_tag="hinglish"),
    ]
    hinglish_snapshot = scorer.analyze(hinglish_turns, "hinglish", SafetyMonitor().assess(hinglish_turns))
    assert hinglish_snapshot.items["phq_q5_appetite"].value >= 2
    assert hinglish_snapshot.items["phq_q6_worthlessness"].value >= 2
    assert hinglish_snapshot.items["phq_q7_concentration"].value >= 1
    assert hinglish_snapshot.items["gad_q2_control_worry"].value >= 2
    assert hinglish_snapshot.items["gad_q3_excessive_worry"].value >= 1
    assert hinglish_snapshot.items["gad_q4_trouble_relaxing"].value >= 1
    assert hinglish_snapshot.items["gad_q5_restlessness"].value >= 1
    assert hinglish_snapshot.items["gad_q6_irritability"].value >= 1
    assert hinglish_snapshot.items["phq_q9_self_harm"].status == "resolved"


def test_scoring_resolves_indirect_scene_style_followups_more_completely():
    scorer = ConversationScorer()

    english_turns = [
        Turn(turn_id=1, speaker="user", text="I've been dragging myself through the day and sleep has been broken for the last couple of weeks.", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="Most nights I wake around 3 or 4 and then lie there replaying work stuff.", language_tag="en"),
        Turn(turn_id=3, speaker="user", text="By the afternoon my body feels heavy, my appetite is off, and lunch just slips.", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="I still get through things but everything feels flat underneath before I even start.", language_tag="en"),
        Turn(turn_id=5, speaker="user", text="When I fall behind I get pretty harsh on myself and feel like I am letting people down.", language_tag="en"),
        Turn(turn_id=6, speaker="user", text="Focus breaks a lot, so I reread the same line and small tasks take forever.", language_tag="en"),
        Turn(turn_id=7, speaker="user", text="The worry jumps between work mistakes, money, and what that means for my future.", language_tag="en"),
        Turn(turn_id=8, speaker="user", text="Mostly it is hard to quiet my mind; the body tension is there but smaller.", language_tag="en"),
        Turn(turn_id=9, speaker="user", text="Some evenings I feel restless and snappy even though I know nobody is doing anything wrong.", language_tag="en"),
        Turn(turn_id=10, speaker="user", text="I do not want to hurt myself or die, I just want a working summary.", language_tag="en"),
    ]
    english_snapshot = scorer.analyze(english_turns, "en", SafetyMonitor().assess(english_turns))
    assert english_snapshot.items["phq_q2_low_mood"].status == "resolved"
    assert english_snapshot.items["phq_q8_psychomotor"].status == "resolved"
    assert english_snapshot.items["gad_q1_nervous"].status == "resolved"
    assert english_snapshot.items["gad_q6_irritability"].status == "resolved"
    assert english_snapshot.items["gad_q7_afraid"].status == "resolved"

    hindi_turns = [
        Turn(turn_id=1, speaker="user", text="पिछले दो हफ्तों से रात में नींद टूटती रहती है और सुबह शुरू होने में बहुत समय लगता है।", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="अक्सर रात के तीन-चार बजे उठ जाता हूँ और फिर काम की बातें दिमाग में चलती रहती हैं।", language_tag="hi"),
        Turn(turn_id=3, speaker="user", text="दिन चढ़ते-चढ़ते आलस बढ़ जाता है, भूख भी कम हो जाती है और कई बार खाना छूट जाता है।", language_tag="hi"),
        Turn(turn_id=4, speaker="user", text="जो चीज़ें पहले अच्छी लगती थीं, अब शुरू करने से पहले ही मन हट जाता है और अंदर से सब फीका लगता है।", language_tag="hi"),
        Turn(turn_id=5, speaker="user", text="पीछे रह जाऊँ तो मैं खुद को बहुत कोसता हूँ और लगता है मैं सब पर बोझ बन रहा हूँ।", language_tag="hi"),
        Turn(turn_id=6, speaker="user", text="ध्यान बार-बार टूटता है, एक ही लाइन दोबारा पढ़नी पड़ती है और छोटे काम भी लंबे लगते हैं।", language_tag="hi"),
        Turn(turn_id=7, speaker="user", text="चिंता काम, पैसों और भविष्य के बीच घूमती रहती है।", language_tag="hi"),
        Turn(turn_id=8, speaker="user", text="ज़्यादा दिमाग को शांत करना मुश्किल होता है; शरीर वाला हिस्सा है लेकिन उतना बड़ा नहीं।", language_tag="hi"),
        Turn(turn_id=9, speaker="user", text="कुछ शामों में बेचैनी और चिड़चिड़ापन दोनों बढ़ जाते हैं।", language_tag="hi"),
        Turn(turn_id=10, speaker="user", text="खुद को नुकसान पहुंचाने का मन नहीं है, बस अभी तक का सार चाहिए।", language_tag="hi"),
    ]
    hindi_snapshot = scorer.analyze(hindi_turns, "hi", SafetyMonitor().assess(hindi_turns))
    assert hindi_snapshot.items["phq_q1_anhedonia"].status == "resolved"
    assert hindi_snapshot.items["phq_q2_low_mood"].status == "resolved"
    assert hindi_snapshot.items["phq_q8_psychomotor"].status == "resolved"
    assert hindi_snapshot.items["gad_q1_nervous"].status == "resolved"
    assert hindi_snapshot.items["gad_q6_irritability"].status == "resolved"
    assert hindi_snapshot.items["gad_q7_afraid"].status == "resolved"

    hinglish_turns = [
        Turn(turn_id=1, speaker="user", text="Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.", language_tag="hinglish"),
        Turn(turn_id=2, speaker="user", text="Most nights 3 ya 4 baje aankh khul jaati hai aur phir work wali soch chalti rehti hai.", language_tag="hinglish"),
        Turn(turn_id=3, speaker="user", text="Day chadhte chadhte aalas badh jata hai, appetite bhi down ho jaati hai aur lunch miss ho jata hai.", language_tag="hinglish"),
        Turn(turn_id=4, speaker="user", text="Jo cheezein pehle achhi lagti thi ab start karne se pehle hi mann hat jata hai aur sab flat feel hota hai.", language_tag="hinglish"),
        Turn(turn_id=5, speaker="user", text="Peeche reh jaun to main khud par kaafi harsh ho jata hoon aur burden jaisa feel hota hai.", language_tag="hinglish"),
        Turn(turn_id=6, speaker="user", text="Focus toot jata hai, same line dobara padhni padti hai, aur small tasks slow lagte hain.", language_tag="hinglish"),
        Turn(turn_id=7, speaker="user", text="Worry work mistakes, paise, aur future ke beech jump karti rehti hai.", language_tag="hinglish"),
        Turn(turn_id=8, speaker="user", text="Mind ko quiet karna tough hota hai; body tension hai but smaller lagti hai.", language_tag="hinglish"),
        Turn(turn_id=9, speaker="user", text="Kuch evenings mein restlessness aur irritability dono badh jaate hain.", language_tag="hinglish"),
        Turn(turn_id=10, speaker="user", text="Khud ko hurt karne ka plan nahi hai, bas abhi ka working summary chahiye.", language_tag="hinglish"),
    ]
    hinglish_snapshot = scorer.analyze(hinglish_turns, "hinglish", SafetyMonitor().assess(hinglish_turns))
    assert hinglish_snapshot.items["phq_q2_low_mood"].status == "resolved"
    assert hinglish_snapshot.items["phq_q8_psychomotor"].status == "resolved"
    assert hinglish_snapshot.items["gad_q1_nervous"].status == "resolved"
    assert hinglish_snapshot.items["gad_q6_irritability"].status == "resolved"
    assert hinglish_snapshot.items["gad_q7_afraid"].status == "resolved"


def test_generic_low_and_disconnected_opening_touches_but_does_not_fully_close_both_mood_items():
    scorer = ConversationScorer()
    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Kaafi time se low aur disconnected feel ho raha hai.",
            language_tag="hinglish",
        )
    ]

    snapshot = scorer.analyze(turns, "hinglish", SafetyMonitor().assess(turns))

    assert snapshot.items["phq_q1_anhedonia"].status == "partial"
    assert snapshot.items["phq_q2_low_mood"].status == "partial"


def test_scoring_captures_messy_sleep_energy_appetite_and_focus_phrasing():
    scorer = ConversationScorer()

    english_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sleep has shifted later. The next day I drag through everything, lunch just slips, and I have to read the same paragraph three times.",
            language_tag="en",
        ),
    ]
    english_snapshot = scorer.analyze(english_turns, "en", SafetyMonitor().assess(english_turns))
    assert english_snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert english_snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}
    assert english_snapshot.items["phq_q5_appetite"].status in {"resolved", "partial"}
    assert english_snapshot.items["phq_q7_concentration"].status in {"resolved", "partial"}

    hindi_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="नींद देर से आती है, दोपहर का खाना छूट जाता है, और वही लाइन कई बार पढ़नी पड़ती है।",
            language_tag="hi",
        ),
    ]
    hindi_snapshot = scorer.analyze(hindi_turns, "hi", SafetyMonitor().assess(hindi_turns))
    assert hindi_snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert hindi_snapshot.items["phq_q5_appetite"].status in {"resolved", "partial"}
    assert hindi_snapshot.items["phq_q7_concentration"].status in {"resolved", "partial"}

    hinglish_turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Sleep shifted later hai, pura system drag karta hai, dopahar ka khana chhut jata hai, aur same paragraph three times padhna padta hai.",
            language_tag="hinglish",
        ),
    ]
    hinglish_snapshot = scorer.analyze(hinglish_turns, "hinglish", SafetyMonitor().assess(hinglish_turns))
    assert hinglish_snapshot.items["phq_q3_sleep"].status in {"resolved", "partial"}
    assert hinglish_snapshot.items["phq_q4_fatigue"].status in {"resolved", "partial"}
    assert hinglish_snapshot.items["phq_q5_appetite"].status in {"resolved", "partial"}
    assert hinglish_snapshot.items["phq_q7_concentration"].status in {"resolved", "partial"}


def test_scoring_captures_flat_dragged_tense_and_snappy_phrasing():
    scorer = ConversationScorer()

    turns = [
        Turn(
            turn_id=1,
            speaker="user",
            text="Stuff I care about feels flat and heavy, my whole body feels dragged, body side is there but smaller, and evenings I get snappy.",
            language_tag="en",
        ),
    ]

    snapshot = scorer.analyze(turns, "en", SafetyMonitor().assess(turns))
    assert snapshot.items["phq_q1_anhedonia"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q2_low_mood"].status in {"resolved", "partial"}
    assert snapshot.items["phq_q8_psychomotor"].status in {"resolved", "partial"}
    assert snapshot.items["gad_q4_trouble_relaxing"].status in {"resolved", "partial"}
    assert snapshot.items["gad_q6_irritability"].status in {"resolved", "partial"}
