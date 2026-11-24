# Joint Set Number-Identity Ablation

- evaluated draws/model: **60**
- global label permutations/model: **4096**
- target result used before portfolio construction: **NO**
- Production promotion eligible: **NO**

## What this control removes

各回で実際に生成された5口をそのまま固定し、1〜37の数字ラベルだけを全評価期間で同じ写像に置換します。
これにより5口の重なり・分散・scenario最適化・config選択は維持したまま、将来当せん数字とのidentity alignmentだけを壊します。

## Joint Set v1

- Top7 hits: observed **1.5333** / permuted mean **1.3244** / identity edge **+0.2089** / p **0.038809**
- portfolio score: observed **2.9920** / permuted mean **2.8059** / identity edge **+0.1861** / p **0.086893**
- portfolio permutation p95/p99: **3.0312 / 3.1344**

## Joint Set v2

- Top7 hits: observed **1.5000** / permuted mean **1.3232** / identity edge **+0.1768** / p **0.092751**
- portfolio score: observed **2.8940** / permuted mean **2.8091** / identity edge **+0.0849** / p **0.254332**
- portfolio permutation p95/p99: **3.0309 / 3.1280**

> p値はResearch診断です。過去60回の再利用データであり、Future OOSの独立証拠ではありません。
> この検定で優位でもProduction昇格条件は変わりません。
