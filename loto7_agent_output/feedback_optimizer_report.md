# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5096**
- incumbent: **signal-g04789-c01-29ccf32ff6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0130**
- incumbent signal objective: **-0.0458**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05096-c01-e45b971968: portfolio gain **+0.0831** / signal **-0.0566** / accepted **NO**
- feedback-g05096-c02-db64285360: portfolio gain **-0.1314** / signal **-0.2611** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
