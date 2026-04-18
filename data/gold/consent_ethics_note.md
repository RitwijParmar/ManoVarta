# Consent and Ethics Note

This project should not represent synthetic or convenience demo data as clinical gold data.

Before any real gold dataset is claimed, the team should ensure:

- participants know the interaction is for research or coursework screening support
- participants understand it is not therapy or emergency care
- audio recording consent is explicit
- transcripts and labels are stored under pseudonymous ids
- direct identifiers are removed from training/evaluation exports
- high-risk disclosures have a documented escalation path outside the model

If the team cannot collect a real clinical dataset, the strictest acceptable fallback is:

- a clearly documented role-play or volunteered pilot set
- explicit note that labels were assigned by a structured DSM/PHQ/GAD rubric
- double annotation and adjudication

That is still weaker than psychiatrist gold labels, but much stronger and more defensible than leaving the gold-label path undocumented.
