# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **3/26 trusted draws**
- status: **active**
- current target: **round 696**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-09-19T13:55:53+09:00**
- base q SHA-256: `9364f21eed47edd6f2143d58794535fc7ef96c9b44aa18bd9d9999fce83bda6d`
- calibrated q SHA-256: `f9e01a0c28261f51b30a2a3404846c79eb94ace337d0fc3c645fec64431b1757`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.10594730**
- mean Brier improvement vs locked base: **+0.00903194**
- mean log delta vs Uniform: **+0.01386909**
- mean Brier improvement vs Uniform: **+0.00087499**
- mean actual-mass delta vs Uniform: **+0.00344339**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **3/3**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
