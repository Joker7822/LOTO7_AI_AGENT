# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5385**
- incumbent: **signal-g05281-c01-55a70e0b94**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1142**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05385-c01-89258f1bc9: portfolio gain **-0.1899** / signal **-0.0567** / accepted **NO**
- feedback-g05385-c02-0b9e36c8e3: portfolio gain **+0.0466** / signal **-0.2372** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
