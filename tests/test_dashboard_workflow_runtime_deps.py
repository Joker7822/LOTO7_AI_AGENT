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
