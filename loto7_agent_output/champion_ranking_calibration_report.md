# Champion Ranking-Preserving Calibration Replay

- calibration: **champion-ranking-calibration-v1**
- Champion: **baseline-5fdb8dc2ad**
- evaluated nested window: **120 draws**
- rank preservation: **100.00%**
- next target: **round 705**
- next calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- role: **Research only; no Production promotion authority**

## Nested calibrated signal vs Uniform

- Top-7 hits: **1.433333** (edge +0.109009)
- actual mass edge: **+0.00023593**
- log edge: **+0.00050953**
- Brier edge: **+0.00002870**

## Paired vs uncalibrated Champion

- log delta: **+0.13306752** (moving-block 95% CI +0.09657006 .. +0.16534153)
- Brier improvement: **+0.01315394** (95% CI +0.00955511 .. +0.01715308)
- Top-7 delta: **+0.00000000** (95% CI +0.00000000 .. +0.00000000)

## Paired vs Uniform

- log delta: **+0.00050953** (95% CI -0.00108451 .. +0.00319705)
- Brier improvement: **+0.00002870** (95% CI -0.00006155 .. +0.00017812)
- actual mass delta: **+0.00023593** (95% CI -0.00007821 .. +0.00079506)

- calibration improves Champion proper scores without rank loss: **true**
- research-worthy signal vs Uniform: **true**
- robust Uniform edge: **false**

> Calibration does not generate tickets and does not alter the Production Champion or any frozen Future-OOS registry.
