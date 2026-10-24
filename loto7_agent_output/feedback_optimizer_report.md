# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5180**
- incumbent: **signal-g05175-c01-33535f4f52**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1252**
- incumbent signal objective: **-0.0430**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05180-c01-929f4f6a62: portfolio gain **-0.0925** / signal **-0.0576** / accepted **NO**
- feedback-g05180-c02-2688ed287d: portfolio gain **+0.0040** / signal **-0.1743** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
