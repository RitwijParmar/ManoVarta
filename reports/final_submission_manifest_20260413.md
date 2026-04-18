# Final Submission Manifest (2026-04-13)

## Compliance Checklist

- ACL format source file present: `reports/acl_paper/project2_acl_report.tex`
- ACL PDF compiled: `reports/acl_paper/project2_acl_report.pdf`
- PDF pages: `7`
- References start page: `6`
- Main content pages (excluding references): `5`
- Gold dataset assignment status: complete (`30/30` English gold-core sessions plus `30/30` Hindi real-audio sessions with local DSM-aligned dual annotations + adjudication; Hindi remains a repurposed pilot rather than a source-matched clinical corpus)
- Full Aya continuation held-out eval completed: `48/48`, parse failures `0`
- Final shipped bundle built: `artifacts/manovarta_shipped_baseline_20260413.zip`

## Frozen Deliverables Directory

- `artifacts/final_submission_20260413/`
- Integrity file: `artifacts/final_submission_20260413/SHA256SUMS.txt`

## Key Metrics Snapshot

- Aya continuation full eval (`reports/aya_daic_continue_full_eval_20260413.json`)
  - Coverage: `0.943`
  - Exact match: `0.614`
  - Macro-F1: `0.297`
  - MAE: `0.409`
  - Safety precision/recall: `1.0 / 1.0`
  - Completed: `48/48`

- Final live runtime (`reports/live_runtime_eval_20260404.json`)
  - Coverage: `0.783`
  - Exact match: `0.639`
  - Macro-F1: `0.251`
  - Safety precision/recall: `1.0 / 1.0`
  - Parse failures: `0`
