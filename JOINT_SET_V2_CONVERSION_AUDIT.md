# Joint Set v2: rank, calibration and five-ticket conversion — Research only

## Experiment A — diagnostic, not selection

Use the already saved strict-nested v2 backtest (60 targets), rebuild each selected configuration with prior-only history and verify exact saved log-score, Top7 and gate values. Record raw and gated inclusion forecasts (sum of each vector = 7), number ranking, mean Top7 hits, log/Brier proper-score edges against uniform 7/37, the fraction of rounds with identical raw/gated Top7, zero gates, and probability-vs-empirical-reliability in five raw-rank buckets.

The gate can shrink probabilities almost to uniform while preserving the rank ordering. A promising historical rank is **not** evidence of independent future predictability. Raw probabilities must never replace the registered prospective vectors.

## Experiment B — exact metric and isolated Monte Carlo samples

The existing optimizer maximizes mean utility with heavy additional rewards for hits 5, 6, 7. The existing realized portfolio score instead is:

    max_ticket_hits + 0.35*any_3plus + 0.75*any_4plus + 0.10*mean_ticket_hits

The research alternative optimizes precisely the latter, with the same five-ticket count, candidate pool, scenario pool, scenario and candidate seed, and local-search budget. The existing v2 optimizer baseline is replayed and **must** numerically reproduce the prior saved strict-nested historical score in each round, or the diagnostic fails.

Each constructed portfolio is evaluated against (a) the previously used historical actual draw, (b) construction Monte Carlo scenarios, (c) independently seeded Monte Carlo scenarios generated from the **same fitted model**. The audit reports a paired realized-score bootstrap interval and train/independent MC optimism. Independently seeded simulator draws are **not independently collected lottery results**, and the previous 60 outcomes are repeatedly reused historical material. They are strictly exploratory, irrespective of p-values or attractive means.

Command:

    python joint_set_v2_conversion_audit.py --rounds 60 --independent-scenarios 512

Output paths: loto7_agent_output/joint_set_v2_conversion_audit_summary.json, joint_set_v2_conversion_audit_report.md, joint_set_v2_conversion_audit_rows.csv.

## Scientific governance

Do **not** modify joint_set_v2_model.py, joint_set_v2_research.py, joint_set_v2_signal_oos.py or any SHA-locked prospective manifest. Do not tune or switch the existing Production, Champion, Formal Challenger, or frozen shadow at 701. No post-hoc objective selection based on these reused 60 draws.

## Independent study after the current 26-draw horizon (PLAN ONLY)

The existing registered shadow starts at target 701, excludes 700, and has a **fixed 26 trusted-draw horizon**. If those 26 consecutive eligible rounds are successfully observed, the last is 726 and 727 is the earliest *potential* next target. This text does not freeze or enroll target 727, or start a second study.

A subsequent study must separately preregister, **before its first eligible result**, (1) one primary endpoint distinguishing number-level signal from five-ticket utility, (2) a single locked candidate or tiny predeclared family, (3) verified pre-draw full inclusion vectors and ticket SHA freeze, (4) paired uniform and matched-budget search baselines, (5) a prospective sample-size/power justification and explicit horizon/stopping boundary, (6) code and configuration hashes, timestamp, append-only audit history, missing-draw fail-closed behavior, and (7) no automatic Production promotion.

For context, a fixed random Top7 has expected 49/37 = 1.3243 hits; with 26 independent draws its average-hit standard error is about 0.186. Detecting persistent +0.25 hits with conventional 5% significance and 80% power would need roughly 100+ independent draws under an idealized iid approximation; real multiple testing and temporal dependence complicate that estimate. Set the exact target and power before starting, not after seeing outcomes.

The current 26-draw study and its registered endpoints remain completely unchanged.
