# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5175**
- incumbent: **signal-g05173-c02-2ea7248cef**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2134**
- incumbent signal objective: **-0.0486**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05175-c01-4a664ff650: portfolio gain **-0.2104** / signal **-0.0621** / accepted **NO**
- feedback-g05175-c02-10a625c4eb: portfolio gain **-0.3064** / signal **-0.3830** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
