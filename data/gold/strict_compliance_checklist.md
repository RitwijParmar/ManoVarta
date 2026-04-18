# Strict Compliance Checklist

Use this checklist before claiming full assignment compliance.

## Data

- [ ] `English` gold sessions exist
- [ ] `Hindi` gold sessions exist
- [ ] every gold session has an audio file
- [ ] every gold session has a transcript file
- [ ] every gold session has profile metadata

## Labels

- [ ] every gold session has item-level `PHQ-9` labels
- [ ] every gold session has item-level `GAD-7` labels
- [ ] every gold session has a safety label
- [ ] every non-zero item has evidence attached
- [ ] every session has two independent annotations
- [ ] every disagreement has adjudication recorded

## Reporting

- [ ] final report points to `data/gold/` instead of synthetic seed data
- [ ] DAIC is described only as auxiliary English supervision
- [ ] limitations clearly state what is pilot vs production-strength
- [ ] evaluation explicitly references the gold set

## Packaging

- [ ] shipped bundle exists at the documented path
- [ ] deployment status can be changed from `partial` to `complete`
- [ ] live URL, Docker assets, and bundle documentation all agree

## Voice

- [ ] voice mode is documented against the bilingual gold audio set
- [ ] transcript-before-submit flow is either implemented or clearly noted as optional

## Final bar

Do not call the project `100% compliant` until every box above is checked.
