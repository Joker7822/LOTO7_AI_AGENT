"""Prevent dashboard fanout and workflow inventory regressions."""
from pathlib import Path

import workflow_inventory as inventory


def test_workflow_inventory_and_dashboard_cadence():
    rows = inventory.scan_workflows(Path(".github/workflows"))
    assert len(rows) >= 49
    dashboard = next(x for x in rows if x["file"] == "dashboard_ops_snapshot.yml")
    assert dashboard["cron"] == ["13,43 * * * *"]
    assert dashboard["workflow_run_dependencies"] == [
        "LOTO7 Independent Result Corroboration", "Weekly Production Publisher"]
    assert dashboard["has_concurrency"] is True
    assert "git pushあり" in inventory.report(rows)
    assert "dashboard_ops_snapshot.yml" in inventory.report(rows)


def test_detect_duplicate_workflow_labels(tmp_path):
    (tmp_path / "a.yml").write_text("name: example\non:\n  schedule:\n    - cron: '0 0 * * *'\n")
    (tmp_path / "b.yml").write_text("name: example\non:\n  workflow_dispatch:\n")
    rows = inventory.scan_workflows(tmp_path)
    assert len(rows) == 2
    try:
        inventory.report(rows)
        assert False, "duplicate workflows must be rejected"
    except ValueError as exc:
        assert "duplicate" in str(exc)
