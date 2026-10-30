# Research Winner Full-History Replay Feedback

- generation: **5561**
- provisional winner: **evo-g05561-c04-d93d96db0e**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0621 | 0.0941 |
| full score Δ vs random | +0.0676 | +0.1367 |
| 120 score Δ vs random | +0.0652 | +0.1012 |
| 60 score Δ vs random | +0.0793 | +0.0825 |
| 30 score Δ vs random | -0.0023 | -0.0569 |

- objective gain: **-0.0319**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
