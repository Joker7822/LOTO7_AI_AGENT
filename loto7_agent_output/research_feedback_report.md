# Research Winner Full-History Replay Feedback

- generation: **5582**
- provisional winner: **evo-g05582-c02-55dee9e34d**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0052 | 0.0941 |
| full score Δ vs random | +0.0102 | +0.1367 |
| 120 score Δ vs random | +0.0827 | +0.1012 |
| 60 score Δ vs random | -0.0882 | +0.0825 |
| 30 score Δ vs random | -0.0963 | -0.0569 |

- objective gain: **-0.0888**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
