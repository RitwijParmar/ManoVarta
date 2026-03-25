# Seed Data Notes

These files are a small pilot set for local development, admin testing, and demo walkthroughs.

- `patient_profiles.json` includes six profile seeds with nuance tags such as disclosure style, somatic wording, code-mixing, and review-level safety cues.
- `conversations.json` includes annotated example conversations across English, Hindi, and Hinglish.
- `patient_profiles_extended.json` adds six harder profile seeds with minimization, contradiction, somatic anxiety, passive safety language, and richer Hinglish.
- `conversations_extended.json` adds aligned annotated conversations for the extended profile set.
- The records are synthetic and should not be described as clinical data.

The loader reads every matching `patient_profiles*.json` and `conversations*.json` file, so the seed cohort can grow without turning one file into a maintenance bottleneck.
The split is still intentionally small compared with a real dataset because the final project is expected to expand annotation coverage later rather than pretend it already has a large corpus.
