# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **10/26 trusted draws**
- status: **active**
- current target: **round 703**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-11-07T16:02:56+09:00**
- expert count: **11**
- final q SHA-256: `d6cec228fb3573b62dde3112c985d8eb1b67583e0d2e3a773f1b0fafc58ba5d7`
- decomposition max abs error: **1.388e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.531259**
- hot_20: **0.159475**
- momentum: **0.086258**
- ewma_30: **0.050592**
- pair_context: **0.046917**
- hot_50: **0.039041**
- overdue: **0.024544**
- ewma_60: **0.018678**
- hot_100: **0.014859**
- recent_cold: **0.014419**
- hot_200: **0.013959**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
