# Research Winner Full-History Replay Feedback

- generation: **5722**
- provisional winner: **evo-g05722-c03-39040a424f**
- incumbent research parent: **signal-g05721-c01-dcdb0d5ee1**
- accepted research parent: **signal-g05721-c01-dcdb0d5ee1**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0164 | 0.1249 |
| full score Δ vs random | +0.0355 | +0.1374 |
| 120 score Δ vs random | +0.0355 | +0.0966 |
| 60 score Δ vs random | -0.0597 | +0.0701 |
| 30 score Δ vs random | +0.0347 | +0.2891 |

- objective gain: **-0.1085**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
