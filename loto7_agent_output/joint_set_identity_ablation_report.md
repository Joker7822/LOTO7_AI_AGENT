# Joint Set Number-Identity Ablation

- evaluated draws/model: **60**
- global label permutations/model: **4096**
- target result used before portfolio construction: **NO**
- Production promotion eligible: **NO**

## What this control removes

各回で実際に生成された5口をそのまま固定し、1〜37の数字ラベルだけを全評価期間で同じ写像に置換します。
これにより5口の重なり・分散・scenario最適化・config選択は維持したまま、将来当せん数字とのidentity alignmentだけを壊します。

## Joint Set v1

- Top7 hits: observed **1.5167** / permuted mean **1.3257** / identity edge **+0.1909** / p **0.065658**
- portfolio score: observed **2.9525** / permuted mean **2.8038** / identity edge **+0.1487** / p **0.134977**
- portfolio permutation p95/p99: **3.0280 / 3.1277**

## Joint Set v2

- Top7 hits: observed **1.5833** / permuted mean **1.3255** / identity edge **+0.2579** / p **0.027093**
- portfolio score: observed **2.8947** / permuted mean **2.8092** / identity edge **+0.0854** / p **0.258970**
- portfolio permutation p95/p99: **3.0308 / 3.1282**

> p値はResearch診断です。過去60回の再利用データであり、Future OOSの独立証拠ではありません。
> この検定で優位でもProduction昇格条件は変わりません。
