# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **11/26 trusted draws**
- status: **active**
- current target: **round 704**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-11-14T16:33:57+09:00**
- expert count: **11**
- final q SHA-256: `1f1f710e82bcab31985ab880689ea3b5c416d817dca3a064589d344b6f47fb3e`
- decomposition max abs error: **1.388e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.524578**
- hot_20: **0.155461**
- momentum: **0.083948**
- pair_context: **0.055798**
- ewma_30: **0.050712**
- hot_50: **0.037785**
- overdue: **0.028280**
- ewma_60: **0.019389**
- hot_100: **0.015210**
- recent_cold: **0.014712**
- hot_200: **0.014127**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
