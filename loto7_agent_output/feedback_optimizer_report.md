# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5209**
- incumbent: **signal-g05198-c01-4cb45d5a7b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0005**
- incumbent signal objective: **-0.0426**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05209-c01-bcb430dd74: portfolio gain **-0.1154** / signal **-0.0565** / accepted **NO**
- feedback-g05209-c02-fcfe03f3c8: portfolio gain **-0.0486** / signal **-0.1435** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
