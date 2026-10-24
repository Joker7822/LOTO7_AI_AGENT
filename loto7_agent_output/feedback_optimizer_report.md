# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5267**
- incumbent: **signal-g05266-c01-283b6daef6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1918**
- incumbent signal objective: **-0.0408**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05267-c01-09efc04f9b: portfolio gain **+0.0079** / signal **-0.0619** / accepted **NO**
- feedback-g05267-c02-64c9440598: portfolio gain **-0.1188** / signal **-0.1006** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
