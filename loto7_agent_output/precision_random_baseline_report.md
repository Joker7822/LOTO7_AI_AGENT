# High-Precision Random Portfolio Baseline

- evaluated rounds: **593**
- Monte Carlo random portfolios: **4,096**
- symmetry reuse across rounds: **YES**
- cache key: **data SHA + min_train + reps**

| Window | max hits | mean hits | >=3 | >=4 | score |
|---|---:|---:|---:|---:|---:|
| full | 2.4387 | 1.3238 | 43.82% | 7.03% | 2.7772 |
| 120 | 2.4387 | 1.3238 | 43.82% | 7.03% | 2.7772 |
| 60 | 2.4387 | 1.3238 | 43.82% | 7.03% | 2.7772 |
| 30 | 2.4387 | 1.3238 | 43.82% | 7.03% | 2.7772 |

> 7/37の数字ラベル対称性により、同じNull分布を全履歴回へ再利用しています。
> Research comparison only; this does not create Future OOS evidence.
