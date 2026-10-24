# Research Winner Full-History Replay Feedback

- generation: **5270**
- provisional winner: **evo-g05270-c01-401b353c41**
- incumbent research parent: **signal-g05266-c01-283b6daef6**
- accepted research parent: **signal-g05266-c01-283b6daef6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0761 | 0.1505 |
| full score Δ vs random | +0.0633 | +0.1570 |
| 120 score Δ vs random | +0.0931 | +0.2117 |
| 60 score Δ vs random | +0.0868 | +0.0659 |
| 30 score Δ vs random | +0.0402 | +0.0825 |

- objective gain: **-0.0744**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
