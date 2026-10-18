# Research Winner Full-History Replay Feedback

- generation: **5086**
- provisional winner: **evo-g05086-c01-957602d478**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0172 | 0.0225 |
| full score Δ vs random | +0.0311 | +0.1330 |
| 120 score Δ vs random | +0.0572 | +0.0389 |
| 60 score Δ vs random | -0.0781 | +0.0014 |
| 30 score Δ vs random | +0.0187 | -0.3797 |

- objective gain: **-0.0053**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
