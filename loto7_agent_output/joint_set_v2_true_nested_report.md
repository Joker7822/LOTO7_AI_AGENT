# Joint Set Research v2.1 — Calibrated Inclusion + Prior-Only Rank Gate

- evaluated rounds: **60**
- predeclared configs: **5**
- selection window: **120** prior draws
- target result used before selection: **NO**
- Production promotion eligible: **NO**

## Bernoulli Inclusion Signal (sum p = 7)
- mean Top7 hits: **1.5833**
- mean actual inclusion probability: **0.189245**
- mean Bernoulli log edge vs uniform: **+0.000026**
- mean Bernoulli Brier edge vs uniform: **+0.000007**
- mean calibrated probability gate: **0.062**

## Prior-Only Portfolio Rank Gate
- mean portfolio gate: **0.199**
- mean prior Top7 edge: **+0.2271**
- mean prior rank z: **+2.485**

## Expected-Utility Five-Ticket Portfolio
- mean max hits: **2.5000** / random **2.4387**
- >=3 round rate: **48.33%** / random **43.82%**
- >=4 round rate: **8.33%** / random **7.03%**
- score: **2.8610** / random **2.7772**
- score delta: **+0.0838** (bootstrap 95% CI -0.1801〜+0.3583)

> v2.1ではproper-score用の校正確率と、5口構築用のprior-only順位Gateを分離します。
> Research-only。Future OOS確認前にProductionへ昇格しません。
