# ACL Paper Source

This folder keeps the final paper source bundle and figure inputs used for the project report.

## Canonical source files

- `ManoVarta_Final_Project_Report.tex`
- `ManoVarta_Final_Project_Report.bib`
- `acl.sty`
- `acl_natbib.bst`
- `figures/`
- `metrics_snapshot.json`

## Build note

Generated PDFs, DOCX exports, PPTX decks, temporary Overleaf bundles, and LaTeX build byproducts are intentionally not part of the clean source bundle.

## Compile

Use any standard ACL-compatible TeX environment:

```bash
pdflatex ManoVarta_Final_Project_Report.tex
bibtex ManoVarta_Final_Project_Report
pdflatex ManoVarta_Final_Project_Report.tex
pdflatex ManoVarta_Final_Project_Report.tex
```
