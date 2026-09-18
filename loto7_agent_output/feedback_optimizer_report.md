# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3781**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1142**
- incumbent signal objective: **-0.0417**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03781-c01-1eaf91a84e: portfolio gain **-0.0581** / signal **-0.0622** / accepted **NO**
- feedback-g03781-c02-43a812b920: portfolio gain **+0.0864** / signal **-0.1349** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
