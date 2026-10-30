# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5544**
- incumbent: **signal-g05281-c01-55a70e0b94**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0941**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05544-c01-89bfbf7937: portfolio gain **+0.0175** / signal **-0.0646** / accepted **NO**
- feedback-g05544-c02-1846b84784: portfolio gain **-0.1421** / signal **-0.1654** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
