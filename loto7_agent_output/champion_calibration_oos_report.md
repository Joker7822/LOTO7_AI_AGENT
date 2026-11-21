# Champion Calibration Future-OOS Shadow

- protocol: **champion-calibration-oos-v1**
- role: **Research diagnostic only; no Production authority**
- locked base model: **baseline-5fdb8dc2ad**
- fixed prospective horizon: **12/26 trusted draws**
- status: **active**
- current target: **round 705**
- pre-frozen: **YES**
- current calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- frozen at JST: **2026-11-21T16:38:32+09:00**
- base q SHA-256: `ade1017ce821ea097f4b425d7b9838fb415973657782f328f834a7b0b1166ac9`
- calibrated q SHA-256: `f69c88f4c99dbc67e30e9d84cced5eb29c3c4914bfde6b5914836a360070df75`
- rank preserved: **true**

## Trusted cumulative diagnostics

- mean log delta vs locked base: **+0.16896868**
- mean Brier improvement vs locked base: **+0.01793665**
- mean log delta vs Uniform: **-0.00097406**
- mean Brier improvement vs Uniform: **-0.00005387**
- mean actual-mass delta vs Uniform: **+0.00012903**
- mean Top-7 delta vs locked base: **+0.00000000**
- rank preserved trusted draws: **12/12**

## Claim policy

- **no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete**
- current claim status: **not_evaluated_until_horizon_complete**
- Interim means are descriptive only; no robust Uniform-edge claim is made before 26 trusted draws.
- Missing, tampered, or post-result references are never reconstructed; affected draws fail closed.
