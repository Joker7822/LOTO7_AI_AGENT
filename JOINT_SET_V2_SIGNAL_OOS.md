# Joint Set v2 Signal — Prospective Future-OOS Protocol

## Purpose

This protocol observes the **Joint Set v2 inclusion-probability signal only** on genuinely future LOTO7 draws. It is Research-only. It has no Production, Champion, Formal Challenger, ticket-selection, or promotion authority.

Historical diagnostics found a potentially interesting v2 number-identity ranking effect, while matched-budget and portfolio-level tests did not establish a reliable five-ticket advantage. Therefore this protocol freezes the signal before future results instead of continuing to tune the portfolio on the same historical window.

## Prospective start and round 700 exclusion

The protocol is registered while the latest resolved draw is round 699.

- Round **700 is explicitly excluded** from this new protocol because it was already frozen under the repository's existing governance before this v2 signal protocol existed.
- The first eligible v2 signal target is round **701**.
- A round-701 inclusion vector may be generated **only after round 700 is present and verified by two result sources**.
- If round 701 becomes known before a round-701 vector was prefrozen, the protocol fails closed. It must not reconstruct round 701 retrospectively.

This makes the first observation genuinely prospective with respect to this protocol.

## Locked algorithm

At registration the protocol hashes and locks:

- `joint_set_v2_signal_oos.py`,
- `joint_set_v2_model.py`,
- `joint_set_v2_research.py`,
- the complete predeclared v2 config-version family,
- `min_train = 100`,
- config-selection window `120`,
- the 26-trusted-draw horizon,
- the endpoint definitions,
- the 4,096-replicate final permutation plan.

If the locked manifest changes during the horizon, the protocol stops with a fail-closed status rather than silently changing the prospective model.

The v2 config itself may vary by target only through the already-predeclared strict prior-only selection rule. For target `t`, the selected config, calibration rows, regime estimate, gate, and 37-number inclusion vector use only draws strictly before `t`.

## What is frozen before each result

For every eligible target the registry stores before the result:

- target round,
- latest resolved prefix round,
- source-verification status of the prefix,
- data SHA256,
- selected v2 config/version and prior-only selection score,
- all 37 calibrated inclusion probabilities, constrained to sum to 7,
- SHA256 of the canonical inclusion vector,
- Top-7 ranking,
- gate diagnostics,
- regime posterior,
- locked algorithm-manifest SHA256,
- freeze timestamp in JST.

The freeze history is append-only by target. Conflicting records for the same target are invalid.

## Trust and fail-closed rules

A target is graded only when the existing source validator reports `verified_two_result_sources` for the exact resolved round.

The protocol fails closed if:

- the first eligible target passes without a prefrozen vector,
- any later target passes before its vector is frozen,
- the locked algorithm manifest changes,
- the canonical inclusion-vector hash changes or is malformed,
- the stored Top-7 does not match the prefrozen vector,
- the inclusion probabilities do not sum to 7,
- a registry needed after the protocol has started is missing.

A missed target is never reconstructed after its result is known.

## Fixed horizon and endpoints

The horizon is **26 trusted future draws**. Interim values are descriptive only and may not be used for tuning.

### Primary endpoint

Mean Bernoulli log proper-score edge versus the uniform inclusion probability `7/37`, computed across all 37 numbers for each draw and averaged over the fixed 26-draw horizon.

### Secondary endpoint

Mean Top-7 winning-number hits across the same fixed 26 draws.

### Supportive endpoint

Mean Bernoulli Brier improvement versus uniform.

## Final matched number-identity inference

Only after 26/26 trusted draws are complete, the protocol runs **4,096 deterministic global permutations of labels 1..37**.

Within each replicate, the same label permutation is applied to every one of the 26 prefrozen vectors. This preserves each vector's probability geometry and cross-draw label structure while breaking alignment with the actual winning-number identities.

The protocol reports one-sided upper-tail Monte Carlo p-values with the correction:

`p = (1 + number of null statistics >= observed) / (4096 + 1)`.

The primary p-value corresponds to the fixed-horizon mean Bernoulli log-score edge. Top-7 and Brier results are secondary/supportive.

## Interpretation boundary

This is a Research-only prospective diagnostic. Even a favorable 26-draw result does not automatically promote v2 or alter Production governance. Any future promotion path must be separately declared and satisfy the repository's existing promotion rules.

No portfolio/ticket policy is tuned or evaluated by this protocol. That separation is deliberate: the purpose is to answer whether the v2 number-identity/inclusion signal itself survives genuinely future observation.
