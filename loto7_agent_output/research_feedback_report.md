# Research Winner Full-History Replay Feedback

- generation: **5619**
- provisional winner: **evo-g05619-c03-804ed4076c**
- incumbent research parent: **signal-g05618-c01-7d2976e19d**
- accepted research parent: **evo-g05619-c03-804ed4076c**
- candidate accepted: **YES**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1419 | -0.0556 |
| full score Δ vs random | +0.0899 | -0.0230 |
| 120 score Δ vs random | +0.1370 | -0.0757 |
| 60 score Δ vs random | +0.2045 | -0.1094 |
| 30 score Δ vs random | +0.2161 | +0.0084 |

- objective gain: **+0.1975**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
