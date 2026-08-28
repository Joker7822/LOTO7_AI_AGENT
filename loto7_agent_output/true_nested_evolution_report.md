# True Nested / Prequential Evolution

- evaluated rounds: **60**
- warm-up evolution steps: **60**
- inner signal candidates/step: **2**
- current Research Winner injected into history: **NO**
- target result used before model selection: **NO**
- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**

## Signal
- mean Top7 hits: **1.5000** (delta vs uniform +0.1757)
- mean actual mass: **0.192386**
- mean log edge vs uniform: **-0.011924**
- mean Brier edge vs uniform: **-0.000989**

## Five-ticket Portfolio
- mean max hits: **2.5167** / precision random **2.4387**
- >=3 round rate: **48.33%** / random **43.82%**
- >=4 round rate: **6.67%** / random **7.03%**
- score: **2.8795** / random **2.7772**
- score delta: **+0.1023** (bootstrap 95% CI -0.1425〜+0.3576)
- round win rate vs random: **48.3%**

> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。
> 過去診断であり、Production昇格は未来OOSのみです。
