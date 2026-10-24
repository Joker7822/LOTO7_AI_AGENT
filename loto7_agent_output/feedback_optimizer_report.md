# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5278**
- incumbent: **signal-g05276-c01-af711eb9cb**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0915**
- incumbent signal objective: **-0.0453**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05278-c01-ce1b3ec3bf: portfolio gain **+0.1623** / signal **-0.0605** / accepted **NO**
- feedback-g05278-c02-53f654551d: portfolio gain **-0.1636** / signal **-0.1775** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
