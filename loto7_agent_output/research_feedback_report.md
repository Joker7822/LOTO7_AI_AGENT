# Research Winner Full-History Replay Feedback

- generation: **5146**
- provisional winner: **evo-g05146-c03-10189a4cac**
- incumbent research parent: **signal-g05132-c01-d09ac468ef**
- accepted research parent: **signal-g05132-c01-d09ac468ef**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0682 | 0.1635 |
| full score Δ vs random | +0.0986 | +0.0967 |
| 120 score Δ vs random | +0.1532 | +0.2614 |
| 60 score Δ vs random | -0.0111 | +0.1713 |
| 30 score Δ vs random | -0.1768 | +0.0392 |

- objective gain: **-0.0953**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
