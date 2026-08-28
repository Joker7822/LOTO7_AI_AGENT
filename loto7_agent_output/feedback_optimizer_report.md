# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2878**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1203**
- incumbent signal objective: **-0.0427**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02878-c01-2091f49b7a: portfolio gain **-0.0754** / signal **-0.0665** / accepted **NO**
- feedback-g02878-c02-1cdc28b6d0: portfolio gain **+0.0559** / signal **-0.2006** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
