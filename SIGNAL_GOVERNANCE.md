# Signal / Portfolio Governance

## Purpose

Research評価を次の2系統へ分離する。

### Signal quality
5口の組み方とは無関係に、各抽せん直前の確率分布 `q` 自体を評価する。

- Top-7 hits
- actual-number probability mass
- mean log probability of the seven actual numbers
- Brier score against the seven-number empirical distribution

Uniform 1/37 distributionを固定基準としてedgeを計算する。

### Portfolio quality
Signal `q` から5口を構成した後の結果を評価する。

- max hits across five tickets
- mean hits
- >=3 hit rate
- >=4 hit rate
- existing composite portfolio score

`overlap_penalty` はPortfolioだけに影響し得るため、Signal改善とは区別する。

## Research Parent acceptance

Portfolio objectiveが改善しても、次のSignal gateを満たさない候補はResearch Parentへ採用しない。

- full-history log edge must not materially regress
- full-history Top-7 edge must not materially regress
- recent-120 log edge must not materially regress
- when the incumbent full-history log edge is non-positive, the challenger must improve it
- boundary regularization prevents unrestricted preference for hard parameter limits

This prevents a model from appearing stronger only because five tickets are spread more aggressively.

## Statistical boundary

All full-history replay, Signal evaluation, Portfolio evaluation, and feedback optimization are retrospective Research evidence. They can be affected by model-selection leakage and are **not** valid Production promotion evidence.

Production Champion promotion remains restricted to pre-frozen Future OOS results under the existing v4 governance policy.

## Result-source verification

`fetch_validate.py` checks:

1. primary historical result feed used by `scrapingloto7.py`
2. Mizuho result page when accessible
3. Rakuten Bank's directly published LOTO7 winning-number endpoint as fallback
4. official lottery schedule context

A parseable secondary result must agree exactly on round, seven main numbers, two bonus numbers, and date when the secondary publishes one. Any disagreement fails closed. If no secondary result is parseable, operation remains degraded and the draw is not trusted for Production promotion evidence.
