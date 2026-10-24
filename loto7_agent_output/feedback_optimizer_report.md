# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5272**
- incumbent: **signal-g05266-c01-283b6daef6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1505**
- incumbent signal objective: **-0.0465**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05272-c01-bf468f0f47: portfolio gain **-0.0882** / signal **-0.0595** / accepted **NO**
- feedback-g05272-c02-5a8bf8e004: portfolio gain **-0.1615** / signal **-0.1678** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
