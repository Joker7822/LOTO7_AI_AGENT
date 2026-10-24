# Research Winner Full-History Replay Feedback

- generation: **5173**
- provisional winner: **evo-g05173-c04-0f3528c193**
- incumbent research parent: **signal-g05169-c01-535d7241c2**
- accepted research parent: **evo-g05173-c04-0f3528c193**
- candidate accepted: **YES**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1425 | 0.0759 |
| full score Δ vs random | +0.0994 | +0.0729 |
| 120 score Δ vs random | +0.2119 | +0.1125 |
| 60 score Δ vs random | +0.1639 | +0.0146 |
| 30 score Δ vs random | +0.0078 | +0.0812 |

- objective gain: **+0.0666**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
