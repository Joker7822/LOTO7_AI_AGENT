# True Nested / Prequential Evolution

- evaluated rounds: **60**
- warm-up evolution steps: **60**
- inner signal candidates/step: **2**
- current Research Winner injected into history: **NO**
- target result used before model selection: **NO**
- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**

## Signal
- mean Top7 hits: **1.5333** (delta vs uniform +0.2090)
- mean actual mass: **0.192584**
- mean log edge vs uniform: **-0.012362**
- mean Brier edge vs uniform: **-0.001040**

## Five-ticket Portfolio
- mean max hits: **2.5000** / precision random **2.4387**
- >=3 round rate: **43.33%** / random **43.82%**
- >=4 round rate: **11.67%** / random **7.03%**
- score: **2.8832** / random **2.7772**
- score delta: **+0.1060** (bootstrap 95% CI -0.1889〜+0.4140)
- round win rate vs random: **43.3%**

> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。
> 過去診断であり、Production昇格は未来OOSのみです。
