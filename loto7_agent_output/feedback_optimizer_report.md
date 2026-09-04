# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2929**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1157**
- incumbent signal objective: **-0.0420**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02929-c01-f053b2cd8b: portfolio gain **-0.0268** / signal **-0.0567** / accepted **NO**
- feedback-g02929-c02-3de26d818a: portfolio gain **+0.2132** / signal **-0.0634** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
