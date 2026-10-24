# Research Winner Full-History Replay Feedback

- generation: **5183**
- provisional winner: **evo-g05183-c01-1b0fa20db3**
- incumbent research parent: **signal-g05175-c01-33535f4f52**
- accepted research parent: **signal-g05175-c01-33535f4f52**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0064 | 0.1252 |
| full score Δ vs random | +0.0655 | +0.1251 |
| 120 score Δ vs random | -0.0328 | +0.1245 |
| 60 score Δ vs random | -0.0129 | +0.0889 |
| 30 score Δ vs random | -0.0248 | +0.2002 |

- objective gain: **-0.1188**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
