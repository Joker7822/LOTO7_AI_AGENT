# Research Winner Full-History Replay Feedback

- generation: **5579**
- provisional winner: **evo-g05579-c03-1b09f83fbb**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0706 | 0.0941 |
| full score Δ vs random | -0.0063 | +0.1367 |
| 120 score Δ vs random | -0.0948 | +0.1012 |
| 60 score Δ vs random | -0.0987 | +0.0825 |
| 30 score Δ vs random | -0.1543 | -0.0569 |

- objective gain: **-0.1646**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
