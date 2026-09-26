# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **4/26 trusted draws**
- status: **active**
- current target: **round 697**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-09-26T14:21:52+09:00**
- base q SHA-256: `28573e6959080a59788ba6e8f9d9160fd61ae4e1869ce8475f0416304e6887b8`
- calibrated q SHA-256: `cb3905c6cb5cef807c62255fbf5eaf139fa1cfe030c07b013667a32730e07464`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.09721673**
- mean Brier improvement vs locked base: **+0.01595954**
- mean log delta vs Uniform: **+0.01090630**
- mean Brier improvement vs Uniform: **+0.00064434**
- mean actual-mass delta vs Uniform: **+0.00270737**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **4/4**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
