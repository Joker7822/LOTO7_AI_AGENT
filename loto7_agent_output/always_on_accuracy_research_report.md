# Always-on Accuracy Research — bounded hourly activities

- Last executed: **2026-10-24T07:14:14+09:00**
- Completed audit cycles: **19**
- This cycle: **literature_search** / インターネットから最新の研究論文を検索
- Network discovery: **searched**
- Trusted draw latest: **699**, two-source: **False**
- Research guard: **WAIT_FOR_NEW_DATA**, same-data trials: **768/800**
- Future actuals: portfolio 7/26, v2 0, fifth-expert 0

## Completed evidence review
- 独立2ソース未照合。未信頼結果で将来予測を採点しない。
- 探索予算ガードがWAIT_FOR_NEW_DATA。既存データの無制限再探索は禁止。
- 真正Future-OOSの実測がまだ不足。改善を断定しない。
- オンライン論文の検索結果は未査読・未検証の研究候補であり、コードを自動採用しない。
- オンライン検索: searched / 新規候補 4件

## Online research leads (unreviewed; do NOT deploy as algorithms)
- [A note on adaptive conformal prediction for time series with structural breaks](https://doi.org/10.2139/ssrn.5946791) (2025) — UNREVIEWED
- [conformalForecast: Conformal Prediction Methods for Multistep-Ahead Time Series Forecasting](https://doi.org/10.32614/cran.package.conformalforecast) (2025) — UNREVIEWED
- [RL-ConFormer: Reinforcement Learning-Enhanced Conformal Prediction with Transformer-Based Hybrid Forecasting for Multi-Horizon Time Series](https://doi.org/10.2139/ssrn.6263102) (2026) — UNREVIEWED
- [Bias corrections and prediction intervals for time-series measurements with fouling and calibration drift](https://doi.org/10.5194/egusphere-2026-4028) (2026) — UNREVIEWED
- [Merging sequential e-values via martingales](https://doi.org/10.1214/24-ejs2228) (2024) — UNREVIEWED
- [Sequential Monte Carlo testing by betting](https://doi.org/10.1093/jrsssb/qkaf014) (2025) — UNREVIEWED
- [Mimic Martingales in Sequential Auctions](https://doi.org/10.2139/ssrn.4689006) (2024) — UNREVIEWED
- [Betting against the Field:&amp;nbsp;Optimal Elimination in Sequential Model Confidence Sets](https://doi.org/10.2139/ssrn.7599398) (2026) — UNREVIEWED
- [Prequential posteriors](https://doi.org/10.1007/s42081-026-00374-w) (2026) — UNREVIEWED
- [Prequential Benchmark of Limit Order Book Mid-Price Movement Prediction Models](https://doi.org/10.2139/ssrn.7273201) (2026) — UNREVIEWED
- [Prequential Streaming Evaluation of Stateful Time-Series Forecasters with Online Conformal Calibration](https://doi.org/10.5281/zenodo.21508920) (2026) — UNREVIEWED
- [In-context learning, data ordering, and active sensing : a prequential perspective](https://doi.org/10.71781/36115) (2026) — UNREVIEWED

Every scheduled cycle has a bounded evidence-check activity.
Network errors are visible. An unattended hourly job is not guaranteed to
run at an exact time. More compute or papers do NOT guarantee a lottery edge.
No optimizer, draw data, Production, Champion or preregistered OOS is changed.
