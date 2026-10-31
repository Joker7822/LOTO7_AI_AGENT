# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5721**
- incumbent: **signal-g05715-c01-c0723748df**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2197**
- incumbent signal objective: **-0.0517**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05721-c01-b78b3449f9: portfolio gain **-0.0751** / signal **-0.0802** / accepted **NO**
- feedback-g05721-c02-1f9528475b: portfolio gain **-0.1555** / signal **-0.2847** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
