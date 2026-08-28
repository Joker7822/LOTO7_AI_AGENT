# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2748**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1203**
- incumbent signal objective: **-0.0427**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02748-c01-557289b420: portfolio gain **-0.0205** / signal **-0.0578** / accepted **NO**
- feedback-g02748-c02-d729bfa8ec: portfolio gain **+0.2416** / signal **-0.2530** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
