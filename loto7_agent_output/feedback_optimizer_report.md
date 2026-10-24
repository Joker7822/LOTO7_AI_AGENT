# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5265**
- incumbent: **signal-g05264-c01-6a58441932**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0825**
- incumbent signal objective: **-0.0853**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05265-c01-ed504d0dd3: portfolio gain **+0.0351** / signal **-0.0847** / accepted **NO**
- feedback-g05265-c02-9744041ee9: portfolio gain **-0.0232** / signal **-0.1026** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
