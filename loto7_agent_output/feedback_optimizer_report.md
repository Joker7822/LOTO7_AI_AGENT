# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5125**
- incumbent: **evo-g05124-c01-18b0716cd5**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1578**
- incumbent signal objective: **-0.1124**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05125-c01-a0074fbde1: portfolio gain **-0.1343** / signal **-0.1002** / accepted **NO**
- feedback-g05125-c02-29cb309bcf: portfolio gain **-0.0035** / signal **-0.1455** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
