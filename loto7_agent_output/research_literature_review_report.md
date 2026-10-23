# Literature metadata reviewer & experiment design queue

This is not full-text paper review or an automated forecasting experiment.
Discovery chain: fa1e0ce004ba41b985f395590bae782e49f886fc9bfa2c8b263ba1ac555be073
Research guard: WAIT_FOR_NEW_DATA; search permitted: False
Triaged papers: 16; non-executable designs: 5

## Read-next list (metadata only)
- DOI 10.2139/ssrn.6617378 (2026) review_next topics=calibration,ensemble
- DOI 10.5194/egusphere-2026-4028 (2026) review_next topics=calibration,distribution_shift
- DOI 10.5281/zenodo.21508920 (2026) review_next topics=calibration,online_evaluation,distribution_shift
- DOI 10.1016/j.ijforecast.2026.04.009 (2026) review_next topics=calibration
- DOI 10.1145/3765611.3815392 (2026) review_next topics=calibration
- DOI 10.1093/jrsssb/qkaf014 (2025) background topics=anytime_evidence
- DOI 10.1214/24-ejs2228 (2024) background topics=anytime_evidence
- DOI 10.2139/ssrn.4689006 (2024) background topics=anytime_evidence
- DOI 10.2139/ssrn.7599398 (2026) background topics=anytime_evidence
- DOI 10.1007/s42081-026-00374-w (2026) background topics=online_evaluation
- DOI 10.2139/ssrn.4896166 (2024) background topics=online_evaluation
- DOI 10.2139/ssrn.5946791 (2025) background topics=distribution_shift

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
### anytime_evidence
- Hypothesis: A new preregistered forecast could show evidence against conditional uniformity.
- Metric: future-only nonnegative e-process with conditional mean at most 1
- Plan: Predeclare a new non-overlapping future stream, frozen predictable e-factor and threshold.
- Human approval, future preregistration, independent data required.
### distribution_shift
- Hypothesis: Chronological model performance may differ by era.
- Metric: era-wise log/Brier edge and descriptive heterogeneity
- Plan: Compare fixed non-overlapping eras, paired block uncertainty and fair-world histories.
- Human approval, future preregistration, independent data required.
### ensemble
- Hypothesis: Fixed probability averaging may reduce variance without improving true accuracy.
- Metric: paired Brier/log-score edge and fair-world selection-adjusted comparison
- Plan: Compare original frozen ensemble, fifth expert and uniform comparator on identical chronological targets.
- Human approval, future preregistration, independent data required.
No automatic code, Champion, Production, OOS modification or new optimizer trials.
