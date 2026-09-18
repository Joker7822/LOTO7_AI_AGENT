# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3621**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1142**
- incumbent signal objective: **-0.0417**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03621-c01-5be838e3dc: portfolio gain **-0.0593** / signal **-0.0700** / accepted **NO**
- feedback-g03621-c02-fd710738bd: portfolio gain **-0.0419** / signal **-0.2979** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
