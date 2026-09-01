# Champion Calibration Exact Future-OOS E-Process

- version: **champion-calibration-exact-eprocess-v1**
- preregistered at JST: **2026-09-01T12:31:54+09:00**
- starts target: **round 693**
- fixed horizon: **0/26 trusted draws**
- null: **conditional_on_the_past_each_future_winning_7_set_is_uniform_over_all_C(37,7)_subsets**
- exact MGF: **without-replacement elementary-symmetric DP**
- lambda mixture: **0.25, 0.5, 1.0, 2.0, 4.0**
- endpoint threshold: **e >= 40 each**
- family alpha: **0.050** (two-endpoint Bonferroni registration)

## Current evidence

- mean log edge vs Uniform: **未採点**
- log-score mixture e-value: **1.00000000**
- mean Brier improvement vs Uniform: **未採点**
- Brier mixture e-value: **1.00000000**
- mean actual-mass delta vs Uniform: **未採点**
- rank preserved: **0/0**

## Fixed claim rule

A `robust_uniform_proper_score_edge` claim is allowed only after exactly 26 trusted draws and only if:
1. ranking is preserved on all trusted draws;
2. mean log edge vs Uniform is positive;
3. mean Brier improvement vs Uniform is positive;
4. log-score mixture e-value is at least 40;
5. Brier mixture e-value is at least 40.

- current claim status: **not_evaluated_until_horizon_complete**
- Interim e-values and means are diagnostics only; this protocol has no Production promotion authority.
