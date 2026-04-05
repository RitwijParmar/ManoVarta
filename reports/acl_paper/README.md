# ACL Paper Bundle

This folder contains the final ACL-style report source for the ManoVarta project.

## Files

- `project2_acl_report.tex`: main paper source
- `project2_acl_report.bib`: bibliography
- `acl.sty`, `acl_natbib.bst`: official ACL style assets fetched from the public ACL style repository
- `figures/`: generated charts used in the paper
- `metrics_snapshot.json`: consolidated metric snapshot used to generate the figures

## Regenerating Figures

From the project root:

```bash
python3 tools/generate_acl_report_figures.py
```

## Compiling the Paper

This workspace does not currently have a LaTeX compiler installed, so the report was written as a compile-ready source bundle rather than a locally rendered PDF.

Compile in Overleaf or any TeX environment with:

```bash
pdflatex project2_acl_report.tex
bibtex project2_acl_report
pdflatex project2_acl_report.tex
pdflatex project2_acl_report.tex
```

## Notes

- The DAIC continuation row in the paper comes from a logged Colab experiment (`v2run3`) captured during project execution. Its summary was discussed and preserved in the generated `metrics_snapshot.json`, but it was not stored as a standalone repo JSON report.
- Gemma 3 remains cited as a planned baseline only. No final reproducible Gemma result was archived, so the paper intentionally does not fabricate Gemma metrics.
