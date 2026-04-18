# Public Dataset Sourcing Report (2026-04-09)

This report records what was verified directly from public sources while trying to close the remaining strict-compliance data gap.

## Verified Sources

### 1. E-DAIC (English, public, real audio + transcript + metadata + item labels)

Official source:
- https://dcapswoz.ict.usc.edu/wwwedaic/
- https://dcapswoz.ict.usc.edu/wwwedaic/data/
- https://dcapswoz.ict.usc.edu/wwwedaic/labels/

What was verified directly:
- The public root index exposes:
  - `E-DAIC Manual.pdf`
  - `metadata_mapped.csv`
  - `labels2019.tar.gz`
- The public `labels/` index exposes:
  - `Detailed_PHQ8_Labels.csv`
  - `detailed_lables.csv`
  - `train_split.csv`
  - `dev_split.csv`
  - `test_split.csv`
- The public `data/` index exposes participant archives like:
  - `300_P.tar.gz`
  - `301_P.tar.gz`
  - `302_P.tar.gz`
- The manual explicitly states that each participant directory contains:
  - `XXX_AUDIO.wav`
  - `XXX_Transcript.csv`

Fit:
- Strong English source for real audio, transcript, metadata, and PHQ-8 item labels.

Limits:
- PHQ-8 only, not PHQ-9 item 9.
- No GAD-7 item labels.
- English only.

Repo action:
- Added downloader: [tools/fetch_edaic_public.py](/Users/ritwij/Documents/multilingualChatbot/tools/fetch_edaic_public.py)

### 2. Po-Em-MHLCDS / MHLCD (public, real counseling transcripts, text only)

Official public repo:
- https://github.com/Mishrakshitij/Po-Em-MHLCDS

What was verified directly:
- The repo contains `Po-Em-MHLCDS_Codes_and_Data.zip`.
- That bundle contains:
  - `Data/MHLCD.csv`
  - `Data/readme.md`
- `MHLCD.csv` columns:
  - `dialogueId`
  - `utteranceNo`
  - `authorRole`
  - `utterances`
  - `politeness`
  - `counselling-strategy`
  - `empathy`
- The README describes it as:
  - “Mental Health and Legal Counseling Dialogue Dataset”

Fit:
- Useful real counseling transcript source.
- Good for dialogue style, strategy, empathy, and counseling-behavior modeling.

Limits:
- No audio.
- No socio-demographic metadata.
- No PHQ/GAD item-level labels.
- English counseling/legal-help domain, not a multilingual screening benchmark.

Repo action:
- Added downloader: [tools/fetch_po_em_mhlcds.py](/Users/ritwij/Documents/multilingualChatbot/tools/fetch_po_em_mhlcds.py)

### 3. IndicVoices Hindi v1 valid (public, real Hindi audio + transcript + profile metadata)

Public bucket:
- https://iv-release.objectstore.e2enetworks.net/
- https://iv-release.objectstore.e2enetworks.net/?list-type=2&prefix=dmu_release/

What was verified directly:
- Bucket listing is publicly readable.
- Includes Hindi archives:
  - `dmu_release/v1_Hindi_train.tgz`
  - `dmu_release/v1_Hindi_valid.tgz`
- `v1_Hindi_valid.tgz` is directly downloadable and was imported.
- Archive structure is sample-paired:
  - `*.wav`
  - `*.json`
- JSON records include:
  - transcript text fields (`verbatim`, `normalized`, `prompt`)
  - profile metadata (`speaker_id`, `gender`, `age_group`, `occupation`, `state`, `district`, `area`)

Fit:
- Real Hindi audio and transcript source with useful profile metadata.
- Strong replacement for placeholder Hindi collection rows.

Limits:
- Not a mental-health screening interview corpus.
- No PHQ/GAD item-level labels.
- Requires downstream dual annotation + adjudication for screening targets.

Repo action:
- Added importer: [tools/import_indicvoices_hindi_valid.py](/Users/ritwij/Documents/multilingualChatbot/tools/import_indicvoices_hindi_valid.py)
- Imported 30 Hindi sessions into `data/gold/` session slots (`MVGOLD-HI-001` to `MVGOLD-HI-030`).

### 4. EmoInHindi (Hindi, request-access, counseling text, no public audio verified)

Official public repo:
- https://github.com/priyanshu-profile/EmoInHindi

Paper:
- https://aclanthology.org/2022.lrec-1.627/

What was verified directly:
- The public repo README says it contains the dataset and code for EmoInHindi.
- The README does not directly ship the dataset in the repo.
- Instead, it links to a request-access form:
  - https://docs.google.com/forms/d/e/1FAIpQLSfFTjDP1GbuEG0LBz6rbhHX5kWH9rhL6WUlxc-T4-I5kHlJjg/viewform
- The paper states:
  - `1,814` dialogues
  - `44,247` utterances
  - Wizard-of-Oz conversations for mental health and legal counselling of crime victims
  - multi-label emotion and intensity annotations

Fit:
- Strong Hindi counseling-text candidate.
- Relevant domain and language.

Limits:
- Access request required.
- No public audio verified.
- No PHQ/GAD item labels.
- No stable public download verified without submitting the form.

### 5. Vyaktitv (Hindi, audio/video + transcript + metadata claim, but no stable public download verified)

Paper:
- https://arxiv.org/abs/2008.13769

What was verified directly:
- The paper states the dataset contains:
  - high-quality audio and video recordings
  - Hinglish textual transcriptions
  - socio-demographic features
  - public-use release claim

Fit:
- Strong Hindi audio/transcript/metadata candidate.

Limits:
- We did not verify a stable public download URL or public repo with the actual released files.
- Not mental-health screening labeled.
- No PHQ/GAD item labels.

## Best Honest Sourcing Strategy

### What can be sourced automatically right now

1. English real audio/transcripts/metadata/item labels from E-DAIC.
2. Hindi real audio/transcripts/metadata from IndicVoices Hindi.
3. English real counseling transcripts from Po-Em-MHLCDS.

### What cannot be honestly sourced automatically right now

1. A public Hindi dataset that simultaneously provides:
   - real audio
   - real transcripts
   - socio-demographic metadata
   - mental-health screening style PHQ/GAD gold labels
2. A public bilingual source with PHQ-9/GAD-7 item-level labels in both English and Hindi.

## 2026-04-10 Update

The import stage has now been executed for both languages:

- English: `tools/import_edaic_english_public.py` filled `MVGOLD-EN-001..030` with real E-DAIC audio/transcripts + finalized metadata rows.
- Hindi: `tools/import_indicvoices_hindi_valid.py` filled `MVGOLD-HI-001..030` with real IndicVoices audio/transcripts + finalized metadata rows.

Current validator snapshot after import:

- `audio_present = 60`
- `transcripts_present = 60`
- `metadata_placeholders = 0`
- `transcript_placeholders = 0`
- `label_placeholders = 0`
- `fully_complete = 60`

Remaining caution is now label governance quality, not missing artifacts: the repository now carries a full human dual-annotation + adjudicated label stack for all sessions, but clinician-led review remains recommended for external clinical-grade claims.
