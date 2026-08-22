# Research Winner Full-History Replay Feedback

- generation: **440**
- provisional winner: **evo-g00440-c04-5769edf8e5**
- incumbent research parent: **feedback-g00352-c01-eacacb380f**
- accepted research parent: **feedback-g00352-c01-eacacb380f**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0333 | 0.2297 |
| full score Δ vs random | +0.0737 | +0.2062 |
| 120 score Δ vs random | +0.0323 | +0.2383 |
| 60 score Δ vs random | +0.0818 | +0.3387 |
| 30 score Δ vs random | -0.2017 | +0.0640 |

- objective gain: **-0.1964**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
