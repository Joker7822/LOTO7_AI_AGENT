# Joint Set Research v2 — Inclusion Probability Strict True Nested

- evaluated rounds: **60**
- predeclared configs: **5**
- selection window: **120** prior draws
- target result used before selection: **NO**
- Production promotion eligible: **NO**

## Bernoulli Inclusion Signal (sum p = 7)
- mean Top7 hits: **1.5667**
- mean actual inclusion probability: **0.189199**
- mean Bernoulli log edge vs uniform: **-0.000031**
- mean Bernoulli Brier edge vs uniform: **-0.000011**
- mean model gate: **0.062**

## Expected-Utility Five-Ticket Portfolio
- mean max hits: **2.5167** / random **2.4387**
- >=3 round rate: **50.00%** / random **43.82%**
- >=4 round rate: **10.00%** / random **7.03%**
- score: **2.8937** / random **2.7772**
- score delta: **+0.1165** (bootstrap 95% CI -0.1657〜+0.4051)

> v2は37数字を独立カテゴリ確率ではなく、合計7のinclusion probabilityとして校正します。
> Research-only。Future OOS確認前にProductionへ昇格しません。
