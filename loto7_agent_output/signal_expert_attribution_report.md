# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **2/26 trusted draws**
- status: **active**
- current target: **round 695**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-09-13T15:46:33+09:00**
- expert count: **11**
- final q SHA-256: `dfa02893c05dc0fecc0b34b6ccba80f5fbe0ba4368c613847dab85bdfb6d70e1`
- decomposition max abs error: **2.776e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.566962**
- hot_20: **0.145934**
- momentum: **0.076897**
- ewma_30: **0.049593**
- pair_context: **0.040051**
- hot_50: **0.031689**
- overdue: **0.025414**
- ewma_60: **0.019902**
- hot_100: **0.015091**
- recent_cold: **0.014385**
- hot_200: **0.014081**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
