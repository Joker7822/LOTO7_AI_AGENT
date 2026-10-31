# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5687**
- incumbent: **signal-g05627-c01-1e9e34f825**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.0483**
- incumbent signal objective: **-0.0461**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05687-c01-45d486de2f: portfolio gain **+0.1591** / signal **-0.0623** / accepted **NO**
- feedback-g05687-c02-ed36c0fe13: portfolio gain **+0.0477** / signal **-0.0758** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
