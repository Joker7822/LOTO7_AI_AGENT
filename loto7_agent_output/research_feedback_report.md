# Research Winner Full-History Replay Feedback

- generation: **600**
- provisional winner: **evo-g00600-c02-2a378dc085**
- incumbent research parent: **feedback-g00352-c01-eacacb380f**
- accepted research parent: **feedback-g00352-c01-eacacb380f**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0221 | 0.2297 |
| full score Δ vs random | -0.0167 | +0.2062 |
| 120 score Δ vs random | +0.0383 | +0.2383 |
| 60 score Δ vs random | +0.0530 | +0.3387 |
| 30 score Δ vs random | +0.0397 | +0.0640 |

- objective gain: **-0.2076**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
