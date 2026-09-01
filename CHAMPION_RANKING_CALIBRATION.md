# Champion Ranking-Preserving Calibration

## Purpose

The current Champion Hedge has useful ranking behavior but poor retrospective probability calibration. This Research-only module asks a narrower question:

> Can we preserve the Champion's exact number ranking while improving log probability and Brier score?

It does **not** change ticket generation, the Production Champion, the frozen Future-OOS registry, or promotion thresholds.

## Transform

For a Champion distribution `q`, a predeclared calibration configuration applies:

1. temperature scaling
   - `q_T(i) ∝ q(i)^(1 / T)` with `T > 0`
2. optional Uniform shrinkage
   - `q_cal(i) = (1 - alpha) q_T(i) + alpha / 37`
   - `0 <= alpha < 1`

Both operations are strictly monotone in the original `q(i)` when `alpha < 1`, so the full 37-number ordering is unchanged. Consequently, Top-7 membership is unchanged by construction.

`alpha = 1` is explicitly rejected because complete Uniform mixing would destroy strict ranking.

## Predeclared family

Version: `champion-ranking-calibration-v1`

The family contains 16 fixed configurations:

- identity
- temperature-only: 1.25, 1.50, 2.00, 3.00, 5.00
- Uniform shrinkage-only: 0.25, 0.50, 0.70, 0.85, 0.93, 0.97
- four limited temperature + shrinkage hybrids

No new calibration parameters are generated from the target result.

## Nested selection

For target row `t`:

1. the underlying Champion probability vector was already generated using draws `< t`
2. every predeclared calibration is scored on prior resolved rows only
3. at most the previous 120 scored rows are used
4. at least 60 prior calibration rows are required; otherwise identity is used
5. selection maximizes a proper-score objective:
   - `log_edge_vs_uniform + 8 * brier_edge_vs_uniform`
6. only after selection is fixed is target row `t` scored

Top-7 hits are not part of the selector because all valid calibrations preserve Top-7 exactly.

## Evaluation

The replay reports:

- Top-7 hits
- actual-number probability mass
- mean log probability of actual numbers
- Brier score
- rank-preservation rate
- moving-block bootstrap comparisons against the uncalibrated Champion
- moving-block bootstrap comparisons against Uniform

A useful calibration should improve Champion log/Brier scores without any Top-7 loss. A stronger signal claim additionally requires positive proper-score and mass edges against Uniform.

## Statistical boundary

All replay results are retrospective Research evidence. Even a strong historical result cannot promote Production.

Any production use would require a separate pre-frozen Future-OOS protocol, with the calibration rule and parameters fixed before target results are known.
