# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5266**
- incumbent: **signal-g05265-c01-a0ff2fc272**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1656**
- incumbent signal objective: **-0.0662**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05266-c01-70ead89381: portfolio gain **-0.1620** / signal **-0.1010** / accepted **NO**
- feedback-g05266-c02-87ebfcff17: portfolio gain **-0.2073** / signal **-0.1529** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
