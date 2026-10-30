# Research Winner Full-History Replay Feedback

- generation: **5539**
- provisional winner: **evo-g05539-c01-a16c0d8c38**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0412 | 0.0941 |
| full score Δ vs random | +0.0163 | +0.1367 |
| 120 score Δ vs random | -0.0064 | +0.1012 |
| 60 score Δ vs random | +0.0851 | +0.0825 |
| 30 score Δ vs random | +0.2074 | -0.0569 |

- objective gain: **-0.0528**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
