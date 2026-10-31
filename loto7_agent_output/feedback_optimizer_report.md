# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5718**
- incumbent: **signal-g05715-c01-c0723748df**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2197**
- incumbent signal objective: **-0.0517**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05718-c01-854a3d7132: portfolio gain **-0.2523** / signal **-0.0957** / accepted **NO**
- feedback-g05718-c02-a0cdcd5f95: portfolio gain **-0.2389** / signal **-0.2233** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
