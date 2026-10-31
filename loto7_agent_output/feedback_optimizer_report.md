# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5803**
- incumbent: **signal-g05799-c01-52cad64a80**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0955**
- incumbent signal objective: **-0.0462**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05803-c01-208a1f7861: portfolio gain **-0.2147** / signal **-0.0626** / accepted **NO**
- feedback-g05803-c02-a46c1d0f50: portfolio gain **-0.1094** / signal **-0.2397** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
