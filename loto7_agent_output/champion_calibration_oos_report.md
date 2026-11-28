# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **13/26 trusted draws**
- status: **active**
- current target: **round 706**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-11-28T17:20:27+09:00**
- base q SHA-256: `bee700e96525c916548a66639092056af9bd4e1bbb78f66926b9f819cd9689fd`
- calibrated q SHA-256: `fd4cc52575ef3df789c3098f90203ad689ed4ac1f2e6d1b7c533d47e2e3c8488`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.16446147**
- mean Brier improvement vs locked base: **+0.01735349**
- mean log delta vs Uniform: **-0.00112224**
- mean Brier improvement vs Uniform: **-0.00006348**
- mean actual-mass delta vs Uniform: **+0.00008228**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **13/13**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
