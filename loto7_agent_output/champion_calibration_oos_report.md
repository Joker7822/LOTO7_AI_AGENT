# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **5/26 trusted draws**
- status: **active**
- current target: **round 698**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-10-03T14:38:27+09:00**
- base q SHA-256: `1715ebee90c5994c7d96ae94da37fe17833e910ce90e3272684ffebe30bddfcc`
- calibrated q SHA-256: `8077cb7d0c354ec22cd7d9390302d33412c3d9075d0c3805ffe5a4d8b4602303`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.11334242**
- mean Brier improvement vs locked base: **+0.01819310**
- mean log delta vs Uniform: **+0.00708921**
- mean Brier improvement vs Uniform: **+0.00040948**
- mean actual-mass delta vs Uniform: **+0.00186901**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **5/5**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
