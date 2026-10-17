# LOTO7 AI Agent Role Council — boundaries and handoffs

The AI agent currently has independent, mature workflows for sourcing, continuous research, prospectively frozen shadow models, formal Future-OOS governance, and weekly Production publication. This feature adds a **cross-workflow decision and oversight layer**, rather than five competing lottery-prediction models.

## Deterministic roles

| Role | Accountability | Inspect only | Decision |
|---|---|---|---|
| data_steward | Source/data trust | CSV latest round, exact draw/date/main/bonus, two-source validation, timestamp | OK / WATCH if untrusted / BLOCK if trusted data conflicts |
| prospective_signal_custodian | SHA-locked v2 signal freeze | Registered manifest, 26-draw state, immutable freeze history, actual registry & result sequence | WAIT for verified 700; WATCH to freeze 701 only when 700 is verified; BLOCK on retroactive gap or SHA drift |
| oos_risk_officer | Champion, formal block & portfolio evidence | Champion, strict shadow/future registries, fixed 26/26 holdout, formal Challenger | WATCH until fixed 26/26, BLOCK on lock/identity mismatch; no promotion authority |
| research_skeptic | Exploratory vs independent evidence | Research cycle/plateau budget, v2 conversion audit metadata | WATCH as budget approaches limit; BLOCK on unregistered inference being promoted as independent |
| release_operations | Weekly Production issuance guard | Official next draw schedule, publisher state and 20:00 JST draw cutoff | OK before deadline; BLOCK on unissued target after result deadline, never backfill |

A reviewer receives an explicit next-action statement. The task queue is ordered BLOCK before WATCH, with a named owner and source-based evidence. Each role computes its verdict independently; the coordinator only aggregates, and it **does not vote to approve a model**.

## Role authority (hard limitation)

This Python job is **read-only** on every input and can only write:
- loto7_agent_output/agent_role_council_summary.json
- loto7_agent_output/agent_role_council_report.md

It cannot read/write credentials, publish tickets, grade or create an OOS freeze, overwrite a registered model, replace Champion, reinterpret historical 60-draw research as independent evidence, or grant a Production promotion. Authorized changes remain in the existing governed GitHub Actions jobs with their separate time and evidence constraints.

A role result of WATCH is descriptive and does not necessarily mean an operational fault. For example: current round 699, fixed v2 signal starts at 701 after verified round 700, and fixed portfolio holdout still has 7/26 trusted draws. This is normal waiting. A BLOCK is a stop-and-investigate recommendation, **not an autonomous rollback or source-repair operation**; the reporting workflow exits nonzero *after preserving the report*.

## Decision audit

The output includes a SHA256 of a canonical list of relevant repository input paths and their file SHA256 fingerprints (including the locked signal implementation). It does not leak the actual inputs into the machine-readable task queue. Every advisory output records:
- as-of JST, latest resolved round, version and snapshot hash;
- five role statuses and detailed findings;
- ordered handoff tasks with role owner, priority, reason and next action;
- a fixed explicit zero-permission matrix for Production changes;
- confirmation that no autonomous mutation was taken.

The workflow runs daily at **10:45 JST** and on relevant code/CSV/OOS state changes. On pull requests it generates its report only under /tmp. On main, it commits only its **own two diagnostic reports** with a bounded retry and never stages research state or Production outputs.

## Execution

    python agent_role_council.py --repo-root . --out-dir loto7_agent_output
    python agent_role_council.py --repo-root . --out-dir /tmp/loto7-role-council --fail-on-blocker
    python -m pytest -q tests/test_agent_role_council.py

Deterministic Python reviewers are distinct operational responsibilities, **not separately trained autonomous AI models**. Any model research and claims of improved future draw accuracy must continue to use independent pre-registered Future-OOS evaluation; governance checks do not constitute evidence of forecasting skill.
