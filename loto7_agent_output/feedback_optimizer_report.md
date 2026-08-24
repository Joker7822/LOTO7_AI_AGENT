# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2246**
- incumbent: **signal-g02245-c01-7f12851754**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1233**
- incumbent signal objective: **-0.0486**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02246-c01-0fefcfd992: portfolio gain **-0.0470** / signal **-0.0741** / accepted **NO**
- feedback-g02246-c02-d0db768729: portfolio gain **+0.0136** / signal **-0.1054** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
