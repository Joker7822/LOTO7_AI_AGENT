# Joint Set Research Suite

This is a **Research-only** model family. It never writes Production tickets, never changes the Production Champion, and never counts retrospective results as Future OOS promotion evidence.

## Architecture

The suite implements the structural research path introduced after the marginal-signal plateau:

1. **Dynamic marginal model**
   - exponentially weighted number frequencies at multiple half-lives
   - overdue and momentum components
   - regime-dependent short/long horizon mixing
2. **Low-rank pair interaction**
   - decayed pair residual matrix
   - strong effective-sample shrinkage
   - eigenvalue truncation to a small interaction rank
   - pair structure is retained during 7-number set sampling
3. **Hidden regime filter**
   - three states: stable / shift / volatile
   - persistent Markov transition model
   - emissions use prior-only recent-vs-prior distribution shift
4. **Dynamic Uniform Gate**
   - model confidence is derived from prior proper-score history only
   - negative log/Brier evidence shrinks the forecast toward uniform
   - sufficiently poor proper-score history can set the model contribution to zero
5. **Leakage-safe external metadata**
   - schema: `effective_round,available_at_jst,feature,value,source,verification`
   - only trusted records available before the conservative target cutoff are admitted
   - numeric metadata uses strongly ridge-shrunk prior-only regression against number residuals
   - categorical values are one-hot encoded
   - an empty metadata file is a valid state and has exactly zero model effect
6. **Expected-Utility five-ticket optimization**
   - draws future scenarios from the Joint Set distribution
   - candidate tickets are sampled from the same distribution
   - greedy selection maximizes portfolio-level expected utility
   - local swap search improves the final five-ticket set
   - no fixed overlap penalty is used

## Strict True Nested evaluation

`joint_set_research.py` evaluates the model with strict prior-only selection.

At historical target `t`:

- each predeclared config has only results from targets before `t`
- config selection uses only prior signal rows
- Dynamic Uniform Gate uses only prior proper-score rows
- pair/regime estimation uses only `x[:t]`
- metadata regression uses only `x[:t]`
- the five-ticket portfolio is constructed before reading `x[t]`
- only then is the target result scored

The config family is intentionally small and fixed in source code. This prevents an unbounded hyperparameter search from masquerading as model evidence.

## Matched-Budget Null

`joint_set_null_calibration.py` generates synthetic fair 7-of-37 histories and repeats the same:

- config family
- config-selection window
- regime/pair machinery
- Dynamic Uniform Gate
- metadata covariate sequence (with randomized draw outcomes)
- scenario count
- candidate count
- Expected-Utility portfolio optimizer

The empirical upper-tail p-value therefore asks whether the observed strict True Nested score delta is unusual relative to fair worlds exposed to the same research machinery.

Default target: **64 worlds**. The dedicated workflow advances two worlds per scheduled run and checkpoints every completed world.

## External metadata policy

The repository intentionally ships `loto7_agent_output/research_external_metadata.csv` with only a header.

Physical or operational metadata is activated only if it can be shown to exist **before the target draw**. A value learned from the target draw itself must not be assigned to that same target round. For example, a ball-set identity learned after round `r` may only affect a later effective round if its `available_at_jst` proves that it was already known before that later target cutoff.

This policy is deliberately conservative. Missing metadata is preferable to a leaked feature.

## Outputs

- `joint_set_true_nested_summary.json`
- `joint_set_true_nested.csv`
- `joint_set_true_nested_report.md`
- `joint_set_current_research.json`
- `joint_set_candidate_tickets.csv`
- `joint_set_latest_prediction.txt`
- `joint_set_null_calibration_state.json`
- `joint_set_null_calibration_summary.json`
- `joint_set_null_calibration_report.md`
- `research_metadata_summary.json`

## Promotion governance

All outputs above have:

- `independent_evidence = false` where applicable
- `promotion_eligible = false`

A Joint Set model may become a future formal challenger only through a separate, explicit freeze decision. Production promotion remains governed solely by trusted frozen Future OOS evidence.
