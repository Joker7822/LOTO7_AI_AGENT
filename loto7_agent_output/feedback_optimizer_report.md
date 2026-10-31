# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5622**
- incumbent: **signal-g05621-c02-744d8fb83f**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1181**
- incumbent signal objective: **-0.0710**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05622-c01-863f76aa1b: portfolio gain **-0.0819** / signal **-0.0899** / accepted **NO**
- feedback-g05622-c02-b3d3742d53: portfolio gain **+0.1071** / signal **-0.0840** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
