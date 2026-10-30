# Research Winner Full-History Replay Feedback

- generation: **5578**
- provisional winner: **evo-g05578-c02-ec2e0b3c08**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0534 | 0.0941 |
| full score Δ vs random | -0.0886 | +0.1367 |
| 120 score Δ vs random | -0.0697 | +0.1012 |
| 60 score Δ vs random | -0.0339 | +0.0825 |
| 30 score Δ vs random | +0.0874 | -0.0569 |

- objective gain: **-0.1475**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
