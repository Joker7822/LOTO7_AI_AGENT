# Joint Set Research v1 — Strict True Nested

- evaluated rounds: **60**
- predeclared configs: **5**
- selection window: **120** prior draws
- validation scenarios/round: **256**
- target result used before selection: **NO**
- Production promotion eligible: **NO**

## Signal + Dynamic Uniform Gate
- mean Top7 hits: **1.5333**
- mean actual mass: **0.189530**
- mean log edge vs uniform: **-0.001150**
- mean Brier edge vs uniform: **-0.000059**
- mean model gate: **0.474**

## Expected-Utility Five-Ticket Portfolio
- mean max hits: **2.5833** / random **2.4387**
- >=3 round rate: **51.67%** / random **43.82%**
- >=4 round rate: **10.00%** / random **7.03%**
- score: **2.9688** / random **2.7772**
- score delta: **+0.1916** (bootstrap 95% CI -0.0691〜+0.4588)

## External metadata
- trusted records: **0**
- usable feature names: **0**
- post-draw/same-round leakage guard: **ON**

> Joint marginal + low-rank pair structure + regime filter + confidence gate + scenario portfolio optimizationを同一のstrict prior-only評価で測定します。
> 過去診断であり、昇格証拠ではありません。
