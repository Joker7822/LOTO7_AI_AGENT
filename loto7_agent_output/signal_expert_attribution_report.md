# Signal Expert Attribution Future-OOS

- protocol: **signal-expert-attribution-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base: **baseline-5fdb8dc2ad**
- fixed observation horizon: **1/26 trusted draws**
- status: **active**
- current target: **round 694**
- pre-frozen: **YES**
- interim model changes allowed: **false**
- frozen at JST: **2026-09-05T14:38:57+09:00**
- expert count: **11**
- final q SHA-256: `7e6a6cfbbe58e637ee5fcb1b8b4928fd469f303cfe780a7d81424a3320473ac5`
- decomposition max abs error: **1.110e-16**
- calibration-shadow crosscheck: **matched**

## Current pre-frozen effective weights

- ewma_10: **0.589004**
- hot_20: **0.140486**
- momentum: **0.067405**
- ewma_30: **0.052100**
- pair_context: **0.034925**
- hot_50: **0.031841**
- overdue: **0.020652**
- ewma_60: **0.020276**
- hot_100: **0.015106**
- recent_cold: **0.014126**
- hot_200: **0.014079**

## Interpretation boundary

- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.
- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.
- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.
- **descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon**
- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.
