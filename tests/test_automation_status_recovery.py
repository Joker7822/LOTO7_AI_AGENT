"""Contract checks that public health telemetry refreshes after bot-produced evidence."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_refreshes_on_critical_evidence_without_research_fanout():
    text = (ROOT / ".github/workflows/dashboard_ops_snapshot.yml").read_text()
    assert "  workflow_run:" in text
    assert "    types: [completed]" in text
    run_section = text.split("  workflow_run:", 1)[1].split("  workflow_dispatch:", 1)[0]
    for name in ("LOTO7 Independent Result Corroboration", "Weekly Production Publisher"):
        assert f'- "{name}"' in run_section
    for name in (
        "Continuous Learning Agent Prospective", "Joint Set v2 Signal Future OOS",
        "Predictive Expert Agent Research", "Continuous LOTO7 Research v4",
        "LOTO7 Agent Role Council", "Pair Context v2 Numeric Diagnostics",
        "Browser Ops Snapshot",
    ):
        assert f'- "{name}"' not in run_section
    assert '- cron: "13,43 * * * *"' in text
    assert "git add -- docs/data/dashboard_snapshot.json" in text


def test_registered_learning_algorithm_is_not_rewritten_to_fix_old_tests():
    workflow = (ROOT / ".github/workflows/continuous_learning_agent.yml").read_text()
    assert "scripts/ci_verify_frozen_regressions.sh tests/test_continuous_learning_agent.py" in workflow
    assert "Dry-run actual registered temporal ledger without main writes" in workflow
    assert "git diff --exit-code -- loto7.csv loto7_agent_output/" in workflow


def test_checkpoint_rebase_fails_if_unknown_evidence_conflicts():
    w = (ROOT / ".github/workflows/continuous_loto7_v4.yml").read_text()
    sh = (ROOT / "scripts/rebase_v4_checkpoint.sh").read_text()
    assert "bash scripts/rebase_v4_checkpoint.sh" in w
    assert 'git checkout --ours -- "$source_file"' in sh
    assert 'if [ "$conflicts" != "$source_file" ]' in sh
    assert "validate_trusted_source(csv, report)" in sh
    assert "git rebase --abort" in sh



def test_verified_results_trigger_registered_701_freeze_workflows():
    for name in ("continuous_learning_agent.yml", "joint_set_v2_signal_oos.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text()
        assert 'workflows: ["LOTO7 Independent Result Corroboration"]' in workflow
        assert "types: [completed]" in workflow
    v2 = (ROOT / ".github/workflows/joint_set_v2_signal_oos.yml").read_text()
    assert "Dry-run registered prospective freeze without main writes" in v2
    # The first frozen target is #701, but after grading it the current
    # target advances. Guard PR dry-run against the actual immutable state.
    assert "before_target = before.get(\"current_target_round\")" in v2
    assert "assert after_target == 701" in v2
    assert "assert after_target == before_target + 1" in v2
    assert "assert after_count == before_count + 1" in v2
    assert 'git diff --exit-code -- loto7.csv loto7_agent_output/' in v2
