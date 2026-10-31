# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **9/26 trusted draws**
- status: **active**
- current target: **round 702**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-10-31T15:11:39+09:00**
- base q SHA-256: `f6b81eba4d095b9b3fb40b69483c716f6dd0473d15eaf93fc512b2ede1033454`
- calibrated q SHA-256: `fd11175bcbfe61dad0783d3de1a343fa99a7de765bc5dd3be82effcd6f268efc`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.14308172**
- mean Brier improvement vs locked base: **+0.01717104**
- mean log delta vs Uniform: **+0.00305640**
- mean Brier improvement vs Uniform: **+0.00017634**
- mean actual-mass delta vs Uniform: **+0.00097703**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **9/9**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
