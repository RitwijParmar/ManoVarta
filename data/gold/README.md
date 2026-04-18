# Gold Data Compliance Pack

This folder is the strict-compliance scaffold for the assignment's data and annotation requirements.

It exists to separate:

- synthetic demo/dev data in `data/seed/`
- processed training/eval exports in `data/processed/`
- real bilingual gold data, labels, and adjudication assets in `data/gold/`

This folder does not claim that the gold dataset is already complete. It defines the structure and documentation needed to make that claim honestly.

## Target scope

The minimum strict-compliance target is:

- two languages: `English` and `Hindi`
- transcript and audio for every gold session
- basic patient profile metadata for every gold session
- item-level `PHQ-9` and `GAD-7` labels
- evidence-backed annotation by two annotators plus adjudication
- explicit safety label for each session

## Folder layout

- `audio/en/`
  - English audio files, one file per session
- `audio/hi/`
  - Hindi audio files, one file per session
- `transcripts/en/`
  - English transcript files
- `transcripts/hi/`
  - Hindi transcript files
- `labels/`
  - adjudicated item-level `PHQ-9` and `GAD-7` labels
- `adjudication/`
  - disagreement logs and adjudication records
- `metadata.csv`
  - one profile/collection row per session
- `packets/`
  - generated per-session annotator and adjudication packets
- `templates/`
  - CSV/JSON templates for metadata and labels

## Required artifacts per session

Each gold session should eventually have:

1. one audio file
2. one transcript file
3. one metadata row
4. two independent annotation files
5. one adjudicated label file

Recommended naming pattern:

- session id: `MVGOLD-EN-001`, `MVGOLD-HI-001`
- audio: `audio/en/MVGOLD-EN-001.wav`
- transcript: `transcripts/en/MVGOLD-EN-001.json`
- labels: `labels/MVGOLD-EN-001.adjudicated.json`

## Completion bar

This pack should only be called complete when all of the following are true:

- every session has both transcript and audio
- every session has bilingual metadata coverage where applicable
- every session has item-level labels for all `PHQ-9` and `GAD-7` items
- every session has evidence spans or evidence quotes recorded
- every session has adjudication completed
- the final report is updated to point to these assets instead of relying on synthetic seed data

## Working process

Initialize the plan:

```bash
python tools/init_gold_dataset.py
```

That creates:

- `data/gold/session_registry.csv`
- `data/gold/collection_plan.json`

Then check current completeness:

```bash
python tools/validate_gold_dataset.py
```

That writes:

- `reports/gold_dataset_status.json`
- `reports/gold_dataset_status.md`

Build session packets for annotators and adjudicators:

```bash
python tools/build_gold_annotation_packets.py
```

Sync `session_registry.csv` statuses from the actual files on disk:

```bash
python tools/sync_gold_registry_status.py
```

Generate disagreement tracking for adjudication:

```bash
python tools/generate_gold_adjudication_report.py
```

Generate a lightweight progress dashboard:

```bash
python tools/generate_gold_progress_dashboard.py
```

Recommended order:

1. collect the `5 English + 5 Hindi` pilot sessions
2. run annotation and adjudication on the pilot
3. use the validator report to fix process issues
4. only then collect the remaining sessions up to the `60`-session target (`30` per language)
