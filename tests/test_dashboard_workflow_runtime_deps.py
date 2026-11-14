"""Prevent dashboard scheduled/workflow_run jobs from missing runtime packages."""
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/dashboard_ops_snapshot.yml"


def test_dashboard_dependencies_installed_on_every_event_before_execution():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" in text
    assert "workflow_run:" in text
    start = text.index("      - name: Install dashboard runtime dependencies for all triggers")
    stop = text.index("      - name: Validate telemetry builder and UI", start)
    install_step = text[start:stop]
    # No conditional allowed: cron and upstream workflow completions
    # must install dependencies even when validation is intentionally skipped.
    assert not any(line.lstrip().startswith("if:") for line in install_step.splitlines())
    assert "python -m pip install -r requirements.txt" in install_step
    assert "import numpy, pandas" in install_step
    assert stop < text.index("      - name: Update only public snapshot on main")
    # Validation remains conditional; runtime installation must not be.
    validation = text[stop:text.index("      - name: Dry run (PR only)", stop)]
    assert "if: github.event_name" in validation
    assert "tests/test_dashboard_workflow_runtime_deps.py" in validation


def test_privileged_workflow_run_requires_successful_first_party_main():
    text = WORKFLOW.read_text(encoding="utf-8")
    # Restrict the trigger itself, then fail closed again at the job boundary.
    trigger = text.split("  workflow_run:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
    assert 'LOTO7 Independent Result Corroboration' in trigger
    assert 'Weekly Production Publisher' in trigger
    assert "types: [completed]" in trigger
    assert "branches: [main]" in trigger

    job = text.split("  build-public-status:\n", 1)[1].split("    runs-on:", 1)[0]
    assert "if: >-" in job
    assert "github.event_name != 'workflow_run' ||" in job
    assert "github.event.workflow_run.conclusion == 'success'" in job
    assert "github.event.workflow_run.head_branch == 'main'" in job
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in job
    assert "&&" in job

    # Scheduled refresh, main pushes, manual dispatch and PR dry-runs remain.
    assert '    - cron: "13,43 * * * *"' in text
    assert "  pull_request:" in text
    assert "  push:" in text
    assert "  schedule:" in text
    assert "  workflow_dispatch:" in text
    assert "      - name: Dry run (PR only)" in text
    publish = text.split("      - name: Update only public snapshot on main", 1)[1]
    assert "if: github.event_name != 'pull_request'" in publish


def test_workflow_run_trust_gate_cannot_be_accidentally_removed():
    # These checks deliberately enforce independent event provenance checks.
    text = WORKFLOW.read_text(encoding="utf-8")
    gate = text.split("    if: >-\n", 1)[1].split("    runs-on:", 1)[0]
    checks = (
        "github.event.workflow_run.conclusion",
        "github.event.workflow_run.head_branch",
        "github.event.workflow_run.head_repository.full_name",
    )
    assert all(check in gate for check in checks)
    assert "github.event_name != 'workflow_run'" in gate
    assert "github.repository" in gate
