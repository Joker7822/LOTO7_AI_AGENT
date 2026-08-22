# Research Winner Full-History Replay Feedback

- generation: **291**
- provisional winner: **evo-g00128-c02-76142c54cc**
- incumbent research parent: **baseline-5fdb8dc2ad**
- accepted research parent: **evo-g00128-c02-76142c54cc**
- candidate accepted: **YES**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0672 | -0.2150 |
| full score Δ vs random | -0.0437 | -0.2072 |
| 120 score Δ vs random | -0.0408 | -0.1925 |
| 60 score Δ vs random | -0.0337 | -0.1690 |
| 30 score Δ vs random | -0.3087 | -0.4130 |

- objective gain: **+0.1478**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
