# Research Winner Full-History Replay Feedback

- generation: **311**
- provisional winner: **evo-g00311-c03-9701b20340**
- incumbent research parent: **feedback-g00308-c01-662d478c2c**
- accepted research parent: **feedback-g00308-c01-662d478c2c**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0153 | 0.1023 |
| full score Δ vs random | +0.0177 | +0.1565 |
| 120 score Δ vs random | -0.0180 | +0.0661 |
| 60 score Δ vs random | +0.0075 | +0.1760 |
| 30 score Δ vs random | -0.1673 | -0.1080 |

- objective gain: **-0.1177**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
