"""Guard the CI/dashboard migration away from deprecated Node 20 action runtimes.

These assertions cover the action runner dependencies, not the intentionally
pinned Node.js version used by the dashboard's UI tests.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
DASHBOARD = ROOT / ".github/workflows/dashboard_ops_snapshot.yml"


def test_primary_ci_action_versions_use_node24_runtimes():
    text = CI.read_text(encoding="utf-8")
    assert "uses: actions/checkout@v5" in text
    assert "uses: actions/setup-python@v6" in text
    assert "uses: actions/upload-artifact@v6" in text
    assert "uses: actions/checkout@v4" not in text
    assert "uses: actions/setup-python@v5" not in text
    assert "uses: actions/upload-artifact@v4" not in text
    # Keep the original Python dependency cache and provenance artifact.
    assert "cache: pip" in text
    assert "retention-days: 30" in text
    assert "permissions:\\n  contents: read" in text


def test_dashboard_action_upgrade_preserves_separate_job_permissions():
    text = DASHBOARD.read_text(encoding="utf-8")
    validate, publisher = text.split("  build-public-status:\n", 1)
    assert validate.count("uses: actions/checkout@v5") == 1
    assert publisher.count("uses: actions/checkout@v5") == 1
    assert validate.count("uses: actions/setup-python@v6") == 1
    assert publisher.count("uses: actions/setup-python@v6") == 1
    assert "uses: actions/setup-node@v5" in validate
    assert 'node-version: "22"' in validate
    assert "package-manager-cache: false" in validate
    for old in ("actions/checkout@v4", "actions/setup-python@v5",
                "actions/setup-node@v4"):
        assert old not in text
    assert "persist-credentials: false" in validate
    assert "persist-credentials: true" in publisher
    assert "needs.validate-public-status.result == 'success'" in publisher
    assert "github.ref == 'refs/heads/main'" in publisher
