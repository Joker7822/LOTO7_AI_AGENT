# Historical security incident and prospective-evidence audit

Updated: 2026-11-25 JST (external integration retirement proposal).
The historical credential exposure is recorded in [issue #45](https://github.com/Joker7822/LOTO7_AI_AGENT/issues/45), opened 2026-09-06.
No credential values are retained here. Removing the external integration does
not verify that the old credentials were revoked or remove them from Git history.
The authorized external administrator must disable the retired endpoint and
revoke exposed credentials; the repository owner must remove unused Actions
secrets. Keep the incident open until verified. The former rotation workflow
and runtime status are not needed after retirement.

## Regression / safeguards

```bash
python -m pytest -q tests/test_weekly_production_schedule.py tests/test_workflow_security_governance.py
```

The weekly publisher and fallback retain source verification, canonical ticket
validation, publication windows and immutable prediction ledgers; the retired
network sync is removed.

## Fixed 26-draw Future OOS: inference boundary

- The existing 26-trusted-draw holdout is retained without resetting candidates, scored outcomes, SHA lock or geometry.
- As of 2026-10-31, `confirmation_policy_registered_at_trusted_draws` is **4** in the archived state: the final confirmation rule was recorded after four trusted outcomes.
- A SHA-locked rule **after** observations is integrity evidence from that point forward, not evidence it was preregistered before the first outcome.
- `future_holdout_evidence.py` now reports this timing as an explicit field. Even if all metrics pass at 26 draws, it cannot emit `confirmed_operational_future_oos_edge` for an incomplete or late-registered confirmation policy.
- This is a **conservative reporting rule**, not an attempt to erase or re-grade the previous results. The original holdout remains a diagnostic study.
- A new, separately preregistered confirmation study would require its own protocol registered before its first outcome. It must not reuse the completed samples from the previous holdout as genuinely new evidence.

## Environment reproducibility

CI records Python package versions from its run in an artifact. This does not replace fully pinned dependencies, wheels and hashes. Before changing NumPy/Pandas versions, establish a separate compatibility baseline: compare deterministic old-replay outputs, output hashes, and all prospective-ledger safety tests. Never update an existing prospective ledger to match a newly installed dependency.
