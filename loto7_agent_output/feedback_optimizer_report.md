# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4954**
- incumbent: **signal-g04789-c01-29ccf32ff6**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0225**
- incumbent signal objective: **-0.0453**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04954-c01-b1da654be3: portfolio gain **-0.0343** / signal **-0.0649** / accepted **NO**
- feedback-g04954-c02-02bd32f936: portfolio gain **+0.0837** / signal **-0.0738** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
