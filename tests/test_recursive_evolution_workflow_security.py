"""Regression checks for the recursive research workflow trust boundary.

Read-only checks only: never invoke the publisher, modify research states,
or require GitHub Actions credentials during pytest.
"""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/recursive_self_evolution.yml"


def test_recursive_publisher_is_main_only_and_waits_for_validation():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    validate, publish = workflow.split("  publish-research-only:\n", 1)
    header = publish.split("    steps:\n", 1)[0]

    assert "needs: validate-recursive-agent" in header
    assert "github.event_name != 'pull_request' &&" in header
    assert "github.ref == 'refs/heads/main' &&" in header
    assert "needs.validate-recursive-agent.result == 'success'" in header

    # Validation is read-only and the write token exists only in the gated job.
    assert "permissions:\n  contents: read" in validate
    assert "contents: write" not in validate
    assert "persist-credentials: false" in validate
    assert "    permissions:\n      contents: write" in publish
    assert "persist-credentials: true" in publish
    assert "git push origin HEAD:main" in publish

    # Research output allowlisting is independent of the job-level event gate.
    assert "loto7_agent_output/recursive_self_evolution_state.json" in publish
    assert "loto7_agent_output/recursive_self_evolution_journal.jsonl" in publish
    assert "loto7_agent_output/recursive_self_evolution_candidate.py" in publish
    assert "loto7_agent_output/recursive_self_evolution_report.md" in publish


def test_recursive_action_upgrade_keeps_validation_and_operational_triggers():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in workflow
    assert "group: recursive-code-meta-evolution-main" in workflow
    assert '    - cron: "11 * * * *"' in workflow
    assert "  workflow_dispatch:" in workflow
    assert "  pull_request:" in workflow
    assert "  push:\n    branches: [main]" in workflow

    assert workflow.count("uses: actions/checkout@v5") == 2
    assert workflow.count("uses: actions/setup-python@v6") == 2
    assert "uses: actions/checkout@v4" not in workflow
    assert "uses: actions/setup-python@v5" not in workflow
    assert workflow.count('python-version: "3.12"') == 2
    assert "python -m pytest -q tests/test_recursive_self_evolution_agent.py tests/test_recursive_evolution_workflow_security.py" in workflow
    assert workflow.count('      - "tests/test_recursive_evolution_workflow_security.py"') == 2
    assert "git diff --exit-code -- loto7.csv loto7_agent_output/" in workflow
