# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4800**
- incumbent: **signal-g04789-c01-29ccf32ff6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0225**
- incumbent signal objective: **-0.0453**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04800-c01-e588ccce5c: portfolio gain **+0.0388** / signal **-0.0622** / accepted **NO**
- feedback-g04800-c02-4b25a7d2f5: portfolio gain **-0.0094** / signal **-0.1799** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
