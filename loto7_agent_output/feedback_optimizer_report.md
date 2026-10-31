# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5695**
- incumbent: **signal-g05690-c01-7b9859bf53**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.0772**
- incumbent signal objective: **-0.0453**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05695-c01-b6f7683ae9: portfolio gain **+0.1092** / signal **-0.1090** / accepted **NO**
- feedback-g05695-c02-3501577f9d: portfolio gain **+0.0892** / signal **-0.2471** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
