# Strict Compliance Repo Audit

- Generated: `2026-04-09`
- Scope: repo-wide audit after gold-data scaffolding, live redeploy, report regeneration, and bundle refresh
- Status: superseded by `reports/strict_compliance_repo_audit_20260410.md` after bilingual real-data imports.

## Already Done - Do Not Redo

These repo-side tasks are complete and should stay off the remaining-task list.

1. Gold-data scaffold exists under `data/gold/`.
   - bilingual folder structure is present
   - collection, annotation, ethics, and checklist docs are present
2. The plan is expanded to `30` sessions per language.
   - `60` total sessions are registered in `data/gold/session_registry.csv`
3. Starter transcript, label, and metadata files exist for all planned sessions.
   - `data/gold/transcripts/`
   - `data/gold/labels/`
   - `data/gold/metadata.csv`
4. Gold-data validation tooling exists and runs.
   - `tools/init_gold_dataset.py`
   - `tools/validate_gold_dataset.py`
5. Gold annotation packet generation exists and runs.
   - `tools/build_gold_annotation_packets.py`
   - packets are generated under `data/gold/packets/`
6. Adjudication/disagreement reporting exists and runs.
   - `tools/generate_gold_adjudication_report.py`
   - disagreement CSV is generated under `data/gold/adjudication/`
7. Registry sync and dashboard tooling exist and run.
   - `tools/sync_gold_registry_status.py`
   - `tools/generate_gold_progress_dashboard.py`
8. Deployment packaging is complete in-repo.
   - shipped bundle exists at `artifacts/manovarta_shipped_baseline_20260413.zip`
9. Voice transcript-before-submit is implemented in the patient UI.
10. Live runtime is aligned with the intended local/hybrid configuration.
   - provider is `local`
   - hybrid safety is enabled
   - local safety checkpoint is enabled

## Real Remaining Tasks

These are the true strict-compliance blockers that still remain after the repo-side work is done.

### 1. Replace placeholders with real bilingual gold data

The repository now has the full workflow, but the content is still placeholder content.

Current validator status:

- `audio_present = 0`
- `metadata_placeholders = 60`
- `transcript_placeholders = 60`
- `label_placeholders = 180`
- `fully_complete = 0`

This means the strict-compliance blocker is still:

- real English audio
- real Hindi audio
- real participant/profile metadata
- real transcripts
- real annotator A labels
- real annotator B labels
- real adjudicated labels

### 2. Gold-data reporting is honest, but evaluation is still seed-based

The assignment report now explicitly says disclosure efficiency is sourced from `seed conversations`, which is honest.
But that also means strict-compliance evaluation is still not grounded in the gold dataset yet.

The remaining task is:

- once real gold data exists, add gold-backed evaluation outputs and point the strict-compliance report to those results

### 3. Adjudication workflow is operational, but not yet exercised on real disagreements

The repo can now generate disagreement tracking, but all current label files are placeholders.

The remaining task is:

- run the annotator A / annotator B / adjudication flow on real sessions until disagreement outputs reflect real annotation differences instead of placeholder files

## Deduplicated Next Actions

If the goal is strict compliance, the next actions should now be:

1. Fill `data/gold/audio/` with real English and Hindi session audio.
2. Replace `data/gold/metadata.csv` placeholder rows with real participant/profile metadata.
3. Replace transcript stubs with real transcripts.
4. Replace starter label files with real annotator A, annotator B, and adjudicated labels.
5. Re-run:
   - `python tools/validate_gold_dataset.py`
   - `python tools/build_gold_annotation_packets.py`
   - `python tools/generate_gold_adjudication_report.py`
6. After placeholders reach zero, add gold-backed evaluation metrics to the assignment report.

## Final Read

The remaining work is now mostly human-data and annotation execution, not product engineering.
The repo is ready for a real bilingual gold-data collection and adjudication cycle, but it is not yet honestly allowed to claim full strict compliance.
