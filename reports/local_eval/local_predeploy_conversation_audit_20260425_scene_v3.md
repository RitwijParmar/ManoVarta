# Local Predeploy Conversation Audit (2026-04-25)

## en
- Final stage: `summary`
- Target topic/item: `anxiety` / `gad_q6_irritability`
- Target scene: `None`
- Closure mode: `False`
- Touched/resolved: `13` / `11`
- Completion ratio: `0.69`
- Totals: `PHQ9=14`, `GAD7=10`
- Safety: `none`

### Turn 1
- User: I've been dragging myself through the day and sleep has been broken for the last couple of weeks.
- Assistant: It sounds like sleep is getting hit in a real way. When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?
- Stage/item: `clarification` / `phq_q3_sleep`
- Scene: `None` | closure `False`
- Coverage: touched `2`, resolved `0`, PHQ9 `4`, GAD7 `0`, safety `none`

### Turn 2
- User: Most nights I wake around 3 or 4 and then lie there replaying work stuff.
- Assistant: That helps place the sleep pattern. Roughly how many nights a week has it been happening like that?
- Stage/item: `clarification` / `phq_q3_sleep`
- Scene: `None` | closure `False`
- Coverage: touched `3`, resolved `2`, PHQ9 `4`, GAD7 `3`, safety `none`

### Turn 3
- User: By the afternoon my body feels heavy, my appetite is off, and lunch just slips.
- Assistant: It sounds like the emotional weight itself has been hard to carry. When this hits, does it sit more like sadness or heaviness through the day, or does it come in waves around certain times?
- Stage/item: `clarification` / `phq_q2_low_mood`
- Scene: `None` | closure `False`
- Coverage: touched `4`, resolved `4`, PHQ9 `6`, GAD7 `3`, safety `none`

### Turn 4
- User: I still get through things but everything feels flat underneath before I even start.
- Assistant: On days when you keep going through the motions, does it mostly slow you down and make basic things feel heavier, or can you function on the outside while still feeling emotionally flat underneath?
- Stage/item: `clarification` / `phq_q2_low_mood`
- Scene: `None` | closure `False`
- Coverage: touched `5`, resolved `5`, PHQ9 `8`, GAD7 `3`, safety `none`

### Turn 5
- User: When I fall behind I get pretty harsh on myself and feel like I am letting people down.
- Assistant: It sounds like the emotional weight itself has been hard to carry. When the harder days hit, what lands most in the foreground: feeling low, losing interest before you even start, or getting harsher on yourself?
- Stage/item: `clarification` / `phq_q2_low_mood`
- Scene: `mood_selfview` | closure `True`
- Coverage: touched `6`, resolved `6`, PHQ9 `11`, GAD7 `3`, safety `none`

### Turn 6
- User: Focus breaks a lot, so I reread the same line and small tasks take forever.
- Assistant: After the rough sleep or low-energy days, what slips first for you: getting going, appetite, staying with one task, or your pace feeling noticeably slowed or keyed up?
- Stage/item: `clarification` / `phq_q8_psychomotor`
- Scene: `sleep_functioning` | closure `True`
- Coverage: touched `8`, resolved `7`, PHQ9 `14`, GAD7 `3`, safety `none`

### Turn 7
- User: The worry jumps between work mistakes, money, and what that means for my future.
- Assistant: It sounds like the worry is staying active even when things are quiet. And when it peaks, what stands out more: hard to quiet the mind, restlessness, irritability, or a sense that something may go wrong next?
- Stage/item: `clarification` / `gad_q4_trouble_relaxing`
- Scene: `worry_activation` | closure `True`
- Coverage: touched `9`, resolved `8`, PHQ9 `14`, GAD7 `5`, safety `none`

### Turn 8
- User: Mostly it is hard to quiet my mind; the body tension is there but smaller.
- Assistant: When the anxiety peaks, does it feel more like something specific might go wrong, that you may get bad news, or that things could spiral out of control?
- Stage/item: `clarification` / `gad_q7_afraid`
- Scene: `worry_activation` | closure `True`
- Coverage: touched `10`, resolved `9`, PHQ9 `14`, GAD7 `7`, safety `none`

### Turn 9
- User: Some evenings I feel restless and snappy even though I know nobody is doing anything wrong.
- Assistant: That timing helps. At that point, is the fear more about something specific going wrong, bad news, or things spiraling out of control?
- Stage/item: `clarification` / `gad_q7_afraid`
- Scene: `None` | closure `True`
- Coverage: touched `12`, resolved `10`, PHQ9 `14`, GAD7 `10`, safety `none`

### Turn 10
- User: I do not want to hurt myself or die, I just want a working summary.
- Assistant: Here is the working picture so far: interest tends to drop before getting started; sleep looks disrupted rather than settled; the harder part looks mental rather than bodily: the mind keeps running even when the body is not the main issue. If one detail still matters to clarify, anxiety is the next best place to tighten.
- Stage/item: `summary` / `gad_q6_irritability`
- Scene: `None` | closure `False`
- Coverage: touched `13`, resolved `11`, PHQ9 `14`, GAD7 `10`, safety `none`

## hi
- Final stage: `summary`
- Target topic/item: `energy` / `phq_q4_fatigue`
- Target scene: `None`
- Closure mode: `False`
- Touched/resolved: `11` / `9`
- Completion ratio: `0.56`
- Totals: `PHQ9=14`, `GAD7=10`
- Safety: `none`

### Turn 1
- User: पिछले दो हफ्तों से रात में नींद टूटती रहती है और सुबह शुरू होने में बहुत समय लगता है।
- Assistant: लगता है इसका असर नींद पर साफ़ पड़ रहा है। जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?
- Stage/item: `clarification` / `phq_q3_sleep`
- Scene: `None` | closure `False`
- Coverage: touched `2`, resolved `0`, PHQ9 `4`, GAD7 `0`, safety `none`

### Turn 2
- User: अक्सर रात के तीन-चार बजे उठ जाता हूँ और फिर काम की बातें दिमाग में चलती रहती हैं।
- Assistant: लगता है चिंता तब भी सक्रिय रहती है जब बाहर सब शांत हो। जब चिंता चलती रहती है, क्या यह ज़्यादा काम, परिवार, पैसों या भविष्य जैसी कई बातों में फैल जाती है, या आम तौर पर किसी एक मुख्य बात पर अटकती है?
- Stage/item: `clarification` / `gad_q3_excessive_worry`
- Scene: `None` | closure `False`
- Coverage: touched `3`, resolved `2`, PHQ9 `4`, GAD7 `3`, safety `none`

### Turn 3
- User: दिन चढ़ते-चढ़ते आलस बढ़ जाता है, भूख भी कम हो जाती है और कई बार खाना छूट जाता है।
- Assistant: लगता है रोज़ का दिन पहले से ज़्यादा मेहनत माँग रहा है। जब थकान या ऊर्जा की कमी बढ़ती है, क्या ज़्यादा ऐसा लगता है कि शरीर भारी पड़ रहा है, दिमाग शुरू होने में धीमा है, या दोनों?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `None` | closure `False`
- Coverage: touched `4`, resolved `3`, PHQ9 `6`, GAD7 `3`, safety `none`

### Turn 4
- User: जो चीज़ें पहले अच्छी लगती थीं, अब शुरू करने से पहले ही मन हट जाता है और अंदर से सब फीका लगता है।
- Assistant: लगता है जो चीज़ें पहले मायने रखती थीं, उनमें अभी मन कम लग रहा है। जब आप उन कामों की तरफ़ जाते हैं जो पहले अच्छे लगते थे, क्या शुरू करने से पहले ही मन हट जाता है, या आप कर लेते हैं लेकिन उनसे बहुत कम महसूस होता है?
- Stage/item: `clarification` / `phq_q1_anhedonia`
- Scene: `None` | closure `False`
- Coverage: touched `4`, resolved `3`, PHQ9 `6`, GAD7 `3`, safety `none`

### Turn 5
- User: पीछे रह जाऊँ तो मैं खुद को बहुत कोसता हूँ और लगता है मैं सब पर बोझ बन रहा हूँ।
- Assistant: जब आप उन कामों की तरफ़ जाते हैं जो पहले अच्छे लगते थे, क्या शुरू करने से पहले ही मन हट जाता है, या आप कर लेते हैं लेकिन उनसे बहुत कम महसूस होता है?
- Stage/item: `clarification` / `phq_q1_anhedonia`
- Scene: `None` | closure `True`
- Coverage: touched `5`, resolved `4`, PHQ9 `9`, GAD7 `3`, safety `none`

### Turn 6
- User: ध्यान बार-बार टूटता है, एक ही लाइन दोबारा पढ़नी पड़ती है और छोटे काम भी लंबे लगते हैं।
- Assistant: जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?
- Stage/item: `clarification` / `phq_q2_low_mood`
- Scene: `None` | closure `True`
- Coverage: touched `6`, resolved `5`, PHQ9 `11`, GAD7 `3`, safety `none`

### Turn 7
- User: चिंता काम, पैसों और भविष्य के बीच घूमती रहती है।
- Assistant: लगता है भावनात्मक बोझ अपने-आप में ही काफ़ी भारी हो गया है। जब यह बना रहता है, क्या यह ज़्यादा दिन भर का लगातार भारी मन लगता है, या भावनात्मक सुन्नपन जैसा जो आता-जाता रहता है?
- Stage/item: `clarification` / `phq_q2_low_mood`
- Scene: `None` | closure `True`
- Coverage: touched `7`, resolved `6`, PHQ9 `11`, GAD7 `5`, safety `none`

### Turn 8
- User: ज़्यादा दिमाग को शांत करना मुश्किल होता है; शरीर वाला हिस्सा है लेकिन उतना बड़ा नहीं।
- Assistant: लगता है खुद को शांत करना जितना होना चाहिए, उससे ज़्यादा मुश्किल हो रहा है। खराब नींद या थके हुए दिनों के बाद सबसे पहले क्या प्रभावित होता है: शुरू होने की ताकत, भूख, एक काम पर टिकना, या चाल-ढाल/रफ्तार का धीमा या बेचैन हो जाना?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `sleep_functioning` | closure `True`
- Coverage: touched `8`, resolved `7`, PHQ9 `11`, GAD7 `7`, safety `none`

### Turn 9
- User: कुछ शामों में बेचैनी और चिड़चिड़ापन दोनों बढ़ जाते हैं।
- Assistant: यह समय-सूचना मददगार है। उस समय के आसपास, क्या ज़्यादा शरीर भारी लगता है, दिमाग शुरू होने में धीमा पड़ता है, या दोनों साथ में?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `None` | closure `True`
- Coverage: touched `10`, resolved `8`, PHQ9 `11`, GAD7 `10`, safety `none`

### Turn 10
- User: खुद को नुकसान पहुंचाने का मन नहीं है, बस अभी तक का सार चाहिए।
- Assistant: अभी तक जो तस्वीर बन रही है, उसमें नींद ठीक से स्थिर नहीं हो पा रही है; ऊर्जा और ध्यान दोनों सामान्य से धीमे लग रहे हैं; मुश्किल हिस्सा शरीर से ज़्यादा मानसिक लग रहा है: जब शरीर मुख्य समस्या नहीं है तब भी दिमाग चलता रहता है। अगर एक बात अभी भी साफ़ करनी हो, तो अगला सबसे उपयोगी हिस्सा चिंता रहेगा।
- Stage/item: `summary` / `phq_q4_fatigue`
- Scene: `None` | closure `False`
- Coverage: touched `11`, resolved `9`, PHQ9 `14`, GAD7 `10`, safety `none`

## hinglish
- Final stage: `summary`
- Target topic/item: `anxiety` / `gad_q6_irritability`
- Target scene: `None`
- Closure mode: `False`
- Touched/resolved: `13` / `10`
- Completion ratio: `0.62`
- Totals: `PHQ9=16`, `GAD7=10`
- Safety: `none`

### Turn 1
- User: Pichhle do hafte se sleep break hoti rehti hai aur morning mein start lena heavy lagta hai.
- Assistant: Lag raha hai iska effect sleep par kaafi clearly aa raha hai. Jab sleep disturb hoti hai, kya zyada issue sone ki shuruat mein hota hai, raat mein baar baar uthne mein, ya bahut jaldi uth jaane mein?
- Stage/item: `clarification` / `phq_q3_sleep`
- Scene: `None` | closure `False`
- Coverage: touched `2`, resolved `0`, PHQ9 `3`, GAD7 `0`, safety `none`

### Turn 2
- User: Most nights 3 ya 4 baje aankh khul jaati hai aur phir work wali soch chalti rehti hai.
- Assistant: Isse sleep pattern thoda clearer ho raha hai. Roughly week mein kitni raaton mein aisa hota hai?
- Stage/item: `clarification` / `phq_q3_sleep`
- Scene: `None` | closure `False`
- Coverage: touched `3`, resolved `2`, PHQ9 `3`, GAD7 `3`, safety `none`

### Turn 3
- User: Day chadhte chadhte aalas badh jata hai, appetite bhi down ho jaati hai aur lunch miss ho jata hai.
- Assistant: Lag raha hai normal day pehle se zyada effort le raha hai. Jab low energy build hoti hai, kya zyada body heavy lagti hai, mind ko start hone mein time lagta hai, ya dono?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `None` | closure `False`
- Coverage: touched `4`, resolved `3`, PHQ9 `5`, GAD7 `3`, safety `none`

### Turn 4
- User: Jo cheezein pehle achhi lagti thi ab start karne se pehle hi mann hat jata hai aur sab flat feel hota hai.
- Assistant: Jab low energy build hoti hai, kya zyada body heavy lagti hai, mind ko start hone mein time lagta hai, ya dono?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `None` | closure `False`
- Coverage: touched `5`, resolved `4`, PHQ9 `7`, GAD7 `3`, safety `none`

### Turn 5
- User: Peeche reh jaun to main khud par kaafi harsh ho jata hoon aur burden jaisa feel hota hai.
- Assistant: Lag raha hai emotional weight khud hi kaafi heavy ho gaya hai. Rough sleep ya low-energy days ke baad sabse pehle kya slip karta hai: start lene ki energy, appetite, ek task par tikna, ya pace ka noticeably slow ya keyed up ho jana?
- Stage/item: `clarification` / `phq_q7_concentration`
- Scene: `sleep_functioning` | closure `True`
- Coverage: touched `6`, resolved `5`, PHQ9 `10`, GAD7 `3`, safety `none`

### Turn 6
- User: Focus toot jata hai, same line dobara padhni padti hai, aur small tasks slow lagte hain.
- Assistant: Lag raha hai normal day pehle se zyada effort le raha hai. Jab low energy build hoti hai, kya zyada body heavy lagti hai, mind ko start hone mein time lagta hai, ya dono?
- Stage/item: `clarification` / `phq_q4_fatigue`
- Scene: `None` | closure `True`
- Coverage: touched `8`, resolved `6`, PHQ9 `13`, GAD7 `3`, safety `none`

### Turn 7
- User: Worry work mistakes, paise, aur future ke beech jump karti rehti hai.
- Assistant: Lag raha hai worry tab bhi active rehti hai jab bahar sab quiet ho. Aur jab yeh peak karti hai, tab kya zyada stand out karta hai: mind ko quiet karna tough hona, restlessness, irritability, ya yeh feel ki aage kuch galat ho sakta hai?
- Stage/item: `clarification` / `gad_q4_trouble_relaxing`
- Scene: `worry_activation` | closure `True`
- Coverage: touched `9`, resolved `7`, PHQ9 `13`, GAD7 `5`, safety `none`

### Turn 8
- User: Mind ko quiet karna tough hota hai; body tension hai but smaller lagti hai.
- Assistant: Jab anxiety peak karti hai, kya zyada lagta hai ki kuch specific galat ho sakta hai, koi bad news mil sakti hai, ya cheezein control se bahar ja sakti hain?
- Stage/item: `clarification` / `gad_q7_afraid`
- Scene: `worry_activation` | closure `True`
- Coverage: touched `10`, resolved `8`, PHQ9 `13`, GAD7 `7`, safety `none`

### Turn 9
- User: Kuch evenings mein restlessness aur irritability dono badh jaate hain.
- Assistant: Yeh timing helpful hai. Us waqt, kya fear zyada kisi specific problem ka hota hai, bad news ka, ya cheezon ke control se bahar jaane ka?
- Stage/item: `clarification` / `gad_q7_afraid`
- Scene: `None` | closure `True`
- Coverage: touched `12`, resolved `9`, PHQ9 `13`, GAD7 `10`, safety `none`

### Turn 10
- User: Khud ko hurt karne ka plan nahi hai, bas abhi ka working summary chahiye.
- Assistant: Ab tak jo picture ban rahi hai, usme kaam start karne se pehle hi mann hatne lagta hai; sleep theek se settle nahi ho pa rahi hai; harder part body se zyada mental lag raha hai: body main issue na ho tab bhi mind chalta rehta hai. Agar ek cheez abhi bhi clarify karni ho, to next best jagah anxiety rahegi.
- Stage/item: `summary` / `gad_q6_irritability`
- Scene: `None` | closure `False`
- Coverage: touched `13`, resolved `10`, PHQ9 `16`, GAD7 `10`, safety `none`
