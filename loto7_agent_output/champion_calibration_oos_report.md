# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **8/26 trusted draws**
- status: **active**
- current target: **round 701**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-10-25T14:10:08+09:00**
- base q SHA-256: `b1b0fc10a2930ce615cbdd9530c040c84165367a59af6a52586908f190c2ebf2`
- calibrated q SHA-256: `683f0b1aaa7d4fc455bc8c1de35f4b0df5dc408e5fdc4d8780222007b5ad6ef3`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.15775903**
- mean Brier improvement vs locked base: **+0.01840750**
- mean log delta vs Uniform: **+0.00230085**
- mean Brier improvement vs Uniform: **+0.00013816**
- mean actual-mass delta vs Uniform: **+0.00085685**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **8/8**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
