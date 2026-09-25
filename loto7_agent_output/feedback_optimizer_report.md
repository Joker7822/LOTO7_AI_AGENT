# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3839**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1219**
- incumbent signal objective: **-0.0419**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03839-c01-71a285c6d8: portfolio gain **-0.0550** / signal **-0.0562** / accepted **NO**
- feedback-g03839-c02-ab3a1ba0d5: portfolio gain **+0.1528** / signal **-0.1123** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
