# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3879**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1219**
- incumbent signal objective: **-0.0419**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03879-c01-459347ac42: portfolio gain **-0.0990** / signal **-0.0750** / accepted **NO**
- feedback-g03879-c02-249adfb3ac: portfolio gain **+0.1025** / signal **-0.2841** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
