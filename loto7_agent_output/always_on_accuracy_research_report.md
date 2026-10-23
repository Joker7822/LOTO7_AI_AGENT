# Always-on Accuracy Research — bounded hourly activities

- Last executed: **2026-10-23T16:35:51+09:00**
- Completed audit cycles: **16**
- This cycle: **generalization** / 過去モデル比較・多重比較を点検
- Network discovery: **not_scheduled**
- Trusted draw latest: **699**, two-source: **False**
- Research guard: **WAIT_FOR_NEW_DATA**, same-data trials: **768/800**
- Future actuals: portfolio 7/26, v2 0, fifth-expert 0

## Completed evidence review
- 独立2ソース未照合。未信頼結果で将来予測を採点しない。
- 探索予算ガードがWAIT_FOR_NEW_DATA。既存データの無制限再探索は禁止。
- 真正Future-OOSの実測がまだ不足。改善を断定しない。
- 過去の4/5モデル比較は探索済み。独立した未来結果なしに選別・昇格しない。

## Online research leads (unreviewed; do NOT deploy as algorithms)
- [Merging sequential e-values via martingales](https://doi.org/10.1214/24-ejs2228) (2024) — UNREVIEWED
- [Sequential Monte Carlo testing by betting](https://doi.org/10.1093/jrsssb/qkaf014) (2025) — UNREVIEWED
- [Mimic Martingales in Sequential Auctions](https://doi.org/10.2139/ssrn.4689006) (2024) — UNREVIEWED
- [Betting against the Field:&amp;nbsp;Optimal Elimination in Sequential Model Confidence Sets](https://doi.org/10.2139/ssrn.7599398) (2026) — UNREVIEWED
- [Prequential posteriors](https://doi.org/10.1007/s42081-026-00374-w) (2026) — UNREVIEWED
- [Prequential Benchmark of Limit Order Book Mid-Price Movement Prediction Models](https://doi.org/10.2139/ssrn.7273201) (2026) — UNREVIEWED
- [Prequential Streaming Evaluation of Stateful Time-Series Forecasters with Online Conformal Calibration](https://doi.org/10.5281/zenodo.21508920) (2026) — UNREVIEWED
- [In-context learning, data ordering, and active sensing : a prequential perspective](https://doi.org/10.71781/36115) (2026) — UNREVIEWED
- [Enforcing tail calibration when training probabilistic forecast models](https://doi.org/10.1016/j.ijforecast.2026.04.009) (2026) — UNREVIEWED
- [PBIE Pro: A Hybrid Probabilistic Decision Framework Integrating Bayesian Inference, Scenario Simulation, and Calibration-Aware Intuition for Robust Forecasting Under Data Scarcity](https://doi.org/10.2139/ssrn.6617378) (2026) — UNREVIEWED
- [Investigating Calibration Challenges in Probabilistic Electricity Price Forecasting](https://doi.org/10.1145/3765611.3815392) (2026) — UNREVIEWED
- [Transformer-Based Probabilistic Demand Forecasting with Adaptive Online Learning](https://doi.org/10.2139/ssrn.4896166) (2024) — UNREVIEWED

Every scheduled cycle has a bounded evidence-check activity.
Network errors are visible. An unattended hourly job is not guaranteed to
run at an exact time. More compute or papers do NOT guarantee a lottery edge.
No optimizer, draw data, Production, Champion or preregistered OOS is changed.
