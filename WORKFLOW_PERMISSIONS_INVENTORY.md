# Workflow Permissions Inventory

_Generated from a full static audit of `.github/workflows/` on 2026-11-24; updated for the three-job-split migration on 2026-11-25.
Counts are measured, not estimated: 58 workflows, 40 with
`contents: write`, 18 read-only. Every `contents: write` workflow was
checked for an actual `git push` — all 40 push their own research or
production outputs back to `main`, so none of them can be downgraded to
read-only without breaking their function. The risk to manage is
therefore **when** the write token is exposed, not whether it exists._

## Classification

### A. Split jobs — least privilege already applied (13)

Top-level permission is `contents: read`; only the publish job, gated by
`needs:` on the verify job and an `if:` excluding `pull_request`, receives
`contents: write`. This is the target pattern for category B.

| Workflow | Triggers | Extra permissions |
|---|---|---|
| `advanced_online_v3.yml` | PR, push(main), schedule, manual | - |
| `autonomous_fulltext_paper_lab.yml` | PR, push(main), schedule, manual | - |
| `dashboard_ops_snapshot.yml` | PR, push(main), schedule, manual | - |
| `disjoint_future_oos.yml` | PR, push(main), schedule, manual | - |
| `independent_loto7_result.yml` | PR, push(main), schedule, manual | - |
| `online_learning_boost_v2.yml` | PR, push(main), schedule, manual | - |
| `open_ended_evolution.yml` | PR, push(main), schedule, manual | - |
| `pair_context_v2.yml` | PR, push(main), schedule, manual | - |
| `recursive_self_evolution.yml` | PR, push(main), schedule, manual | - |
| `repair_online_schedule_20261111.yml` | PR, push(main) | - |
| `advanced_validation_lab.yml` | PR, push(main), schedule, manual | - |
| `always_on_accuracy_research.yml` | PR, push(main), schedule, manual, workflow_run (trusted main only) | - |
| `frequent_online_research_feed.yml` | PR, push(main), schedule, manual | - |

### B. Single job, PR-triggered, push step guarded (14)

One job holds `contents: write` for its whole run, including on
`pull_request`. In every case the commit/push step (or the job itself) is
guarded by an event condition such as
`if: github.event_name != 'pull_request'`, so PR code cannot push — but
PR code does execute while a write-capable token exists in the job.
**Next step:** migrate these to the category-A split in small batches,
The first batch (hourly research, two-hourly discovery and three-hourly validation) now uses separate read-only validation and main-only publish jobs. Continue migrating the remaining 14 in reviewable batches. Until migrated,
the push guard is mandatory: a new workflow in this category without an
event guard on its push step must not be merged, and the net-zero rule
in `RESEARCH_EXPANSION_POLICY.md` applies.

| Workflow | Triggers | Extra permissions |
|---|---|---|
| `accuracy_extension_agent.yml` | PR, push(main), schedule, manual | - |
| `agent_role_council.yml` | PR, push(main), schedule, manual | - |
| `autonomous_evolution_lab.yml` | PR, push(main), schedule, manual | - |
| `autonomous_self_rewrite.yml` | PR, push(main), schedule, manual | - |
| `continuous_learning_agent.yml` | PR, push(main), schedule, manual | - |
| `first_prize_prospective_oos.yml` | PR, push(main), schedule, manual | - |
| `joint_set_v2_continuous_rank_bonus.yml` | PR, push(main), manual | - |
| `joint_set_v2_conversion_audit.yml` | PR, push(main), manual | - |
| `joint_set_v2_rank_portfolio.yml` | PR, push(main), manual | - |
| `joint_set_v2_signal_oos.yml` | PR, push(main), schedule, manual | - |
| `online_literature_auto_verify.yml` | PR, push(main), schedule, manual | - |
| `predictive_expert_agent.yml` | PR, push(main), schedule, manual | - |
| `research_data_quality_auto.yml` | PR, push(main), schedule, manual | actions: write |
| `watch_auto_improvement.yml` | PR, push(main), schedule, manual | - |

### C. Single job, no PR trigger (13)

Triggered only by pushes to `main`, schedules, or manual dispatch, so
unreviewed PR code never runs with the write token. Keep as is; re-check
if a `pull_request` trigger is ever added (that moves the workflow to
category B and the guard requirement applies).

| Workflow | Triggers | Extra permissions |
|---|---|---|
| `champion_calibration_oos.yml` | push(main), schedule, manual | - |
| `champion_ranking_calibration.yml` | push(main), manual | - |
| `continuous_loto7_v4.yml` | push(main), schedule, manual | actions: write |
| `joint_set_identity_ablation.yml` | push(main), manual | - |
| `joint_set_parallel_null.yml` | push(main), manual | - |
| `joint_set_research.yml` | push(main), schedule, manual | - |
| `publish_production_now.yml` | manual | - |
| `signal_expert_attribution_oos.yml` | push(main), schedule, manual | - |
| `signal_meta_research.yml` | push(main), manual | - |
| `strict_oos_bootstrap.yml` | push(main), manual | - |
| `verify_sakura_credential_rotation.yml` | manual | issues: write |
| `weekly_production_fallback.yml` | schedule, manual | - |
| `weekly_production_publisher.yml` | push(main), schedule, manual | - |

### Read-only (18)

`contents: read` only. Two watchdogs additionally hold `actions: write`
and no contents write; that is dispatch-only privilege, used to start
another workflow via `gh workflow run`.

| Workflow | Triggers | Extra permissions |
|---|---|---|
| `autonomous_research_specialists.yml` | PR, schedule, manual | - |
| `browser_dashboard_ci.yml` | PR, push(main), manual | - |
| `ci.yml` | PR, push(main) | - |
| `friday_production_publication_watchdog.yml` | push(main), schedule, manual | actions: write |
| `friday_result_check_watchdog.yml` | push(main), schedule, manual | actions: write |
| `full_round2_reforecast.yml` | PR, manual | - |
| `online_research_intelligence.yml` | PR, schedule, manual | - |
| `online_research_operational_audit.yml` | PR, schedule, manual | - |
| `production_combination_agent_full_replay.yml` | PR, manual | - |
| `production_geometry35_policy.yml` | PR, manual | - |
| `production_roi_cash_v2_adoption.yml` | PR, manual | - |
| `research_evolution_round2_replay.yml` | PR, schedule, manual | - |
| `research_intelligence_core.yml` | PR, schedule, manual | - |
| `research_roi_cash_v2.yml` | PR, manual | - |
| `round20_change_replay.yml` | PR, push(main), schedule, manual | - |
| `signal_portfolio_factorial.yml` | PR, manual | - |
| `sync_sakura_prediction_db.yml` | PR, push(main), manual | - |
| `top1_overlap34_research.yml` | PR, manual | - |

## Additional write permissions — all verified in use

| Permission | Workflows | Verified use |
|---|---|---|
| `actions: write` | `continuous_loto7_v4.yml`, `research_data_quality_auto.yml` | `gh workflow run` self/target re-dispatch |
| `actions: write` (no contents write) | `friday_production_publication_watchdog.yml`, `friday_result_check_watchdog.yml` | `gh workflow run` watchdog dispatch |
| `issues: write` | `verify_sakura_credential_rotation.yml` | `gh issue comment` / `gh issue close` after a successful verification run |

No other write scopes (`packages`, `deployments`, `id-token`, …) appear
anywhere in the inventory.

## SHA pinning

Every `uses:` reference (168 across 57 workflow files; one workflow uses
no actions) is pinned to a full 40-character commit SHA with the
major-version tag kept as a trailing comment, e.g.
`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7`.
All referenced actions are first-party `actions/*`. Dependabot's
`github-actions` ecosystem (weekly, grouped, see `.github/dependabot.yml`)
proposes SHA updates as reviewable PRs, which is how pins advance from
here — tags must not be reintroduced.
