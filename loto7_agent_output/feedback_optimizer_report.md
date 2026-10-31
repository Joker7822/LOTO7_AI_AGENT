# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5683**
- incumbent: **signal-g05627-c01-1e9e34f825**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.0483**
- incumbent signal objective: **-0.0461**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05683-c01-6b11c2fc65: portfolio gain **+0.2456** / signal **-0.0563** / accepted **NO**
- feedback-g05683-c02-50403b843d: portfolio gain **-0.0046** / signal **-0.2945** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
