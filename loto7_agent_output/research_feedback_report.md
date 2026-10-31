# Research Winner Full-History Replay Feedback

- generation: **5737**
- provisional winner: **evo-g05737-c04-e80a61a4fb**
- incumbent research parent: **signal-g05721-c01-dcdb0d5ee1**
- accepted research parent: **signal-g05721-c01-dcdb0d5ee1**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0065 | 0.1249 |
| full score Δ vs random | -0.0032 | +0.1374 |
| 120 score Δ vs random | +0.0825 | +0.0966 |
| 60 score Δ vs random | -0.0434 | +0.0701 |
| 30 score Δ vs random | -0.1263 | +0.2891 |

- objective gain: **-0.1184**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
