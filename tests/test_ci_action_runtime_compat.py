"""Guard the CI/dashboard action pins (full SHA, current majors).

These assertions cover the action runner dependencies, not the intentionally
pinned Node.js version used by the dashboard's UI tests.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
DASHBOARD = ROOT / ".github/workflows/dashboard_ops_snapshot.yml"


def test_primary_ci_action_versions_use_node24_runtimes():
    text = CI.read_text(encoding="utf-8")
    assert "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7" in text
    assert "uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7" in text
    assert "uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7" in text
    assert "actions/checkout@" in text and "checkout@v" not in text
    assert "setup-python@v" not in text
    assert "upload-artifact@v" not in text
    # Keep the original Python dependency cache and provenance artifact.
    assert "cache: pip" in text
    assert "retention-days: 30" in text
    assert "permissions:\n  contents: read" in text


def test_dashboard_action_upgrade_preserves_separate_job_permissions():
    text = DASHBOARD.read_text(encoding="utf-8")
    validate, publisher = text.split("  build-public-status:\n", 1)
    assert validate.count("uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7") == 1
    assert publisher.count("uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7") == 1
    assert validate.count("uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7") == 1
    assert publisher.count("uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7") == 1
    assert "uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7" in validate
    assert 'node-version: "22"' in validate
    assert "package-manager-cache: false" in validate
    for old in ("actions/checkout@v", "actions/setup-python@v",
                "actions/setup-node@v"):
        assert old not in text
    assert "persist-credentials: false" in validate
    assert "persist-credentials: true" in publisher
    assert "needs.validate-public-status.result == 'success'" in publisher
    assert "github.ref == 'refs/heads/main'" in publisher
