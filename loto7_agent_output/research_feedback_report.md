# Research Winner Full-History Replay Feedback

- generation: **5585**
- provisional winner: **evo-g05585-c02-6d412ac6c6**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0070 | 0.0941 |
| full score Δ vs random | -0.0114 | +0.1367 |
| 120 score Δ vs random | +0.0178 | +0.1012 |
| 60 score Δ vs random | +0.0683 | +0.0825 |
| 30 score Δ vs random | -0.0893 | -0.0569 |

- objective gain: **-0.0871**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
