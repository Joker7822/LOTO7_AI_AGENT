# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5156**
- incumbent: **signal-g05155-c01-b7bf1ffa1e**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2341**
- incumbent signal objective: **-0.0457**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05156-c01-4321d1845e: portfolio gain **-0.1541** / signal **-0.1183** / accepted **NO**
- feedback-g05156-c02-f023edbd36: portfolio gain **-0.2923** / signal **-0.4433** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
