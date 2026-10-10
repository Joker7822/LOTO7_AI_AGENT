# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **6/26 trusted draws**
- status: **active**
- current target: **round 699**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-10-10T15:17:33+09:00**
- base q SHA-256: `2343d92c9818d61acdf97e5601ee783609a997b075a0f92578985c7a29c429d9`
- calibrated q SHA-256: `1d72304644c3947ecff505d4359d86fb470e40694d5e3bead676d36f9c94806c`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.11629292**
- mean Brier improvement vs locked base: **+0.01751270**
- mean log delta vs Uniform: **+0.00606509**
- mean Brier improvement vs Uniform: **+0.00034650**
- mean actual-mass delta vs Uniform: **+0.00162058**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **6/6**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
