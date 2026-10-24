# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5269**
- incumbent: **signal-g05266-c01-283b6daef6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1505**
- incumbent signal objective: **-0.0465**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05269-c01-2688a277ca: portfolio gain **-0.1189** / signal **-0.0572** / accepted **NO**
- feedback-g05269-c02-ce46f3face: portfolio gain **-0.1158** / signal **-0.2350** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
