# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5717**
- incumbent: **signal-g05715-c01-c0723748df**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2197**
- incumbent signal objective: **-0.0517**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05717-c01-8ed5e1aedd: portfolio gain **-0.1719** / signal **-0.0727** / accepted **NO**
- feedback-g05717-c02-42f30226da: portfolio gain **-0.0895** / signal **-0.2472** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
