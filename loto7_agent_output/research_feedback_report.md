# Research Winner Full-History Replay Feedback

- generation: **4787**
- provisional winner: **evo-g04787-c01-ccf22768a2**
- incumbent research parent: **signal-g04747-c01-251fbf034b**
- accepted research parent: **signal-g04747-c01-251fbf034b**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1214 | 0.1244 |
| full score Δ vs random | +0.1515 | +0.0822 |
| 120 score Δ vs random | +0.0725 | +0.1576 |
| 60 score Δ vs random | +0.0595 | +0.2092 |
| 30 score Δ vs random | +0.3107 | -0.0133 |

- objective gain: **-0.0031**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
