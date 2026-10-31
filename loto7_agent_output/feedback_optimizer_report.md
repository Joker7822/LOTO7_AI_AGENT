# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5596**
- incumbent: **signal-g05281-c01-55a70e0b94**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0941**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05596-c01-20a99d7ef0: portfolio gain **+0.0582** / signal **-0.0574** / accepted **NO**
- feedback-g05596-c02-f948a3a33f: portfolio gain **-0.3519** / signal **-0.6390** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
