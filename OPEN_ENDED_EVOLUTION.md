# Open-ended autonomous evolution researcher

2026-10-24 JST

This is a **new**, genuinely open-ended autonomous research lane for LOTO7. It is separate from the historical four-trial `autonomous_evolution_lab.py` and its `WAIT_FOR_INDEPENDENT_RESULT_SOURCE` stopping condition.

## What runs automatically

1. Inspect the actual chronological draw CSV and identify whether the latest outcome is verified or provisional.
2. Automatically generate mathematical model *programs*, not merely modify a fixed six-number parameter vector. The grammar supports frequency, exponential decay, gap, pair-context, uniform, weighted blends, and nonlinear power transforms.
3. Conduct prior-only 48-draw rolling historical tests and calculate log-score delta versus uniform, Top7 hits and three temporal block scores.
4. Self-select historically higher-fitness research programs and modify their structure, subtrees, operators and hyperparameters through mutation, crossover-style combinations and occasional independent restarts.
5. Auto-generate a working Python model module named `open_ended_evolution_candidate.py` for the highest historical research candidate.
6. Hash-chain each execution checkpoint including the evolving research state and a trajectory digest. Recover a missing state file from the authenticated journal; detect altered records.
7. Checkpoint and resume hourly. There is **no fixed global trial, data-SHA, generation or candidate-creation limit**.

## Difference from the previous bounded research lane

The search DOES continue when `research_cycle_guard.json` says `WAIT_FOR_NEW_DATA`, and it DOES run repeated historical experiments when the latest draw is not independently verified. An unverified latest row is excluded from the scoring sample and labelled provisional. The existing registered research guard is not modified. The lane is explicitly a separate **exploratory** search with no fixed lifetime budget.

The latest source's claimed round must still match the actual CSV. This is a numerical correctness condition, not a research quota. The model's program tree has a per-evaluation complexity threshold to prevent a single candidate from making its runner hang. There is no lifetime search limit.

## Reality of "unlimited"

No finite infrastructure provides literally unlimited compute, API calls, cloud quota, storage or money. GitHub Actions executes a **35-second research slice per hour**, checkpointing indefinitely until its owner disables the workflow or GitHub limits take effect. Runs may be delayed or halted by GitHub. Git-repository journal growth and Actions usage should be monitored.

Generated research programs use a typed mathematical instruction set. This is **automatic algorithmic program evolution**, not an unrestricted general AI with the ability to run arbitrary network commands or rewrite its governing repository. It does not silently overwrite publicly issued five-ticket forecasts, Production Champion, draw CSV or prefrozen Future-OOS records.

## Scientific limitation

Fitness is repeatedly tuned against the same historical 48 draws. Improving this number is **in-sample evolutionary selection** and is vulnerable to overfitting and multiple-testing bias. No increase in fair LOTO7 winning probability is established. An independently preregistered future study would be required to establish such an improvement.

## Use

- Direct execution: `python open_ended_evolution_agent.py --seconds 35`
- Manually run a fixed number of generations: `python open_ended_evolution_agent.py --steps 20`
- Test: `python -m pytest -q tests/test_open_ended_evolution_agent.py`
- GitHub Actions: `.github/workflows/open_ended_evolution.yml`
- Output: `loto7_agent_output/open_ended_evolution_state.json`, `open_ended_evolution_journal.jsonl`, `open_ended_evolution_report.md`, `open_ended_evolution_candidate.py`
