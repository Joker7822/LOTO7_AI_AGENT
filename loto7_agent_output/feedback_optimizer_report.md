# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3501**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1413**
- incumbent signal objective: **-0.0428**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03501-c01-cfb8c9a0f4: portfolio gain **+0.0411** / signal **-0.0664** / accepted **NO**
- feedback-g03501-c02-f5a01dd259: portfolio gain **+0.0922** / signal **-0.3849** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
