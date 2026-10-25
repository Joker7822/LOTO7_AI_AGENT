# Signal × Portfolio Factorial & Expert Ablations (Research Only)

This diagnostic isolates *signal quality* from *five-ticket geometry* without
touching Production, Champion, any prefrozen forecasts, or existing Future OOS
registries. A historical improvement **is not** a claim of future predictive skill.

## Four prespecified factorial arms

All four are evaluated against each target draw with forecasts from earlier
draws only:

| Arm | Number weighting | Ticket construction |
| --- | --- | --- |
| uniform_random | 7/37 for each number | 16 seeded random portfolios per target (mean) |
| model_random | Existing legacy baseline weighted model | 16 seeded random portfolios per target (mean) |
| uniform_optimized | Uniform reference | Seeded greedy expected utility on uniform simulated scenarios |
| model_optimized | Existing legacy baseline weighted model | The same greedy optimization, model simulated scenarios |

The two random arms average the number of independently drawn portfolios selected
by `--random-reps`; the optimized arms each commit one five-ticket portfolio
before observing the target. **Their Monte Carlo uncertainty is not identical**.
Always compare paired per-round scores and intervals, not just aggregate means.

The optimized arm uses an exponential race (weighted sampling without replacement),
then maximizes the existing historical composite score:

```
max_hits + 0.35 * I(max_hits >= 3) + 0.75 * I(max_hits >= 4)
         + 0.10 * mean_ticket_hits
```

Candidate-ticket order is preserved when deduplicating; lexicographic truncation
would introduce an accidental small-number preference. The simulation is a
research model, not a proof of a true draw distribution. Under a perfectly fair
draw, portfolio geometry can alter thresholds for **any one** of five tickets
without improving the first-prize probability of five distinct tickets.

## Prior-only expert ablations

The same `baseline` configuration is retrained chronologically for each variant:

- `legacy` (unaltered reference)
- `pair_int64` (corrected pair-context separately versioned, no legacy edits)
- `drop_pair`, `drop_hot`, `drop_ewma`, `drop_overdue`,
  `drop_momentum`, `drop_recent_cold`
- `prior_uniform_gate`: use uniform weighting if the **previous 30** legacy
  inclusion log-score edges have a nonpositive mean; otherwise use baseline.

No variant may use the target outcome to compute that target forecast. Each
variant updates its weights only *after* scoring the observed target. Report
Top7 hits plus Bernoulli log-score/Brier-score deltas against the 7/37 uniform
inclusion baseline. Pair-v2 is **not** installed into the old runtime.

## Reproduce

```bash
python -m pytest -q tests/test_signal_portfolio_factorial.py
python signal_portfolio_factorial.py \
  --csv loto7.csv \
  --out research_output/signal_portfolio_factorial.json \
  --min-train 100 --last-n 60 \
  --scenarios 128 --candidates 48 --random-reps 16 \
  --seed 20261025
```

The report records the data/implementation SHA-256, chronological period,
configurations, signal ablation metrics, four portfolio arm scores, and
per-round forecast/portfolio SHA-256 values. The output path defaults outside
protected ledgers; do not automatically commit this artifact as formal future
evidence.

`python -m pytest -q` covers the regression suite. GitHub Actions can run the
research as a read-only workflow and upload a downloadable artifact.

## Governance and interpretation

- This evaluation reuses past draws that guided prior research and is therefore
  **exploratory**. It is not an independent holdout, a future-OOS proof, or a
  promotion decision.
- The default `last_n=60` is intended to expose engineering problems; it is
  not sufficient to establish a small predictive advantage. Freeze exactly one
  candidate with immutable algorithm SHA and parameters, then use newly observed
  independently corroborated draws under separate prospective registration.
- Never overwrite the existing 26-draw holdout, Champion baseline, official
  draw results, registered future observations, or already issued tickets.
- When the source is conditionally fair 7-of-37, historic draw frequencies
  cannot improve expected future inclusion probabilities. The uniform signal
  is a mandatory negative control.
- Optimizing for 3+ or 4+ ticket hits is a different objective from maximizing
  1st-prize probability. Do not treat coverage gains as an overall predictive
  breakthrough.


## Full 600-draw historical replay and reconciliation

To rerun **every target draw from round 101 through round 700** without
modifying any original, frozen predictions:

```bash
python -m pytest -q tests/test_signal_portfolio_factorial.py tests/test_summarize_factorial_replay.py
python signal_portfolio_factorial.py --csv loto7.csv \
  --out research_output/signal_portfolio_factorial.json \
  --min-train 100 --last-n 600 \
  --scenarios 128 --candidates 48 --random-reps 16 --seed 20261025
python summarize_factorial_replay.py \
  --replay research_output/signal_portfolio_factorial.json \
  --out research_output/full_history_replay_summary.json
```

The independent summary script fails closed unless the full 600 rows are
continuous, every aggregate reconciles to its stored per-round score, source
SHA-256 fingerprints exist, and research-only / no-promotion flags are intact.
It computes paired mean differences for draw windows 60, 120, and 600, with
seeded circular five-draw-block bootstrap 95% *exploratory* intervals. These
intervals do **not** adjust for previous model search or multiple hypotheses.

Both JSON artifacts are uploaded by the read-only diagnostic workflow.
Forecast and portfolio checksums are retained for each historical target.
All nine signal-variant metrics and all four five-ticket-arm metrics are retained
per target, enabling independent recomputation of the reported aggregates.

**Important:** The historical backtest *recomputes* predictions with the current
version of the code. It is **not** a replacement for independent evidence from
predictions issued and frozen before their actual draw results. These results
must never be used to retroactively modify Future-OOS evidence, existing
Champion registration, or historical issued tickets.
