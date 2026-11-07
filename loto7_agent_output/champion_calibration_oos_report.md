# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **10/26 trusted draws**
- status: **active**
- current target: **round 703**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-11-07T15:29:06+09:00**
- base q SHA-256: `d6cec228fb3573b62dde3112c985d8eb1b67583e0d2e3a773f1b0fafc58ba5d7`
- calibrated q SHA-256: `c30d1883363f1bfa5de070e374591b6b93fd5ed84622c80d703cd412339949fb`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.15367350**
- mean Brier improvement vs locked base: **+0.01784893**
- mean log delta vs Uniform: **+0.00129781**
- mean Brier improvement vs Uniform: **+0.00007461**
- mean actual-mass delta vs Uniform: **+0.00060857**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **10/10**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
