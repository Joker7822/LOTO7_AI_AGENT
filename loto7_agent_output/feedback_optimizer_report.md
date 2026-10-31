# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5625**
- incumbent: **signal-g05622-c02-44c2d7a3af**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1152**
- incumbent signal objective: **-0.0697**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05625-c01-d674c947eb: portfolio gain **-0.0220** / signal **-0.0675** / accepted **NO**
- feedback-g05625-c02-a3a108a419: portfolio gain **-0.2143** / signal **-0.4010** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
