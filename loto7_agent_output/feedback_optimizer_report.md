# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5562**
- incumbent: **signal-g05281-c01-55a70e0b94**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0941**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05562-c01-e02c6c7a8f: portfolio gain **-0.1176** / signal **-0.0590** / accepted **NO**
- feedback-g05562-c02-3424a28c10: portfolio gain **-0.1277** / signal **-0.0935** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
