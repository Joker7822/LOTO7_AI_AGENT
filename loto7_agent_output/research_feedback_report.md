# Research Winner Full-History Replay Feedback

- generation: **5627**
- provisional winner: **evo-g05627-c04-514233ce01**
- incumbent research parent: **signal-g05626-c01-b6ee2714ac**
- accepted research parent: **signal-g05626-c01-b6ee2714ac**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0756 | 0.0394 |
| full score Δ vs random | +0.0543 | +0.1493 |
| 120 score Δ vs random | +0.1355 | +0.0528 |
| 60 score Δ vs random | +0.0415 | -0.1359 |
| 30 score Δ vs random | +0.0081 | -0.0419 |

- objective gain: **+0.0362**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
