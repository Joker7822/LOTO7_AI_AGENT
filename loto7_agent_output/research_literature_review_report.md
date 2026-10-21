# Literature metadata reviewer & experiment design queue

This is not full-text paper review or an automated forecasting experiment.
Discovery chain: 41e8d8f69051cbfc4bb25edb6acf0a552fa04ec4b809d478ce7acbe75f74ef5e
Research guard: WAIT_FOR_NEW_DATA; search permitted: False
Triaged papers: 4; non-executable designs: 3

## Read-next list (metadata only)
- DOI 10.2139/ssrn.6617378 (2026) review_next topics=calibration,ensemble
- DOI 10.1016/j.ijforecast.2026.04.009 (2026) review_next topics=calibration
- DOI 10.1145/3765611.3815392 (2026) review_next topics=calibration
- DOI 10.2139/ssrn.4896166 (2024) background topics=online_evaluation

## Draft-only experiment templates
### calibration
- Hypothesis: Frozen 37-number inclusion forecasts may need calibration auditing.
- Metric: Brier/log-score and calibration-bin deviation
- Plan: Evaluate reliability bins and prequential proper scores using only existing frozen predictions.
- Human approval, future preregistration, independent data required.
### online_evaluation
- Hypothesis: A fixed online learner could differ from the uniform baseline in future data.
- Metric: prequential proper-score edge versus uniform 7/37
- Plan: Specify update timing, fixed rate, and test-then-train chronology before any future evaluation.
- Human approval, future preregistration, independent data required.
### ensemble
- Hypothesis: Fixed probability averaging may reduce variance without improving true accuracy.
- Metric: paired Brier/log-score edge and fair-world selection-adjusted comparison
- Plan: Compare original frozen ensemble, fifth expert and uniform comparator on identical chronological targets.
- Human approval, future preregistration, independent data required.
No automatic code, Champion, Production, OOS modification or new optimizer trials.
