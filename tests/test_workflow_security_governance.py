"""Workflow security governance checks (2026-11-24 audit follow-up #2).

Static, read-only checks: every action is SHA-pinned, Dependabot keeps
the pins moving, and the write-permission inventory stays complete.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
USES = re.compile(r"uses:\s*([^\s#]+)(?:\s*#\s*(v\d+))?")


def _workflow_files():
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


def test_all_actions_pinned_to_full_sha_with_version_comment():
    offenders = []
    for path in _workflow_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = USES.search(line)
            if not m:
                continue
            ref, version = m.group(1), m.group(2)
            sha = ref.rsplit("@", 1)[-1]
            if not re.fullmatch(r"[0-9a-f]{40}", sha) or version is None:
                offenders.append(f"{path.name}: {ref}")
    assert not offenders, f"Unpinned action references: {offenders}"


def test_dependabot_covers_github_actions_weekly():
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in text
    assert 'interval: "weekly"' in text


def test_permissions_inventory_covers_every_workflow():
    doc = (ROOT / "WORKFLOW_PERMISSIONS_INVENTORY.md").read_text(encoding="utf-8")
    missing = [p.name for p in _workflow_files() if p.name not in doc]
    assert not missing, f"Workflows missing from inventory: {missing}"


def test_no_workflow_requests_unreviewed_write_scopes():
    allowed = {"contents: write", "actions: write"}
    offenders = []
    for path in _workflow_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.search(r"^\s+([a-z-]+):\s*write\s*$", line)
            if m and f"{m.group(1)}: write" not in allowed:
                offenders.append(f"{path.name}: {m.group(1)}: write")
    assert not offenders, f"Unreviewed write scopes: {offenders}"


def test_retired_external_db_integration_is_absent():
    for relative in ("sakura", "prediction_db_sync.py", "verify_sakura_rotation.py",
                     ".github/workflows/sync_sakura_prediction_db.yml",
                     ".github/workflows/verify_sakura_credential_rotation.yml"):
        assert not (ROOT / relative).exists(), relative
    for path in _workflow_files():
        workflow = path.read_text(encoding="utf-8")
        for forbidden in ("prediction_db_sync.py", "verify_sakura_rotation.py",
                          "SAKURA_PREDICTION_", "--credential-rotation-status"):
            assert forbidden not in workflow, f"{path.name}: {forbidden}"
