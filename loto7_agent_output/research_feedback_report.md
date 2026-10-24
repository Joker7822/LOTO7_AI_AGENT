# Research Winner Full-History Replay Feedback

- generation: **5172**
- provisional winner: **evo-g05172-c03-5dd81eb2d7**
- incumbent research parent: **signal-g05169-c01-535d7241c2**
- accepted research parent: **signal-g05169-c01-535d7241c2**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0888 | 0.0759 |
| full score Δ vs random | +0.0701 | +0.0729 |
| 120 score Δ vs random | +0.1479 | +0.1125 |
| 60 score Δ vs random | -0.0089 | +0.0146 |
| 30 score Δ vs random | +0.1435 | +0.0812 |

- objective gain: **+0.0129**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
