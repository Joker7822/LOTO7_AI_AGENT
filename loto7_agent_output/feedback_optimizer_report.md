# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4748**
- incumbent: **signal-g04747-c01-251fbf034b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1838**
- incumbent signal objective: **-0.0363**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04748-c01-20bb34dd09: portfolio gain **+0.0340** / signal **-0.0563** / accepted **NO**
- feedback-g04748-c02-ac7837c844: portfolio gain **-0.0651** / signal **-0.2122** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
