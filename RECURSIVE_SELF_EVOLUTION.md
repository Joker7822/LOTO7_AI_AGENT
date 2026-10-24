# Recursive code and meta-evolution researcher

**Research-only.** This agent adds a second evolving layer to the original
\`open_ended_evolution_agent.py\`. It evolves the *mathematical source expression*
of the model **and also the policy choosing its own mutation operators**.

## What self-evolves

1. Source formulas change structurally. Generated Python source contains a working
   \`predict_inclusion_probability(prior_history)\` and an updated versioned expression.
   Candidate expression ASTs may use arithmetic, finite constants, historical features,
   and pure transformations \`tanh\`, \`abs\`, \`sqrt\`, and \`log1p\`.
2. Its mutation policy adapts automatically: restart, AST feature splice,
   numerical parameter tuning, wrapping/complexifying code, and structural crossover.
   The trials and successes of each operation update its future selection probability.
   Each move keeps a nonzero probability, preventing total exploratory stagnation.
3. It performs strictly chronological prior-only diagnostics across 24 older
   outcome rounds. Fitness includes temporal block instability and small code
   complexity penalties, **not** true external holdout claims.
4. Cumulative generations and trials have no predefined global ceiling. Each
   25-second GitHub Actions slice resumes the hash-chained checkpoint, preserving
   learned mutation policy and diversity archive. Seeds depend on the CSV SHA
   and absolute generation, so identical work split across jobs is reproducible.
5. A draw-history update triggers re-evaluation against the new history and
   resets incompatible mutation-policy performance counters rather than
   comparing fitness values from different evaluation datasets.
6. Its access is limited to four new \`recursive_self_evolution_*\` report artifacts.
   Existing Champion, result sources, Future-OOS, published tickets, and algorithm
   registrations are not overwritten.

## Running

\`\`\`shell
python recursive_self_evolution_agent.py --steps 15
python recursive_self_evolution_agent.py --seconds 25
python -m pytest -q tests/test_recursive_self_evolution_agent.py
\`\`\`

The scheduled GitHub workflow is \`.github/workflows/recursive_self_evolution.yml\`.
Each execution is a time-slice, not a global research stop condition. The
checkpoint includes a SHA-256 hash chain but **is not cryptographically signed**
against an attacker able to rewrite the entire Git history.

## What "no restrictions" does and does not mean

There is no global count limit on new generations, repeated historical
experiments, the cumulative number of evolved mathematical expressions,
or mutation-policy updates. However:

- No finite computer or GitHub Actions account offers literally infinite memory,
  compute, storage, network, runtime, or money. GitHub scheduling is best-effort.
- Generated expressions can be executed only within the deliberately constrained
  mathematical AST and bounded *per-candidate* complexity. The agent cannot run
  arbitrary shell scripts, install packages, fetch arbitrary URLs, change
  governance code, or self-assign writing authority.
- A historical increase in mean log score does not establish improved lottery
  forecasting or future winning probability. Intensive repeated selection can
  **overfit the same historical draws**. Any future prediction improvement must
  be independently preregistered and evaluated on draws not yet observed.

Thus this implements an ongoing **recursive algorithmic self-evolution loop**,
not a general-purpose, unlimited, unconstrained artificial intelligence.
