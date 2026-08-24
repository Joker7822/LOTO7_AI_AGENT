# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2453**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1231**
- incumbent signal objective: **-0.0428**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02453-c01-17ba2f1a93: portfolio gain **-0.0709** / signal **-0.0584** / accepted **NO**
- feedback-g02453-c02-0f9a846a5f: portfolio gain **+0.1082** / signal **-0.2171** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
