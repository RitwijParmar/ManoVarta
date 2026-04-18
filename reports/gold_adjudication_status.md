# Gold Adjudication Status

- Total sessions: `60`
- Sessions with dual annotations present: `60`
- Sessions with open disagreements: `31`
- Sessions blocked by placeholders: `0`

## Agreement Metrics

- Metrics scope: `human_only_dual_annotations`
- Sessions used for metrics: `60`
- Sessions skipped for non-human labels: `0`
- Overall pair count: `960`
- Overall exact agreement: `0.9271`
- Overall Cohen's kappa: `0.7319`

### Item-wise Kappa

| Item | Pairs | Exact agreement | Cohen's kappa |
| --- | ---: | ---: | ---: |
| gad_q1_nervous | 60 | 1.0 | 1.0 |
| gad_q2_control_worry | 60 | 0.9833 | 0.8276 |
| gad_q3_excessive_worry | 60 | 0.9333 | 0.3143 |
| gad_q4_trouble_relaxing | 60 | 1.0 | 1.0 |
| gad_q5_restlessness | 60 | 1.0 | 1.0 |
| gad_q6_irritability | 60 | 0.8 | 0.6532 |
| gad_q7_afraid | 60 | 1.0 | 1.0 |
| phq_q1_anhedonia | 60 | 0.95 | 0.6429 |
| phq_q2_low_mood | 60 | 0.7667 | 0.6115 |
| phq_q3_sleep | 60 | 0.9 | 0.7218 |
| phq_q4_fatigue | 60 | 1.0 | 1.0 |
| phq_q5_appetite | 60 | 0.9833 | 0.869 |
| phq_q6_worthlessness | 60 | 0.7167 | 0.1727 |
| phq_q7_concentration | 60 | 0.85 | 0.4168 |
| phq_q8_psychomotor | 60 | 0.95 | 0.6814 |
| phq_q9_self_harm | 60 | 1.0 | 1.0 |

### Conflict Heatmap (Absolute Score Difference)

| Item | diff=0 | diff=1 | diff=2 | diff=3 |
| --- | ---: | ---: | ---: | ---: |
| gad_q1_nervous | 60 | 0 | 0 | 0 |
| gad_q2_control_worry | 59 | 1 | 0 | 0 |
| gad_q3_excessive_worry | 56 | 4 | 0 | 0 |
| gad_q4_trouble_relaxing | 60 | 0 | 0 | 0 |
| gad_q5_restlessness | 60 | 0 | 0 | 0 |
| gad_q6_irritability | 48 | 12 | 0 | 0 |
| gad_q7_afraid | 60 | 0 | 0 | 0 |
| phq_q1_anhedonia | 57 | 3 | 0 | 0 |
| phq_q2_low_mood | 46 | 10 | 4 | 0 |
| phq_q3_sleep | 54 | 3 | 2 | 1 |
| phq_q4_fatigue | 60 | 0 | 0 | 0 |
| phq_q5_appetite | 59 | 1 | 0 | 0 |
| phq_q6_worthlessness | 43 | 10 | 4 | 3 |
| phq_q7_concentration | 51 | 8 | 1 | 0 |
| phq_q8_psychomotor | 57 | 3 | 0 | 0 |
| phq_q9_self_harm | 60 | 0 | 0 | 0 |

## Session Issues

- None

## Sample Disagreements

- MVGOLD-EN-001 gad_q1_nervous: A=`1` vs B=`1`
- MVGOLD-EN-001 gad_q2_control_worry: A=`0` vs B=`0`
- MVGOLD-EN-001 gad_q3_excessive_worry: A=`1` vs B=`0`
- MVGOLD-EN-001 gad_q4_trouble_relaxing: A=`0` vs B=`0`
- MVGOLD-EN-001 gad_q6_irritability: A=`1` vs B=`2`
- MVGOLD-EN-001 gad_q7_afraid: A=`0` vs B=`0`
- MVGOLD-EN-001 phq_q2_low_mood: A=`2` vs B=`2`
- MVGOLD-EN-001 phq_q4_fatigue: A=`0` vs B=`0`
- MVGOLD-EN-001 phq_q5_appetite: A=`0` vs B=`0`
- MVGOLD-EN-001 phq_q6_worthlessness: A=`0` vs B=`1`
- MVGOLD-EN-001 phq_q7_concentration: A=`0` vs B=`0`
- MVGOLD-EN-002 gad_q3_excessive_worry: A=`1` vs B=`0`
- MVGOLD-EN-002 gad_q4_trouble_relaxing: A=`0` vs B=`0`
- MVGOLD-EN-002 gad_q6_irritability: A=`1` vs B=`1`
- MVGOLD-EN-002 phq_q2_low_mood: A=`0` vs B=`0`
- MVGOLD-EN-002 phq_q3_sleep: A=`0` vs B=`0`
- MVGOLD-EN-002 phq_q4_fatigue: A=`1` vs B=`1`
- MVGOLD-EN-002 phq_q6_worthlessness: A=`0` vs B=`0`
- MVGOLD-EN-003 gad_q6_irritability: A=`1` vs B=`0`
- MVGOLD-EN-003 phq_q1_anhedonia: A=`0` vs B=`0`
- ...and `108` more disagreement rows
