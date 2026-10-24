"""Contract checks that public health telemetry refreshes after bot-produced evidence."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_refreshes_on_evidence_workflow_completion():
    text = (ROOT / ".github/workflows/dashboard_ops_snapshot.yml").read_text()
    assert "  workflow_run:" in text
    assert "    types: [completed]" in text
    for name in (
        "LOTO7 Independent Result Corroboration",
        "Continuous Learning Agent Prospective",
        "Joint Set v2 Signal Future OOS",
        "Predictive Expert Agent Research",
        "Continuous LOTO7 Research v4",
        "LOTO7 Agent Role Council",
    ):
        assert f'- "{name}"' in text
    # The snapshot itself cannot trigger a workflow_run feedback loop.
    assert '"Browser Ops Snapshot"' not in text.split("  workflow_run:", 1)[1].split("  workflow_dispatch:", 1)[0]
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
    assert 'state["current_target_round"] == 701' in v2
    assert 'git diff --exit-code -- loto7.csv loto7_agent_output/' in v2
