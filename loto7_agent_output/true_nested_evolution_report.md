# True Nested / Prequential Evolution

- evaluated rounds: **60**
- warm-up evolution steps: **60**
- inner signal candidates/step: **2**
- current Research Winner injected into history: **NO**
- target result used before model selection: **NO**
- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**

## Signal
- mean Top7 hits: **1.4167** (delta vs uniform +0.0923)
- mean actual mass: **0.191360**
- mean log edge vs uniform: **-0.018925**
- mean Brier edge vs uniform: **-0.001451**

## Five-ticket Portfolio
- mean max hits: **2.4333** / precision random **2.4387**
- >=3 round rate: **45.00%** / random **43.82%**
- >=4 round rate: **6.67%** / random **7.03%**
- score: **2.7792** / random **2.7772**
- score delta: **+0.0020** (bootstrap 95% CI -0.2512〜+0.2751)
- round win rate vs random: **45.0%**

> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。
> 過去診断であり、Production昇格は未来OOSのみです。
