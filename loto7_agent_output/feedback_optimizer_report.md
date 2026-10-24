# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5127**
- incumbent: **signal-g05125-c02-f268e34b06**
- trials: **2**
- accepted: **feedback-g05127-c01-3807b2151d**
- incumbent portfolio objective: **+0.0054**
- incumbent signal objective: **-0.1071**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05127-c01-3807b2151d: portfolio gain **+0.0228** / signal **-0.0807** / accepted **YES**
- feedback-g05127-c02-9d3fee072c: portfolio gain **-0.2664** / signal **-0.3434** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
