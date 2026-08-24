# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2381**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1231**
- incumbent signal objective: **-0.0428**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02381-c01-d3c7ae9b62: portfolio gain **+0.1799** / signal **-0.0629** / accepted **NO**
- feedback-g02381-c02-b8a4cdacb2: portfolio gain **+0.0674** / signal **-0.0906** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
