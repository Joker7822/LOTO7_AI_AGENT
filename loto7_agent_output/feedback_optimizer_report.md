# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5621**
- incumbent: **evo-g05619-c03-804ed4076c**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1419**
- incumbent signal objective: **-0.1131**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05621-c01-52e158742d: portfolio gain **-0.1842** / signal **-0.1123** / accepted **NO**
- feedback-g05621-c02-b643cc726b: portfolio gain **-0.0240** / signal **-0.1242** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
