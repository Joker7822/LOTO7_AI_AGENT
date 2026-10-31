# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5714**
- incumbent: **signal-g05705-c01-0b089f3f09**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0865**
- incumbent signal objective: **-0.0584**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05714-c01-8fa0f8362c: portfolio gain **-0.1082** / signal **-0.0936** / accepted **NO**
- feedback-g05714-c02-251f349e64: portfolio gain **-0.0986** / signal **-0.0899** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
