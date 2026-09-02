# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **0/26 trusted draws**
- status: **active**
- current target: **round 693**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-09-02T11:25:45+09:00**
- expert count: **11**
- final q SHA-256: `e0c96f42547169da34c0f1935fe9597e06cf6cedd31f5a4f412db46ab5eb60db`
- decomposition max abs error: **2.776e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.553022**
- hot_20: **0.157084**
- momentum: **0.082439**
- pair_context: **0.045275**
- ewma_30: **0.044562**
- overdue: **0.027222**
- hot_50: **0.025163**
- ewma_60: **0.020380**
- hot_100: **0.016007**
- recent_cold: **0.014572**
- hot_200: **0.014275**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
