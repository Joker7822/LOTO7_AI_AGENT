# Research Winner Full-History Replay Feedback

- generation: **5192**
- provisional winner: **evo-g05192-c01-2738387d90**
- incumbent research parent: **signal-g05175-c01-33535f4f52**
- accepted research parent: **signal-g05175-c01-33535f4f52**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0969 | 0.1252 |
| full score Δ vs random | +0.0613 | +0.1251 |
| 120 score Δ vs random | +0.1262 | +0.1245 |
| 60 score Δ vs random | +0.0441 | +0.0889 |
| 30 score Δ vs random | +0.2245 | +0.2002 |

- objective gain: **-0.0283**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
