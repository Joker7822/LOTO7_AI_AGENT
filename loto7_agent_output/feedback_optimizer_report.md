# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2452**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1231**
- incumbent signal objective: **-0.0428**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02452-c01-b8e1a99521: portfolio gain **-0.0616** / signal **-0.0724** / accepted **NO**
- feedback-g02452-c02-0dd763f97c: portfolio gain **+0.0726** / signal **-0.1486** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
