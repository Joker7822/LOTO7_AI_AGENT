# Research Winner Full-History Replay Feedback

- generation: **4755**
- provisional winner: **evo-g04755-c03-2d72dce3c9**
- incumbent research parent: **signal-g04747-c01-251fbf034b**
- accepted research parent: **signal-g04747-c01-251fbf034b**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0735 | 0.1244 |
| full score Δ vs random | +0.1185 | +0.0822 |
| 120 score Δ vs random | +0.0679 | +0.1576 |
| 60 score Δ vs random | +0.0459 | +0.2092 |
| 30 score Δ vs random | -0.0097 | -0.0133 |

- objective gain: **-0.0510**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
