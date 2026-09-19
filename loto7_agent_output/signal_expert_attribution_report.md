# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **3/26 trusted draws**
- status: **active**
- current target: **round 696**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-09-19T14:46:32+09:00**
- expert count: **11**
- final q SHA-256: `9364f21eed47edd6f2143d58794535fc7ef96c9b44aa18bd9d9999fce83bda6d`
- decomposition max abs error: **5.551e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.572629**
- hot_20: **0.135459**
- momentum: **0.067241**
- ewma_30: **0.060185**
- hot_50: **0.040261**
- pair_context: **0.036263**
- overdue: **0.024971**
- ewma_60: **0.020245**
- hot_100: **0.014644**
- recent_cold: **0.014131**
- hot_200: **0.013970**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
