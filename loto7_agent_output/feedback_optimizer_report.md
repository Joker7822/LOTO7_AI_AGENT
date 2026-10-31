# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5624**
- incumbent: **signal-g05622-c02-44c2d7a3af**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1152**
- incumbent signal objective: **-0.0697**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05624-c01-5911c98046: portfolio gain **-0.0785** / signal **-0.0792** / accepted **NO**
- feedback-g05624-c02-049888a102: portfolio gain **-0.0958** / signal **-0.1512** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
