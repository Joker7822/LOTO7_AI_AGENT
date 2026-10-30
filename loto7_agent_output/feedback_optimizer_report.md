# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5571**
- incumbent: **signal-g05281-c01-55a70e0b94**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0941**
- incumbent signal objective: **-0.0450**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05571-c01-c8120b949b: portfolio gain **-0.1383** / signal **-0.0601** / accepted **NO**
- feedback-g05571-c02-d18e31b5b0: portfolio gain **-0.0977** / signal **-0.0748** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
