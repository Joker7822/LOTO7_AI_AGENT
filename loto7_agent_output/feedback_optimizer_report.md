# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5712**
- incumbent: **signal-g05705-c01-0b089f3f09**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0865**
- incumbent signal objective: **-0.0584**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05712-c01-162db8ca49: portfolio gain **-0.0433** / signal **-0.0709** / accepted **NO**
- feedback-g05712-c02-05131cb1f6: portfolio gain **-0.1419** / signal **-0.1594** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
