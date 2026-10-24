# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5259**
- incumbent: **signal-g05198-c01-4cb45d5a7b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0005**
- incumbent signal objective: **-0.0426**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05259-c01-def1ee4e88: portfolio gain **-0.0568** / signal **-0.0576** / accepted **NO**
- feedback-g05259-c02-30d3901e2a: portfolio gain **+0.0335** / signal **-0.0880** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
