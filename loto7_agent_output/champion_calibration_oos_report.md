# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **11/26 trusted draws**
- status: **active**
- current target: **round 704**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-11-14T15:56:38+09:00**
- base q SHA-256: `1f1f710e82bcab31985ab880689ea3b5c416d817dca3a064589d344b6f47fb3e`
- calibrated q SHA-256: `47de6dac38df0ab775b91c3e586c9e2bad95d0aacf480a03ba539becb0f89747`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.17474301**
- mean Brier improvement vs locked base: **+0.01864244**
- mean log delta vs Uniform: **-0.00087177**
- mean Brier improvement vs Uniform: **-0.00004628**
- mean actual-mass delta vs Uniform: **+0.00017047**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **11/11**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
