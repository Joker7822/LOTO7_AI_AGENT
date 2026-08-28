# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2698**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1203**
- incumbent signal objective: **-0.0427**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02698-c01-4b841d3a2f: portfolio gain **-0.0091** / signal **-0.0593** / accepted **NO**
- feedback-g02698-c02-5631f59917: portfolio gain **+0.1264** / signal **-0.0887** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
