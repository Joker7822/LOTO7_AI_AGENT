# Always-on Accuracy Research — bounded hourly activities

- Last executed: **2026-10-22T03:41:13+09:00**
- Completed audit cycles: **6**
- This cycle: **budget_and_plan** / 試行予算を守り次の検証を計画
- Network discovery: **not_scheduled**
- Trusted draw latest: **699**, two-source: **False**
- Research guard: **WAIT_FOR_NEW_DATA**, same-data trials: **768/800**
- Future actuals: portfolio 7/26, v2 0, fifth-expert 0

## Completed evidence review
- 独立2ソース未照合。未信頼結果で将来予測を採点しない。
- 探索予算ガードがWAIT_FOR_NEW_DATA。既存データの無制限再探索は禁止。
- 真正Future-OOSの実測がまだ不足。改善を断定しない。
- 同一履歴の新規試行予算 768/800

## Online research leads (unreviewed; do NOT deploy as algorithms)
- [Enforcing tail calibration when training probabilistic forecast models](https://doi.org/10.1016/j.ijforecast.2026.04.009) (2026) — UNREVIEWED
- [PBIE Pro: A Hybrid Probabilistic Decision Framework Integrating Bayesian Inference, Scenario Simulation, and Calibration-Aware Intuition for Robust Forecasting Under Data Scarcity](https://doi.org/10.2139/ssrn.6617378) (2026) — UNREVIEWED
- [Investigating Calibration Challenges in Probabilistic Electricity Price Forecasting](https://doi.org/10.1145/3765611.3815392) (2026) — UNREVIEWED
- [Transformer-Based Probabilistic Demand Forecasting with Adaptive Online Learning](https://doi.org/10.2139/ssrn.4896166) (2024) — UNREVIEWED

Every scheduled cycle has a bounded evidence-check activity.
Network errors are visible. An unattended hourly job is not guaranteed to
run at an exact time. More compute or papers do NOT guarantee a lottery edge.
No optimizer, draw data, Production, Champion or preregistered OOS is changed.
