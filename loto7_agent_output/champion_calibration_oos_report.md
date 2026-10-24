# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **7/26 trusted draws**
- status: **awaiting_trusted_result_verification**
- current target: **round 700**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-10-17T13:54:27+09:00**
- base q SHA-256: `d9782b8d436d3994704ef0cf5cd4f016131bc2dce6566b4b8b040e9452ed163b`
- calibrated q SHA-256: `1cf517744c319e384022f513bf3a462902ad53467a36cb0131f21cb2c71c9321`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.12072679**
- mean Brier improvement vs locked base: **+0.01609831**
- mean log delta vs Uniform: **+0.00612910**
- mean Brier improvement vs Uniform: **+0.00035658**
- mean actual-mass delta vs Uniform: **+0.00163225**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **7/7**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
