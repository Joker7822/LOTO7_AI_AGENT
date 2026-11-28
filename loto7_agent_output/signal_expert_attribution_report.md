# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **13/26 trusted draws**
- status: **active**
- current target: **round 706**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-11-28T17:52:37+09:00**
- expert count: **11**
- final q SHA-256: `bee700e96525c916548a66639092056af9bd4e1bbb78f66926b9f819cd9689fd`
- decomposition max abs error: **2.082e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.505878**
- hot_20: **0.165608**
- momentum: **0.103942**
- pair_context: **0.065321**
- ewma_30: **0.040865**
- hot_50: **0.030496**
- overdue: **0.026014**
- ewma_60: **0.017790**
- recent_cold: **0.015128**
- hot_100: **0.014825**
- hot_200: **0.014133**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
