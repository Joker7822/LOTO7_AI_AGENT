# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **9/26 trusted draws**
- status: **active**
- current target: **round 702**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-10-31T15:57:08+09:00**
- expert count: **11**
- final q SHA-256: `f6b81eba4d095b9b3fb40b69483c716f6dd0473d15eaf93fc512b2ede1033454`
- decomposition max abs error: **2.776e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.556156**
- hot_20: **0.144267**
- momentum: **0.076611**
- ewma_30: **0.052610**
- pair_context: **0.043765**
- hot_50: **0.039866**
- overdue: **0.024550**
- ewma_60: **0.019002**
- hot_100: **0.014931**
- recent_cold: **0.014291**
- hot_200: **0.013950**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
