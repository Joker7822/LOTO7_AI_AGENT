# True Nested / Prequential Evolution

- evaluated rounds: **60**
- warm-up evolution steps: **60**
- inner signal candidates/step: **2**
- current Research Winner injected into history: **NO**
- target result used before model selection: **NO**
- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**

## Signal
- mean Top7 hits: **1.5167** (delta vs uniform +0.1923)
- mean actual mass: **0.192280**
- mean log edge vs uniform: **-0.013364**
- mean Brier edge vs uniform: **-0.001043**

## Five-ticket Portfolio
- mean max hits: **2.5500** / precision random **2.4387**
- >=3 round rate: **51.67%** / random **43.82%**
- >=4 round rate: **10.00%** / random **7.03%**
- score: **2.9562** / random **2.7772**
- score delta: **+0.1790** (bootstrap 95% CI -0.1114〜+0.4716)
- round win rate vs random: **51.7%**

> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。
> 過去診断であり、Production昇格は未来OOSのみです。
