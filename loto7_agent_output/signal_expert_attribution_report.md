# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **5/26 trusted draws**
- status: **active**
- current target: **round 698**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-10-03T15:24:20+09:00**
- expert count: **11**
- final q SHA-256: `1715ebee90c5994c7d96ae94da37fe17833e910ce90e3272684ffebe30bddfcc`
- decomposition max abs error: **4.163e-17**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.575841**
- hot_20: **0.140198**
- momentum: **0.069847**
- ewma_30: **0.052938**
- pair_context: **0.039596**
- hot_50: **0.034405**
- overdue: **0.024887**
- ewma_60: **0.019241**
- hot_100: **0.014964**
- recent_cold: **0.014100**
- hot_200: **0.013983**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
