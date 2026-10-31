# Research Winner Full-History Replay Feedback

- generation: **5803**
- provisional winner: **evo-g05803-c04-fc429e7723**
- incumbent research parent: **signal-g05799-c01-52cad64a80**
- accepted research parent: **signal-g05799-c01-52cad64a80**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0213 | 0.0955 |
| full score Δ vs random | +0.0206 | +0.0911 |
| 120 score Δ vs random | +0.0365 | +0.1101 |
| 60 score Δ vs random | -0.0287 | +0.0795 |
| 30 score Δ vs random | +0.0704 | +0.0921 |

- objective gain: **-0.0742**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
