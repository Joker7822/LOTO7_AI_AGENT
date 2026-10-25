# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **8/26 trusted draws**
- status: **active**
- current target: **round 701**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-10-25T15:00:30+09:00**
- expert count: **11**
- final q SHA-256: `b1b0fc10a2930ce615cbdd9530c040c84165367a59af6a52586908f190c2ebf2`
- decomposition max abs error: **5.551e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.542959**
- hot_20: **0.136073**
- momentum: **0.073194**
- ewma_30: **0.063143**
- hot_50: **0.048600**
- pair_context: **0.040852**
- overdue: **0.030004**
- ewma_60: **0.021354**
- hot_100: **0.015374**
- recent_cold: **0.014343**
- hot_200: **0.014104**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
