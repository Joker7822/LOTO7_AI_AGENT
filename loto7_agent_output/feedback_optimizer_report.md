# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5172**
- incumbent: **signal-g05169-c01-535d7241c2**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0759**
- incumbent signal objective: **-0.0484**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05172-c01-381db24312: portfolio gain **-0.1154** / signal **-0.0678** / accepted **NO**
- feedback-g05172-c02-51b7329f3e: portfolio gain **-0.0666** / signal **-0.1379** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
