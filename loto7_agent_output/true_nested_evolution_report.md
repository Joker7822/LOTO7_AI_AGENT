# True Nested / Prequential Evolution

- evaluated rounds: **60**
- warm-up evolution steps: **60**
- inner signal candidates/step: **2**
- current Research Winner injected into history: **NO**
- target result used before model selection: **NO**
- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**

## Signal
- mean Top7 hits: **1.4167** (delta vs uniform +0.0923)
- mean actual mass: **0.190416**
- mean log edge vs uniform: **-0.022359**
- mean Brier edge vs uniform: **-0.001677**

## Five-ticket Portfolio
- mean max hits: **2.3833** / precision random **2.4387**
- >=3 round rate: **40.00%** / random **43.82%**
- >=4 round rate: **8.33%** / random **7.03%**
- score: **2.7235** / random **2.7772**
- score delta: **-0.0537** (bootstrap 95% CI -0.3279〜+0.2325)
- round win rate vs random: **40.0%**

> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。
> 過去診断であり、Production昇格は未来OOSのみです。
