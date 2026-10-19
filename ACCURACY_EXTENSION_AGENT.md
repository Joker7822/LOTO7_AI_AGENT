# Accuracy Extension Agent — fifth-expert prospective shadow

This is a **separate research-only forecasting candidate**, not a claim that lottery results are predictable or that model accuracy has improved.

## What is actually new

The existing Predictive Expert Agent blends four hypotheses (uniform 7/37, smoothed recent frequency, smoothed long frequency, and small momentum). This new agent adds a fifth **very strongly smoothed one-draw-lag transition** hypothesis. It estimates conditional marginal inclusion frequencies from at most the *previous 160 real historical transitions* and the seven numbers in the immediately preceding draw. This is a speculative pattern model: if LOTO7 draws are genuinely fair/independent, the correct conditional probabilities remain 7/37 and any apparent patterns may be noise.

Each of the five experts has a fixed positive prior weight; expert weights are then updated via prior-only Bernoulli proper log-score edges, with a fixed decay. Every prediction is subsequently shrunk 25% toward uniform 7/37. All probabilities remain within (0,1) and add up to exactly 7: this is **not** the false assumption that seven independent lottery-number draws occur.

The warmup, transition window, virtual prior strength (500), weight prior, online update rate, model code and score family are **SHA locked on the research registration** and cannot be changed retrospectively within this version.

## Evidence: two completely separate tracks

### Previously examined historical draws (exploratory only)

- Study uses the last 60 real draws, strict chronological walk-forward predictions and online updates *only after* each target outcome is scored.
- Compare the new five-expert ensemble against uniform proper log/Brier score and Top7, plus the original four-expert model only when its saved record is for the *exact same* historical data SHA and 60-round horizon.
- Repeat the **entire same learner** in 32 synthetic fair 7-of-37 histories for a matched full-budget null. The empirical p value is descriptive/exploratory because the historical dataset has already been explored extensively.
- Historical results cannot trigger model selection, adoption, automatic retuning, statistical claims or Production.

### Truly new results after prefrozen forecasts (descriptive only)

The independent **Accuracy Extension** protocol is registered before target **701** and explicitly excludes previously frozen target **700**.

1. Initial registration while current history ends at 699 saves the registration, the fixed code manifest and a waiting state. **No target 701 forecast is published at that time.**
2. Only once round 700 is available and **independently verified by two sources** does the agent freeze a full 37-marginal vector and Top7 *for target 701, before 701's outcome*.
3. Once round 701 is published and again verified by both sources, it grades **only that recorded vector**, appends a SHA256-chained result, learns using the now-confirmed result, and freezes target 702; repeat in strict order.
4. Every run audits the entire append-only chain, frozen vector hash, source verification, historical-prefix SHA, round identities, prior draw dates and previous grades. No skipped or retrospective 701 target may be reconstructed.
5. Continual monitoring is open-ended, but its p-values and post-hoc selection are **not** confirmatory. At least a separately registered new, nonoverlapping future evaluation is necessary before promoting anything.

The existing registered **Continuous Learning v1**, **Joint Set v2 future OOS**, locked Champion, fixed 26-draw portfolio and Production publisher are untouched. The fifth-expert ledger is deliberately independent from the existing shadow, not a silent modification to a predeclared model.

## Dedicated research-only files

All seven artifacts are under loto7_agent_output and owned only by accuracy_extension_agent.py / its workflow:

- accuracy_extension_agent_registration.json
- accuracy_extension_agent_registry.json
- accuracy_extension_agent_state.json
- accuracy_extension_agent_freezes.jsonl
- accuracy_extension_agent_grades.jsonl
- accuracy_extension_agent_summary.json
- accuracy_extension_agent_report.md

GitHub Actions workflow: .github/workflows/accuracy_extension_agent.yml. It runs after the weekly draw, on source/CSV changes, manual dispatch, and PR tests. Only the seven paths above can be committed. It cannot write to Production, the original shadow registries or the lottery CSV.

Run:

    python accuracy_extension_agent.py --repo-root . --out-dir loto7_agent_output --source-report loto7_agent_output/source_validation.json --null-worlds 32
    python -m pytest -q tests/test_accuracy_extension_agent.py

For developer/synthetic PR scenarios, use --out-dir /tmp/accuracy-extension-test and --null-worlds 2. Artificial draw 700/701 fixtures are created **only** in isolated temporary directories.

**Success criterion**: more verified, genuinely future-only observations; not simply more backtests or apparently favorable historical Top7 scores. A genuinely fair lottery offers no guaranteed exploitable predictive edge.
