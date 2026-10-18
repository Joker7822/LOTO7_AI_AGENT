# Continuous Learning Agent — ongoing, genuinely prospective research

## Why

The former Predictive Expert Agent could redo historical research, but simply running it every day on the **same** data does not constitute improvement or fresh evidence. This new engine separates:
- **learning**, continuously updating prior-only expert weights when a genuinely new two-source-verified draw arrives;
- **prospective evidence**, permanently freezing the *next target's* full 37-number probability vector **before** its outcome;
- **evaluation**, grading only the frozen vector against the newly verified actual result; and
- **safety**, refusing to recover missing freezes by backfilling or altering the Production Champion.

The system is allowed to *adapt* after each new result. It does **not** guarantee its predictions will improve: under a fair lottery there may be no learnable edge. It is an open-ended descriptive monitoring experiment, not a continually re-tested significance claim.

## Immutable operating protocol

1. The protocol is registered once using the current repository's source SHA256 for **continuous_learning_agent.py**, **predictive_expert_agent.py**, **joint_set_v2_model.py**, **joint_set_v2_signal_oos.py** and **joint_set_v2_signal_oos_guard.py**, plus all hyperparameters and start/exclusion policies.
2. The protocol **excludes round 700** (already frozen under a different prior protocol). The first independently registered target is **701** and may be frozen **only after round 700's actual result was checked against two independent source records**.
3. An initial run on real draw **699** writes the registration, state and report, but **does not create a 701 forecast**. No result has yet become available to authorize it.
4. Once 700 is trusted, the fixed algorithm reconstructs all prior-only expert log-score updates chronologically from the real CSV (warmup=100), chooses the next forecast weights from strictly past outcomes, and freezes all 37 probabilities for **target 701** with exact SHA, data SHA and manifest hash.
5. Once 701 becomes two-source trusted, the engine scores **only that already frozen vector**; each result row stores the seven actual numbers, log-score vs uniform, Brier edge and Top7 count. It appends a hash-chained grading event and immediately freezes a new forecast for **702**, incorporating 701 **only after 701 was verified and graded**.
6. Each subsequent trusted draw repeats the same state transition without an end date. Untrusted data => hold. Skipped draw / broken manifest / failed result audit / changed freeze / duplicate target => **fail closed**. Every launch rechecks the entire immutable history and all previously graded results.
7. The first 26 prospective results become a **descriptive checkpoint only**; the engine continues after that. Drift monitors the 12 most recent prospective log-score edges; if negative, it reports a warning but never searches new hyperparameters based on ongoing evidence.
8. The registered model family, learner parameters and code remain fixed throughout this version. Continuous evolution here is **online weights adapting**, not arbitrary post-hoc reoptimization, unlimited added features or hidden promotions. Any change to this engine's locked code requires a **separate new registration with nonoverlapping future targets**, not an edit to the original 701-onward record.

## What is and is not independent

The earlier historical 60 draws used to develop these features are **not untouched holdout**. The first eligible genuinely prospective result is target 701, provided it had actually been frozen before result publication. The chronological log and GitHub commit history provide auditable provenance, but SHA hashes alone cannot independently prove publication timestamps. The already registered Joint Set v2 701–726 prospective signal shadow is a *different* experiment, unchanged.

The ongoing evidence is **descriptive**. No fixed-horizon p-values, alpha-spending, selection from various ongoing candidates, or automatic Production promotions. A separate pre-registration and sufficient new truly held-out results would be required for a confirmatory accuracy or deployment claim.

## Data & governance

Source: loto7.csv and loto7_agent_output/source_validation.json, validated through the existing secondary draw-source guard.

This engine is the sole writer of the following distinct **research-only** files:
- continuous_learning_agent_registration.json — source/algorithm manifest;
- continuous_learning_agent_registry.json — latest currently frozen, next target;
- continuous_learning_agent_state.json — number of trusted results, current target;
- continuous_learning_agent_freeze_history.jsonl — chained append-only full vectors;
- continuous_learning_agent_results.jsonl — chained append-only grading events;
- continuous_learning_agent_summary.json — descriptive progress, log/Brier/Top7 and recent drift;
- continuous_learning_agent_report.md — human-readable status.

No writes to Champion, Production tickets, original strict OOS, Joint Set v2 shadow, source report, or forecast code. Changes to registered inputs are prohibited, not auto-migrated. The workflow fires on data/source changes and daily at **10:35 JST**, with bounded git retry that re-reads the latest main and validates all evidence again. Its commits only stage the seven research files.

Run:

    python continuous_learning_agent.py --repo-root . --out-dir loto7_agent_output --source-report loto7_agent_output/source_validation.json
    python -m pytest -q tests/test_continuous_learning_agent.py

All synthetic timeline tests run in a temporary directory. Fake outcomes for 700/701 are **never** written to the real CSV or main's registered evidence.

## Safety caveat

Persistent learning does not imply persistent accuracy gains or actual profits. If every draw is fair and independent, the correct conditional inclusion probability remains 7/37. The strongest scientifically valid autonomy is continuous *measurement*, guarded incremental *updates*, and refusal to deploy unproven improvements.
