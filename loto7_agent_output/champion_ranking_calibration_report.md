# Champion Ranking-Preserving Calibration Replay

- calibration: **champion-ranking-calibration-v1**
- Champion: **baseline-5fdb8dc2ad**
- evaluated nested window: **120 draws**
- rank preservation: **100.00%**
- next target: **round 693**
- next calibration: **shrink-0p93-1209c16b93** (T=1.00, uniform_mix=0.93)
- role: **Research only; no Production promotion authority**

## Nested calibrated signal vs Uniform

- Top-7 hits: **1.466667** (edge +0.142342)
- actual mass edge: **+0.00023120**
- log edge: **+0.00063469**
- Brier edge: **+0.00003550**

## Paired vs uncalibrated Champion

- log delta: **+0.12693245** (moving-block 95% CI +0.09302943 .. +0.15870168)
- Brier improvement: **+0.01229900** (95% CI +0.00877632 .. +0.01554691)
- Top-7 delta: **+0.00000000** (95% CI +0.00000000 .. +0.00000000)

## Paired vs Uniform

- log delta: **+0.00063469** (95% CI -0.00105129 .. +0.00309515)
- Brier improvement: **+0.00003550** (95% CI -0.00005862 .. +0.00016578)
- actual mass delta: **+0.00023120** (95% CI -0.00010189 .. +0.00072160)

- calibration improves Champion proper scores without rank loss: **true**
- research-worthy signal vs Uniform: **true**
- robust Uniform edge: **false**

> Calibration does not generate tickets and does not alter the Production Champion or any frozen Future-OOS registry.
