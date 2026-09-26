# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **4/26 trusted draws**
- status: **active**
- current target: **round 697**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-09-26T15:06:48+09:00**
- expert count: **11**
- final q SHA-256: `28573e6959080a59788ba6e8f9d9160fd61ae4e1869ce8475f0416304e6887b8`
- decomposition max abs error: **2.776e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.592299**
- hot_20: **0.128414**
- momentum: **0.066401**
- ewma_30: **0.053641**
- pair_context: **0.039917**
- hot_50: **0.035570**
- overdue: **0.022019**
- ewma_60: **0.019135**
- hot_100: **0.014586**
- recent_cold: **0.014080**
- hot_200: **0.013939**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
