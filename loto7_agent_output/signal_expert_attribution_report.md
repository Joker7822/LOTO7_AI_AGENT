# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **7/26 trusted draws**
- status: **awaiting_trusted_result_verification**
- current target: **round 700**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-10-17T14:32:41+09:00**
- expert count: **11**
- final q SHA-256: `d9782b8d436d3994704ef0cf5cd4f016131bc2dce6566b4b8b040e9452ed163b`
- decomposition max abs error: **2.776e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.563911**
- hot_20: **0.135450**
- momentum: **0.065562**
- ewma_30: **0.063682**
- hot_50: **0.048039**
- pair_context: **0.037071**
- overdue: **0.022331**
- ewma_60: **0.020921**
- hot_100: **0.014915**
- recent_cold: **0.014079**
- hot_200: **0.014038**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
