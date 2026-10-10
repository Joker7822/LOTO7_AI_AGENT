# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **6/26 trusted draws**
- status: **active**
- current target: **round 699**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-10-10T15:59:56+09:00**
- expert count: **11**
- final q SHA-256: `2343d92c9818d61acdf97e5601ee783609a997b075a0f92578985c7a29c429d9`
- decomposition max abs error: **1.388e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.578426**
- hot_20: **0.142237**
- momentum: **0.076578**
- ewma_30: **0.047777**
- pair_context: **0.038185**
- hot_50: **0.030830**
- overdue: **0.024389**
- ewma_60: **0.018480**
- hot_100: **0.014976**
- recent_cold: **0.014114**
- hot_200: **0.014007**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
