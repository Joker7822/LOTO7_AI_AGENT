# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5104**
- incumbent: **signal-g04789-c01-29ccf32ff6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0130**
- incumbent signal objective: **-0.0458**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05104-c01-42feb13b23: portfolio gain **+0.1402** / signal **-0.0591** / accepted **NO**
- feedback-g05104-c02-4df25d0abe: portfolio gain **+0.0013** / signal **-0.4563** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
