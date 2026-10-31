# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5729**
- incumbent: **signal-g05721-c01-dcdb0d5ee1**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1249**
- incumbent signal objective: **-0.0466**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05729-c01-2a27789147: portfolio gain **-0.2325** / signal **-0.0614** / accepted **NO**
- feedback-g05729-c02-3961a6d0bd: portfolio gain **-0.0606** / signal **-0.1549** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
