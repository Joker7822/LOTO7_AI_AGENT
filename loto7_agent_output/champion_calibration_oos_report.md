# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **2/26 trusted draws**
- status: **active**
- current target: **round 695**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-09-12T13:54:57+09:00**
- base q SHA-256: `dfa02893c05dc0fecc0b34b6ccba80f5fbe0ba4368c613847dab85bdfb6d70e1`
- calibrated q SHA-256: `aa8c1292420715dead8a27b49104a913c6b00d409dc05135997e470c21327749`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.14975362**
- mean Brier improvement vs locked base: **+0.01693978**
- mean log delta vs Uniform: **+0.00511932**
- mean Brier improvement vs Uniform: **+0.00032841**
- mean actual-mass delta vs Uniform: **+0.00154228**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **2/2**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
