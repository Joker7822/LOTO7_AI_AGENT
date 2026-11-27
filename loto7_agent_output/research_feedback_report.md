# Research Winner Full-History Replay Feedback

- generation: **7039**
- provisional winner: **evo-g07039-c02-640a17c922**
- incumbent research parent: **signal-g06845-c01-6183c9b064**
- accepted research parent: **signal-g06845-c01-6183c9b064**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1088 | 0.2363 |
| full score Δ vs random | +0.0725 | +0.2117 |
| 120 score Δ vs random | +0.1127 | +0.1909 |
| 60 score Δ vs random | +0.1120 | +0.3039 |
| 30 score Δ vs random | +0.2154 | +0.3457 |

- objective gain: **-0.1275**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
