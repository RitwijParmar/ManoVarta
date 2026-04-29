# Local Predeploy Conversation Audit (Scene Planner)

## en

- final stage: `summary`
- touched: `5/16`
- resolved: `0`
- safety: `none`
- totals: `PHQ9=8` `GAD7=0`

1. stage=`clarification` topic=`sleep` item=`phq_q3_sleep` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: I've been dragging myself through the day and sleep has been broken for the last couple of weeks.
   assistant: It sounds like sleep is getting hit in a real way. When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?
2. stage=`clarification` topic=`sleep` item=`phq_q3_sleep` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: Most nights I wake around 3 or 4 and then lie there replaying work stuff.
   assistant: It sounds like sleep is taking a real hit here. When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?
3. stage=`clarification` topic=`energy` item=`phq_q5_appetite` scene=`None` closure=`False` touched=`3` resolved=`0` safety=`none`
   user: By the afternoon my body feels heavy, my appetite is off, and lunch just slips.
   assistant: Has appetite mostly been lower than usual, higher than usual, or more irregular because meals get skipped or delayed?
4. stage=`clarification` topic=`mood` item=`phq_q1_anhedonia` scene=`None` closure=`False` touched=`4` resolved=`0` safety=`none`
   user: I still get through things but everything feels flat underneath before I even start.
   assistant: It sounds like the emotional weight itself has been hard to carry. When you try to do things you usually care about, does the interest drop before you start, or do you go through with them but feel very little from them?
5. stage=`clarification` topic=`mood` item=`phq_q2_low_mood` scene=`mood_selfview` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: When I fall behind I get pretty harsh on myself and feel like I am letting people down.
   assistant: When the harder days hit, what lands most in the foreground: feeling low, losing interest before you even start, or getting harsher on yourself?
6. stage=`clarification` topic=`focus` item=`phq_q7_concentration` scene=`None` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: Focus breaks a lot, so I reread the same line and small tasks take forever.
   assistant: It sounds like this is getting in the way of staying with tasks. When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?
7. stage=`clarification` topic=`anxiety` item=`gad_q2_control_worry` scene=`worry_shape` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: The worry jumps between work mistakes, money, and what that means for my future.
   assistant: It sounds like the worry is staying active even when things are quiet. When the worry starts, which shape fits it best: a keyed-up feeling in the background, one thought-loop you cannot shake, or several work or future worries piling together?
8. stage=`clarification` topic=`anxiety` item=`gad_q4_trouble_relaxing` scene=`worry_activation` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: Mostly it is hard to quiet my mind; the body tension is there but smaller.
   assistant: It sounds like settling down is taking more effort than it should. And when it peaks, what stands out more: hard to quiet the mind, restlessness, irritability, or a sense that something may go wrong next?
9. stage=`clarification` topic=`anxiety` item=`gad_q5_restlessness` scene=`worry_activation` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: Some evenings I feel restless and snappy even though I know nobody is doing anything wrong.
   assistant: It sounds like the worry is staying active even when things are quiet. When that restless feeling shows up, is it more that your body cannot sit still, or that your mind feels agitated even if you stay still?
10. stage=`summary` topic=`safety` item=`phq_q9_self_harm` scene=`None` closure=`False` touched=`5` resolved=`0` safety=`none`
   user: I do not want to hurt myself or die, I just want a working summary.
   assistant: Here is the working picture so far: interest tends to drop before getting started; sleep looks disrupted rather than settled; the worry seems to pull both thoughts and body tension together. If one detail still matters to clarify, anxiety is the next best place to tighten.

## hi

- final stage: `clarification`
- touched: `4/16`
- resolved: `0`
- safety: `none`
- totals: `PHQ9=4` `GAD7=5`

1. stage=`clarification` topic=`sleep` item=`phq_q3_sleep` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: पिछले दो हफ्तों से रात में नींद टूटती रहती है और सुबह शुरू होने में बहुत समय लगता है।
   assistant: लगता है इसका असर नींद पर साफ़ पड़ रहा है। जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?
2. stage=`clarification` topic=`energy` item=`phq_q5_appetite` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: ज़्यादातर 3-4 बजे आंख खुल जाती है और फिर काम की बातें दिमाग में चलती रहती हैं।
   assistant: क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?
3. stage=`clarification` topic=`energy` item=`phq_q5_appetite` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: दिन चढ़ते-चढ़ते आलस बढ़ जाता है, भूख भी कम हो जाती है और कई बार खाना छूट जाता है।
   assistant: क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?
4. stage=`clarification` topic=`energy` item=`phq_q5_appetite` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: जो चीज़ें पहले अच्छी लगती थीं अब शुरू करने से पहले ही मन हट जाता है।
   assistant: क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?
5. stage=`clarification` topic=`self_view` item=`phq_q6_worthlessness` scene=`None` closure=`True` touched=`2` resolved=`0` safety=`none`
   user: पीछे रह जाऊँ तो मैं खुद को बहुत कोसता हूँ और लगता है मैं सब पर बोझ बन रहा हूँ।
   assistant: लगता है इसका असर इस बात पर भी पड़ रहा है कि आप अपने-आप से कैसे बात कर रहे हैं। जब चीज़ें इतनी भारी लगती हैं, क्या आप खुद को ज़्यादा दोष देने लगते हैं या बोझ जैसा महसूस होता है?
6. stage=`clarification` topic=`focus` item=`phq_q7_concentration` scene=`None` closure=`True` touched=`2` resolved=`0` safety=`none`
   user: ध्यान बार-बार टूटता है, एक ही लाइन दोबारा पढ़नी पड़ती है और छोटे काम भी लंबे लगते हैं।
   assistant: लगता है इसकी वजह से काम या पढ़ाई पर टिके रहना मुश्किल हो रहा है। जब आप काम या पढ़ाई पर बैठते हैं, क्या ज़्यादा ऐसा होता है कि ध्यान बार-बार भटक जाता है, या एक ही बात पर लौटते रहते हैं लेकिन वह टिकती नहीं?
7. stage=`clarification` topic=`anxiety` item=`gad_q2_control_worry` scene=`worry_shape` closure=`True` touched=`2` resolved=`0` safety=`none`
   user: चिंता काम, पैसों और भविष्य के बीच घूमती रहती है।
   assistant: लगता है चिंता शुरू होने के बाद उसे रोकना आसान नहीं पड़ रहा। जब चिंता शुरू होती है, किस तरह ज़्यादा फिट बैठती है: अंदर-ही-अंदर घबराया-सा एहसास, एक ही विचार की लूप जो छूटती नहीं, या काम/भविष्य की कई चिंताएँ एक साथ जमा होना?
8. stage=`clarification` topic=`anxiety` item=`gad_q4_trouble_relaxing` scene=`worry_activation` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: ज़्यादा दिमाग को शांत करना मुश्किल होता है; शरीर वाला हिस्सा है लेकिन उतना बड़ा नहीं।
   assistant: और जब यह सबसे तेज़ होती है, तब क्या ज़्यादा सामने आता है: दिमाग को शांत करना मुश्किल होना, बेचैनी, चिड़चिड़ापन, या यह एहसास कि आगे कुछ गलत हो सकता है?
9. stage=`clarification` topic=`anxiety` item=`gad_q5_restlessness` scene=`worry_activation` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: कुछ शामों में बेचैनी और चिड़चिड़ापन दोनों बढ़ जाते हैं।
   assistant: जब यह बेचैनी आती है, क्या ज़्यादा ऐसा लगता है कि शरीर चैन से बैठ नहीं पा रहा, या दिमाग बेचैन रहता है चाहे आप शांत बैठे हों?
10. stage=`clarification` topic=`anxiety` item=`gad_q4_trouble_relaxing` scene=`worry_activation` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: खुद को नुकसान पहुंचाने का मन नहीं है, बस अभी तक का सार चाहिए।
   assistant: और जब यह सबसे तेज़ होती है, तब क्या ज़्यादा सामने आता है: दिमाग को शांत करना मुश्किल होना, बेचैनी, चिड़चिड़ापन, या यह एहसास कि आगे कुछ गलत हो सकता है?

## hinglish

- final stage: `summary`
- touched: `6/16`
- resolved: `0`
- safety: `none`
- totals: `PHQ9=7` `GAD7=5`

1. stage=`clarification` topic=`sleep` item=`phq_q3_sleep` scene=`None` closure=`False` touched=`2` resolved=`0` safety=`none`
   user: Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.
   assistant: Lag raha hai iska effect sleep par kaafi clearly aa raha hai. Jab sleep disturb hoti hai, kya zyada issue sone ki shuruat mein hota hai, raat mein baar baar uthne mein, ya bahut jaldi uth jaane mein?
2. stage=`clarification` topic=`anxiety` item=`gad_q2_control_worry` scene=`None` closure=`False` touched=`3` resolved=`0` safety=`none`
   user: Mostly 3 ya 4 baje aankh khul jaati hai aur phir work wali soch chalti rehti hai.
   assistant: Lag raha hai worry tab bhi active rehti hai jab bahar sab quiet ho. Jab worry start hoti hai, kya aap mind ko usse hata paate ho, ya rokne ki koshish ke baad bhi woh loop hoti rehti hai?
3. stage=`clarification` topic=`energy` item=`phq_q5_appetite` scene=`None` closure=`False` touched=`3` resolved=`0` safety=`none`
   user: Day chadhte chadhte aalas badh jata hai, appetite bhi down ho jaati hai aur lunch miss ho jata hai.
   assistant: Lag raha hai normal day pehle se zyada effort le raha hai. Kya appetite zyada kam hui hai, zyada badhi hai, ya meals skip ya delay hone ki wajah se zyada irregular ho gayi hai?
4. stage=`clarification` topic=`mood` item=`phq_q2_low_mood` scene=`None` closure=`False` touched=`4` resolved=`0` safety=`none`
   user: Jo cheezein pehle achhi lagti thi ab start karne se pehle hi mann hat jata hai.
   assistant: Lag raha hai emotional weight khud hi kaafi heavy ho gaya hai. Jab yeh feel hota hai, kya yeh zyada poore din ki sadness ya heaviness jaisa rehta hai, ya kuch specific times par waves mein aata hai?
5. stage=`clarification` topic=`self_view` item=`phq_q6_worthlessness` scene=`None` closure=`True` touched=`4` resolved=`0` safety=`none`
   user: Peeche reh jaun to main khud par kaafi harsh ho jata hoon aur burden jaisa feel hota hai.
   assistant: Lag raha hai iska effect aap apne aap se kaise baat karte ho us par bhi aa raha hai. Jab cheezein itni heavy lagti hain, kya aap khud ko zyada blame karte ho ya burden jaisa feel hota hai?
6. stage=`clarification` topic=`focus` item=`phq_q7_concentration` scene=`None` closure=`True` touched=`5` resolved=`0` safety=`none`
   user: Focus toot jata hai, same line dobara padhni padti hai, aur small tasks slow lagte hain.
   assistant: Lag raha hai tasks par tikna is wajah se mushkil ho raha hai. Jab aap work ya study par baithte ho, kya zyada aisa hota hai ki attention baar baar slip ho jata hai, ya same line par wapas aate rehte ho lekin woh stick nahi karti?
7. stage=`clarification` topic=`anxiety` item=`gad_q2_control_worry` scene=`worry_shape` closure=`True` touched=`5` resolved=`0` safety=`none`
   user: Worry work mistakes, paise, aur future ke beech jump karti rehti hai.
   assistant: Lag raha hai worry tab bhi active rehti hai jab bahar sab quiet ho. Jab worry start hoti hai, kaunsi shape zyada fit baithti hai: background mein keyed-up feeling, ek thought-loop jo chhootti nahi, ya work aur future ki kai worries saath mein pile hona?
8. stage=`clarification` topic=`anxiety` item=`gad_q4_trouble_relaxing` scene=`worry_activation` closure=`True` touched=`6` resolved=`0` safety=`none`
   user: Mind ko quiet karna tough hota hai; body side hai but smaller lagti hai.
   assistant: Aur jab yeh peak karti hai, tab kya zyada stand out karta hai: mind ko quiet karna tough hona, restlessness, irritability, ya yeh feel ki aage kuch galat ho sakta hai?
9. stage=`clarification` topic=`anxiety` item=`gad_q5_restlessness` scene=`worry_activation` closure=`True` touched=`6` resolved=`0` safety=`none`
   user: Kuch evenings mein restlessness aur irritability dono badh jaate hain.
   assistant: Jab yeh restlessness aati hai, kya zyada body chain se baith nahi paati, ya mind agitated rehta hai chahe aap still baithe ho?
10. stage=`summary` topic=`anxiety` item=`gad_q2_control_worry` scene=`None` closure=`False` touched=`6` resolved=`0` safety=`none`
   user: Khud ko hurt karne ka plan nahi hai, bas abhi ka working summary chahiye.
   assistant: Ab tak jo picture ban rahi hai, usme kaam start karne se pehle hi mann hatne lagta hai; sleep theek se settle nahi ho pa rahi hai; worry thoughts aur body tension dono ko saath kheench rahi hai. Agar ek cheez abhi bhi clarify karni ho, to next best jagah anxiety rahegi.
