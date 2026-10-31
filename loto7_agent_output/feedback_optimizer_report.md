# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5700**
- incumbent: **signal-g05698-c02-10c0dbd440**
- trials: **2**
- accepted: **feedback-g05700-c01-fc56ff7da8**
- incumbent portfolio objective: **+0.0683**
- incumbent signal objective: **-0.0894**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05700-c01-fc56ff7da8: portfolio gain **+0.0527** / signal **-0.0716** / accepted **YES**
- feedback-g05700-c02-4c5c788ce0: portfolio gain **-0.2032** / signal **-0.5432** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
