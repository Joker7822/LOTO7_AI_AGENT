# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4564**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1004**
- incumbent signal objective: **-0.0423**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04564-c01-6598210815: portfolio gain **-0.0249** / signal **-0.0775** / accepted **NO**
- feedback-g04564-c02-451c9bde8b: portfolio gain **+0.0538** / signal **-0.4020** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
