# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4922**
- incumbent: **signal-g04789-c01-29ccf32ff6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0225**
- incumbent signal objective: **-0.0453**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04922-c01-d3b775682e: portfolio gain **-0.0414** / signal **-0.1100** / accepted **NO**
- feedback-g04922-c02-4557688491: portfolio gain **+0.0308** / signal **-0.1801** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
