# Research Winner Full-History Replay Feedback

- generation: **7122**
- provisional winner: **evo-g07122-c01-95ab04417a**
- incumbent research parent: **signal-g06845-c01-6183c9b064**
- accepted research parent: **signal-g06845-c01-6183c9b064**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1364 | 0.2363 |
| full score Δ vs random | +0.0931 | +0.2117 |
| 120 score Δ vs random | +0.2546 | +0.1909 |
| 60 score Δ vs random | +0.0935 | +0.3039 |
| 30 score Δ vs random | -0.0406 | +0.3457 |

- objective gain: **-0.0999**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
