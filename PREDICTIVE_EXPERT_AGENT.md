# Predictive Expert Agent — research-only forecast skill enhancement

## Objective

The previous Role Council checks operational safety. This agent performs a **new, concrete numeric forecasting experiment**, asking whether an online ensemble of simple, heavily shrunk inclusion-probability experts can predict seven winning numbers better than uniform without hindsight.

It does **not** modify frozen Joint Set v2 algorithm files, the registered 26-draw signal shadow starting at 701, 26-draw Portfolio OOS, Champion, Production, purchase tickets or the original strict OOS promotion gate.

## Four cooperating scientific roles

1. **Hypothesis engineer:** produces four 37-number inclusion-probability experts with exactly seven total expected hits: uniform 7/37, 40-draw Bayesian-shrunk frequency, 160-draw Bayesian-shrunk frequency, and a small, zero-sum momentum shrinkage deviation. This is an experimental hypothesis: no hot/cold or momentum predictability is presumed.
2. **Online calibration specialist:** mixes these forecasts via deterministic exponentially weighted historic Bernoulli proper-log-score edges. The uniform expert receives a predeclared **55% initial weight**, and all nonuniform hypotheses collectively 45%. At target t, features and weights depend **only on draws before t**. Each outcome updates weights after its scored forecast, never before.
3. **Independent skeptical validator:** evaluates every target via one chronological prequential pass (100-draw warmup, then 60 most recent real draws for reported diagnostics). Then runs **the same 100-train + online update + 60-evaluation protocol on each of 64 independent synthetic fair 7-of-37 histories**, all matching the real history length. Reports primary log-score edge, secondary Top7, proper Brier, rank bucket reliability and plus-one empirical upper-tail null p. Also compares the saved strict nested v2 report only when its data SHA and evaluation count exactly agree.
4. **Promotion firewall:** interprets all outcomes from the previously explored historical dataset as **research-only**, no matter what p-value is obtained. No automatic adoption or retroactive claim. Synthetic worlds are a statistical control, not prospective evidence.

All coefficients, prior weights, window lengths, budget and online learning rate are fixed in the initial version of predictive_expert_agent.py. There is no selection among hundreds of candidates using the evaluated historical 60 draws.

### Rigorous restrictions

- Inclusion vectors are 37 Bernoulli *marginal* probabilities for a 7-without-replacement draw, each in [0,1], summing to 7; the experiment does not pretend to identify 37 independent draws.
- Fair null controls generate exactly seven distinct numbers per simulated draw, matching the true drawing mechanism. They repeat **the entire adaptive learning path and number of evaluations**, not a cheap fixed-forecast permutation.
- Actual historic 60 draws have been inspected in multiple earlier reports. A nominally small null p-value here is **exploratory only**, cannot be used as independent evidence or a model switch.
- Prior-only and terminal-target mutation tests enforce no look-ahead; modifying the current outcome must not change the probabilities/weights at that target.
- No online learning result overrides the registered prospective v2 signal whose protocol manifest SHA256 is locked. A distinct preregistered Future-OOS study would be required **before** using this predictor for actual decision-making.
- Don't reinterpret a score improvement as a guarantee of winnings or a higher fair lottery probability. A fundamentally fair machine has no exploitable historical signal.

## Agent outputs and next allowed research step

The agent produces three separate files under loto7_agent_output:

- predictive_expert_agent_summary.json — four roles, proper scores, Top7, null world distribution summary, p-values, prior-only weight trajectory summary and a non-adoption handoff;
- predictive_expert_agent_rounds.csv — target-by-target online scores and weights;
- predictive_expert_agent_report.md — human-readable conclusions and evidence limitations.

Run manually:

    python predictive_expert_agent.py --csv loto7.csv --out-dir loto7_agent_output --min-train 100 --last-n 60 --null-worlds 64
    python -m pytest -q tests/test_predictive_expert_agent.py

The agent's GitHub workflow runs on research-only code changes, manually, and every Saturday at 13:30 JST after normal Friday result ingestion. It must only add those three report files. No automatic dispatch to Production or the registered v2 OOS.

If the results justify further research, define a new **separately dated and algorithm-hashed prospective experiment before its eligible target outcome**. The current 701–726 registered signal run is never switched based on this retrospective comparison.
