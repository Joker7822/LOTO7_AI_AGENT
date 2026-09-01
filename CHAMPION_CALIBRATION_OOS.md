# Champion Calibration Future-OOS Shadow

## Purpose

This protocol prospectively tests whether ranking-preserving probability calibration of the Production Champion improves proper scoring without changing number ranking.

It is **Research diagnostic only**. It cannot promote Production, change tickets, or alter the existing Strict Future-OOS gate.

## Locked base model

At protocol start, the current Production Champion config is copied into the protocol state and then locked for the entire prospective horizon. Later Production promotions do not rewrite the tested base signal.

## Calibration rule

For each future target, the calibration family and selector are fixed in `champion_ranking_calibration.py`.

The selected transform is chosen using only already-resolved historical rows before the target:

- temperature scaling: `q_T(i) ∝ q(i)^(1/T)`
- optional Uniform shrinkage: `(1-alpha) q_T + alpha/37`
- `T > 0`
- `0 <= alpha < 1`
- selection window: 120 resolved rows
- minimum history: 60 rows
- selector: `log_edge_vs_uniform + 8 * brier_edge_vs_uniform`

Because each transform is monotone in the base probability, the complete 37-number ranking and Top-7 membership must remain unchanged.

## Pre-freeze rule

For target round `r`, a reference may only be created while the latest resolved CSV round is `r-1`.

Each freeze stores:

- target round
- locked base model/config
- selected calibration config
- full 37-value base probability vector
- full 37-value calibrated probability vector
- `.17g` canonical string representation
- SHA-256 of each exact canonical vector
- Top-7 numbers
- data SHA and freeze timestamp

The same record is appended to `champion_calibration_oos_freeze_history.jsonl` so prior references remain auditable after the live registry advances.

Missing, malformed, tampered, or post-result references are not reconstructed. The affected draw fails closed.

## Result trust

A result is counted only when existing source validation reports:

- status `ok`
- latest validated round equals the target
- verification `verified_two_result_sources`

If the lottery result exists but trusted verification is not yet ready, grading waits and the next target is not frozen from that untrusted result.

## Metrics

Each trusted future draw records calibrated, locked-base, and Uniform values for:

- Top-7 hits
- actual-number probability mass
- mean log probability of actual numbers
- Brier score

Paired deltas are stored as:

- calibrated log score minus locked-base log score
- calibrated log score minus Uniform log score
- locked-base Brier minus calibrated Brier
- Uniform Brier minus calibrated Brier
- actual-mass deltas
- Top-7 delta vs locked base

Top-7 delta must be exactly zero; otherwise the draw fails closed.

## Fixed horizon

The prospective horizon is **26 trusted draws**.

Interim cumulative means are descriptive only. The protocol makes **no robust Uniform-edge claim before all 26 trusted draws are complete**. At horizon completion, status changes to `requires_final_fixed_horizon_analysis`; final statistical analysis is a separate explicit step.

## Files

- `champion_calibration_oos.py`
- `loto7_agent_output/champion_calibration_oos_registry.json`
- `loto7_agent_output/champion_calibration_oos_state.json`
- `loto7_agent_output/champion_calibration_oos_results.csv`
- `loto7_agent_output/champion_calibration_oos_freeze_history.jsonl`
- `loto7_agent_output/champion_calibration_oos_report.md`
- `.github/workflows/champion_calibration_oos.yml`
