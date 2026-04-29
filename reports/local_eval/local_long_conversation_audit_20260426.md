# Local Long Conversation Audit

## english_non_anxiety
- session_id: `mv-bd78d7d38b`
- exact assistant repeats: `0`
- final topic/item/scene: `focus` / `phq_q7_concentration` / `None`
- final coverage touched/resolved: `3` / `3`
- final safety: `none`
1. U: I have not been feeling like myself lately.
   A: It sounds like things that usually matter to you are feeling flatter right now. When you try to do things you usually care about, does the interest drop before you start, or do you go through with them but feel very little from them?
   plan: mood / phq_q1_anhedonia / None / open_question
2. U: Sleep has been taking forever and I wake up tired.
   A: It sounds like the day is taking more effort than it used to. When the energy drops, is it more like your body feels heavy, your mind feels slow to get going, or both?
   plan: energy / phq_q4_fatigue / None / symptom_probe
3. U: I can still do work, but it feels flat underneath.
   A: It sounds like the emotional weight itself has been hard to carry. On most days, has it felt more like low mood itself, or more like losing interest in things you usually enjoy?
   plan: mood / None / None / open_question
4. U: It feels more like low energy than worry.
   A: It sounds like the day is taking more effort than it used to. Is it more like low energy through the day, changes in appetite, or both?
   plan: energy / phq_q4_fatigue / None / symptom_probe
5. U: Meals get irregular too because I keep delaying them.
   A: After the rough sleep or low-energy days, what slips first for you: getting going, appetite, staying with one task, or your pace feeling noticeably slowed or keyed up?
   plan: energy / phq_q5_appetite / sleep_functioning / symptom_probe
6. U: Focus slips and I end up rereading the same paragraph.
   A: It sounds like this is getting in the way of staying with tasks. When you try to work or study, is it more that your attention slips away, or that you keep coming back to the same line and it still does not stick?
   plan: focus / phq_q7_concentration / None / symptom_probe
7. U: Then I get hard on myself because even simple things feel harder than they should.
   A: When you try to study or work, is it more that your focus keeps breaking, or that you keep rereading or rechecking because things do not stick?
   plan: focus / phq_q7_concentration / None / symptom_probe
8. U: Can you summarize what you are seeing so far?
   A: Here is the working picture so far: interest tends to drop before getting started; the heaviness seems to stay through much of the day; worry still looks like an active part of the picture. If one detail still matters to clarify, self-view is the next best place to tighten.
   plan: focus / phq_q7_concentration / None / summarize

## english_anxiety
- session_id: `mv-eaaf87b1af`
- exact assistant repeats: `0`
- final topic/item/scene: `anxiety` / `gad_q7_afraid` / `worry_activation`
- final coverage touched/resolved: `1` / `1`
- final safety: `none`
1. U: My mind keeps looping about work and the future late at night.
   A: It sounds like sleep is getting hit in a real way. When sleep gets disrupted, is it mostly hard to fall asleep, waking during the night, or waking too early?
   plan: sleep / phq_q3_sleep / None / clarify
2. U: Even when I try to stop it, it keeps running.
   A: It sounds like the worry is staying active even when things are quiet. When the worry keeps running, does it spread across things like work, family, money, or the future, or does it usually get stuck on one main issue?
   plan: anxiety / gad_q3_excessive_worry / None / open_question
3. U: Then my chest and jaw stay tight too.
   A: When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?
   plan: anxiety / gad_q4_trouble_relaxing / None / open_question
4. U: It spreads from work into money and family stuff as well.
   A: It sounds like the worry is staying active even when things are quiet. Does this feel more like constant worry in your mind, tension in your body, or both at the same time?
   plan: anxiety / gad_q1_nervous / None / open_question
5. U: The harder part is still quieting my mind.
   A: It sounds like both mind and body can get pulled in here. When this builds up, does it settle once the moment passes, or does the tension stay stuck for a long time afterward?
   plan: anxiety / gad_q4_trouble_relaxing / None / open_question
6. U: If you have enough, please summarize the pattern.
   A: It sounds like the worry is staying active even when things are quiet. And when it peaks, what stands out more: hard to quiet the mind, restlessness, irritability, or a sense that something may go wrong next?
   plan: anxiety / gad_q7_afraid / worry_activation / open_question

## hindi_mixed
- session_id: `mv-8a6f5a66d7`
- exact assistant repeats: `0`
- final topic/item/scene: `energy` / `phq_q5_appetite` / `None`
- final coverage touched/resolved: `3` / `3`
- final safety: `none`
1. U: नींद का पैटर्न बदल गया है, नींद काफी देर से आती है और काफी कम समय के लिए।
   A: लगता है इसका असर नींद पर साफ़ पड़ रहा है। जब नींद बिगड़ती है, क्या ज़्यादा दिक्कत सोने की शुरुआत में होती है, रात में बार-बार उठने में, या बहुत जल्दी उठ जाने में?
   plan: sleep / phq_q3_sleep / None / clarify
2. U: यह कुछ दिनों से ऐसा ही है, नींद कम आती है और किसी काम में मन नहीं लगता।
   A: लगता है दिन अपने-आप में ही भारी लग रहे हैं। जब यह महसूस होता है, क्या यह ज़्यादा दिन भर की उदासी या भारीपन जैसा रहता है, या कुछ खास समय पर लहरों में आता है?
   plan: mood / phq_q2_low_mood / None / clarify
3. U: काम या पढ़ाई पर ध्यान भी जल्दी टूट जाता है।
   A: लगता है इसकी वजह से काम या पढ़ाई पर टिके रहना मुश्किल हो रहा है। जब आप काम या पढ़ाई पर बैठते हैं, क्या ज़्यादा ऐसा होता है कि ध्यान बार-बार भटक जाता है, या एक ही बात पर लौटते रहते हैं लेकिन वह टिकती नहीं?
   plan: focus / phq_q7_concentration / None / symptom_probe
4. U: मन पहले से ही हट जाता है, कोई काम करने की इच्छा नहीं होती।
   A: लगता है इसका असर इस पर भी पड़ रहा है कि आप अपने बारे में क्या महसूस कर रहे हैं। जब दिन ज़्यादा भारी होता है, सबसे आगे क्या महसूस होता है: उदासी, शुरू करने से पहले ही मन हट जाना, या अपने-आप पर ज़्यादा कठोर हो जाना?
   plan: mood / phq_q6_worthlessness / mood_selfview / clarify
5. U: भूख भी कभी कम हो जाती है और दिन भारी लगता है।
   A: लगता है रोज़ का दिन पहले से ज़्यादा मेहनत माँग रहा है। क्या भूख ज़्यादा कम हुई है, ज़्यादा बढ़ी है, या बात ज़्यादा अनियमित खाने की है क्योंकि खाना छूट या देर से हो रहा है?
   plan: energy / phq_q5_appetite / None / symptom_probe
6. U: मैं वर्तमान देखता हूं तो उदासी आती है और अपने ऊपर भी निराशा होती है।
   A: खराब नींद या थके हुए दिनों के बाद सबसे पहले क्या प्रभावित होता है: शुरू होने की ताकत, भूख, एक काम पर टिकना, या चाल-ढाल/रफ्तार का धीमा या बेचैन हो जाना?
   plan: energy / phq_q4_fatigue / sleep_functioning / symptom_probe
7. U: चिंता उतनी नहीं है, ज़्यादा थकान और उदासी है।
   A: जब थकान या ऊर्जा की कमी बढ़ती है, क्या ज़्यादा ऐसा लगता है कि शरीर भारी पड़ रहा है, दिमाग शुरू होने में धीमा है, या दोनों?
   plan: energy / phq_q4_fatigue / None / symptom_probe
8. U: अब तक जो समझा है उसका summary बता दो।
   A: अभी तक जो तस्वीर बन रही है, उसमें काम शुरू करने से पहले ही मन हटने लगता है; भारीपन दिन के बड़े हिस्से में बना रहता है; चिंता अभी भी इस तस्वीर का सक्रिय हिस्सा लग रही है। अगर एक बात अभी भी साफ़ करनी हो, तो अगला सबसे उपयोगी हिस्सा मनोदशा रहेगा।
   plan: energy / phq_q5_appetite / None / summarize

## hinglish_mixed
- session_id: `mv-51389609ce`
- exact assistant repeats: `1`
- final topic/item/scene: `focus` / `phq_q7_concentration` / `None`
- final coverage touched/resolved: `1` / `0`
- final safety: `none`
1. U: Kal se body thodi down lag rahi hai aur sleep bhi theek nahi hai.
   A: Lag raha hai iska effect sleep par kaafi clearly aa raha hai. Jab sleep disturb hoti hai, kya zyada issue sone ki shuruat mein hota hai, raat mein baar baar uthne mein, ya bahut jaldi uth jaane mein?
   plan: sleep / phq_q3_sleep / None / open_question
2. U: Kaam start karne ka mann nahi karta aur energy low rehti hai.
   A: Lag raha hai normal day pehle se zyada effort le raha hai. Rough sleep ya low-energy days ke baad sabse pehle kya slip karta hai: start lene ki energy, appetite, ek task par tikna, ya pace ka noticeably slow ya keyed up ho jana?
   plan: energy / phq_q4_fatigue / sleep_functioning / symptom_probe
3. U: Worry utni nahi hai, bas thakan aur udasi zyada lagti hai.
   A: Jab low energy build hoti hai, kya zyada body heavy lagti hai, mind ko start hone mein time lagta hai, ya dono?
   plan: energy / phq_q4_fatigue / None / clarify
4. U: Meals bhi skip ho jaate hain aur kabhi focus same line par atak jata hai.
   A: Lag raha hai tasks par tikna is wajah se mushkil ho raha hai. Jab aap work ya study par baithte ho, kya zyada aisa hota hai ki attention baar baar slip ho jata hai, ya same line par wapas aate rehte ho lekin woh stick nahi karti? Ek recent example, ek timing detail, ya 0 se 10 ka quick estimate bhi enough hai.
   plan: focus / phq_q7_concentration / None / clarify
5. U: Kabhi lagta hai main normal se zyada khud ko judge kar raha hoon.
   A: Jab aap study ya work karte ho, kya zyada issue focus break hone ka hota hai, ya same cheez baar baar dekhni padti hai kyunki woh stick nahi karti?
   plan: focus / phq_q7_concentration / None / clarify
6. U: Subah start lene mein kaafi time lagta hai.
   A: Jab aap study ya work karte ho, kya zyada issue focus break hone ka hota hai, ya same cheez baar baar dekhni padti hai kyunki woh stick nahi karti?
   plan: focus / phq_q7_concentration / None / clarify
7. U: Conversation close mat karo, bas ab tak ki summary de do.
   A: Ab tak jo picture ban rahi hai, usme worry zyada racing thoughts se nahi balki physical tension ke form mein aa rahi hai; energy ya start-up effort bhi normal se lower lag raha hai. Agar ek cheez abhi bhi clarify karni ho, to next best jagah energy rahegi.
   plan: focus / phq_q7_concentration / None / summarize
