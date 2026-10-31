# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5779**
- incumbent: **signal-g05751-c01-b251534c9e**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0564**
- incumbent signal objective: **-0.0467**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05779-c01-bc12fb081f: portfolio gain **-0.0566** / signal **-0.1086** / accepted **NO**
- feedback-g05779-c02-ae96c188c9: portfolio gain **+0.1130** / signal **-0.1415** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
