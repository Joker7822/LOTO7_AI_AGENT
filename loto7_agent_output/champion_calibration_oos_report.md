# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **1/26 trusted draws**
- status: **active**
- current target: **round 694**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-09-05T13:52:48+09:00**
- base q SHA-256: `7e6a6cfbbe58e637ee5fcb1b8b4928fd469f303cfe780a7d81424a3320473ac5`
- calibrated q SHA-256: `da99b03e19d3e8cef55ddd3dd0d78645934dfc86571dceec2157949c7f4e096b`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **-0.13203944**
- mean Brier improvement vs locked base: **-0.00940996**
- mean log delta vs Uniform: **+0.03454944**
- mean Brier improvement vs Uniform: **+0.00207891**
- mean actual-mass delta vs Uniform: **+0.00761201**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **1/1**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
