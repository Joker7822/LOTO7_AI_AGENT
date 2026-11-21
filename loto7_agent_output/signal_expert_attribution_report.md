# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **12/26 trusted draws**
- status: **active**
- current target: **round 705**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-11-21T17:14:59+09:00**
- expert count: **11**
- final q SHA-256: `ade1017ce821ea097f4b425d7b9838fb415973657782f328f834a7b0b1166ac9`
- decomposition max abs error: **1.388e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.511707**
- hot_20: **0.161003**
- momentum: **0.092919**
- pair_context: **0.060692**
- ewma_30: **0.046337**
- hot_50: **0.035086**
- overdue: **0.029832**
- ewma_60: **0.018413**
- recent_cold: **0.014974**
- hot_100: **0.014937**
- hot_200: **0.014099**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
