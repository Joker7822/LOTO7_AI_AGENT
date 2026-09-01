# Calibration Future-OOS Exact E-Process

## Purpose

This document preregisters the final statistical endpoint for the Research-only Champion calibration Future-OOS shadow before the first trusted draw (target round 693) is observed.

It does not change Production, the Formal Challenger, ticket generation, the existing Strict Future-OOS gate, or any promotion threshold.

## Fixed horizon

- Start: target round 693.
- Horizon: exactly 26 trusted future draws.
- Trusted means the existing two-result-source verification accepts the draw.
- Interim values are diagnostic only.
- No robust Uniform-edge claim is allowed before all 26 trusted draws are complete.

## Null hypothesis

Conditional on all information available before each draw, the next winning 7-number set is uniformly distributed over all `C(37,7)` subsets.

The calibrated probability vector may adapt to earlier resolved draws, provided the complete 37-value vector is frozen before the target result. Therefore the test is valid for the adaptive prospective protocol.

## Primary proper-score endpoints

Two endpoints are preregistered.

### 1. Log-score edge vs Uniform

For frozen probabilities `q_i`, define

`a_i = log(37 q_i)`.

For the winning set `S` of size 7,

`L = (1/7) * sum_{i in S} a_i`.

This is exactly the draw's mean log-probability edge over Uniform.
Under the null,

`E_0[L | past] = (1/37) * sum_i a_i <= 0`

by Jensen's inequality.

### 2. Brier improvement vs Uniform

Using the repository's existing target distribution with `1/7` on each winning number,

`B = Brier(Uniform) - Brier(q)`

can be written as

`B = 2 * mean_{i in S}(q_i) - sum_i q_i^2 - 1/37`.

Under the null,

`E_0[B | past] = 1/37 - sum_i q_i^2 <= 0`.

## Exact without-replacement MGF

Each endpoint is an affine function of a size-7 sample mean from the fixed 37-number population for that draw.

For a standardized centered statistic and a fixed positive `lambda`, the conditional MGF under the null is computed exactly, not by bootstrap or asymptotic approximation.

For per-number log weights `w_i`,

`E_0[exp(lambda Z)] = e_7(exp(w_1), ..., exp(w_37)) / C(37,7)`,

where `e_7` is the seventh elementary symmetric polynomial.

The implementation evaluates this quantity in log space by dynamic programming in `O(37 * 7)` time.

The per-draw e-factor is

`exp(lambda * Z_observed) / E_0[exp(lambda Z)]`.

Because its conditional expectation is exactly 1 under the null, multiplying factors over future draws gives a valid e-process even when later frozen vectors depend on earlier results.

## Fixed lambda mixture

The following values are fixed before the first trusted draw:

- 0.25
- 0.50
- 1.00
- 2.00
- 4.00

Each lambda has its own product e-process. The reported endpoint e-value is their equal-weight mixture. No historical or future retuning of these lambdas is allowed within this 26-draw protocol.

## Family control and final claim

There are two primary endpoints. The registered family alpha is 0.05 and the conservative endpoint alpha is 0.025, so the required e-value for each endpoint is 40.

The claim `robust_uniform_proper_score_edge` is confirmed only if, at the fixed 26-trusted-draw endpoint, all of the following hold:

1. ranking was preserved on all 26 trusted draws;
2. mean log-score edge vs Uniform is positive;
3. mean Brier improvement vs Uniform is positive;
4. the log-score mixture e-value is at least 40;
5. the Brier-improvement mixture e-value is at least 40.

Actual-number probability-mass edge remains a secondary descriptive diagnostic and is not a primary significance endpoint.

## Fail-closed rules

A trusted result is excluded from this endpoint and the protocol is invalidated for that draw if its matching prefrozen reference is missing or if the calibrated-q SHA-256 differs from the hash recorded in the result ledger.

The e-process is deterministically rebuilt from the immutable freeze-history ledger and trusted results on every run. This avoids dependence on mutable accumulated state.

## Governance

This endpoint has `diagnostic_only` authority. A positive 26-draw result is evidence for the calibration signal, not automatic permission to alter Production or the existing ticket-level promotion gate.
