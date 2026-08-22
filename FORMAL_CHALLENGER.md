# Formal Challenger Policy

## Goal

Future OOS promotion evidence must come from one pre-frozen challenger at a time. Research may continue exploring many candidates, but only one model is promotion-eligible during a formal evaluation block.

## Block rules

- exactly **1 Formal Challenger** per Production Champion
- minimum block length: **8 trusted future draws**
- the challenger model/config is locked for the full block
- each target round receives newly frozen tickets for the same locked config
- untrusted/degraded-source draws do not advance the trusted-draw count
- after 8 trusted draws, existing v4 promotion thresholds still apply
- if the challenger is not promoted after the block, a new block starts with the highest-ranked frozen Research candidate available for the next target
- a Production Champion change immediately closes the old block and starts a new block against the new Champion

## Multiplicity control

`shadow_registry.json` is reduced to one promotion-eligible candidate before a future draw is graded. Other v4 shadow candidates are copied to `research_shadow_registry.json` and are Research-only.

`oos_candidate_state.json` keeps promotion evidence only for the active Formal Challenger versus the current Champion. Historical/non-formal evidence is not allowed to remain eligible for promotion.

This removes the previous six-candidate simultaneous promotion path and avoids candidate churn preventing evidence accumulation.

## Outputs

- `formal_challenger_state.json` — current locked block
- `formal_challenger_history.jsonl` — closed blocks and final evidence
- `research_shadow_registry.json` — archived Research-only frozen candidates
- `shadow_registry.json` — exactly one promotion-eligible Formal Challenger

## Statistical boundary

Historical research scores can select which already-frozen candidate enters the next formal block, but they cannot promote a model. Promotion still requires the existing v4 Future OOS e-process, minimum mean score delta, win-rate threshold, and trusted result-source verification.
