# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2252**
- incumbent: **signal-g02251-c01-14a223885f**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1112**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02252-c01-01bb942fa9: portfolio gain **+0.0536** / signal **-0.0578** / accepted **NO**
- feedback-g02252-c02-5daeb9072c: portfolio gain **-0.1696** / signal **-0.1245** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
