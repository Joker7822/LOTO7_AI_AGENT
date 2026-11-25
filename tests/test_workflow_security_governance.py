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
    allowed = {"contents: write", "actions: write", "issues: write"}
    offenders = []
    for path in _workflow_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.search(r"^\s+([a-z-]+):\s*write\s*$", line)
            if m and f"{m.group(1)}: write" not in allowed:
                offenders.append(f"{path.name}: {m.group(1)}: write")
    assert not offenders, f"Unreviewed write scopes: {offenders}"


def test_high_frequency_research_publishers_use_separate_main_only_write_jobs():
    jobs = {
        "always_on_accuracy_research.yml": "bounded-research",
        "frequent_online_research_feed.yml": "search-verify-triage",
        "advanced_validation_lab.yml": "scientific-validation",
    }
    for filename, job in jobs.items():
        workflow = (WORKFLOWS / filename).read_text(encoding="utf-8")
        verify, publish = workflow.split("  publish-research-only:\n", 1)
        header = publish.split("    steps:\n", 1)[0]
        assert "permissions:\n  contents: read" in verify, filename
        assert "contents: write" not in verify, filename
        assert "persist-credentials: false" in verify, filename
        assert "persist-credentials: true" not in verify, filename
        assert "git push origin HEAD:main" not in verify, filename
        assert f"needs: {job}" in header, filename
        assert f"needs.{job}.result == 'success'" in header, filename
        assert "github.event_name != 'pull_request' &&" in header, filename
        assert "github.ref == 'refs/heads/main' &&" in header, filename
        assert "permissions:\n      contents: write" in header, filename
        assert workflow.count("contents: write") == 1, filename
        assert "persist-credentials: true" in publish, filename
        assert "git push origin HEAD:main" in publish, filename
        assert "unexpected=" in publish, filename


def test_hourly_privileged_workflow_run_requires_trusted_main_predecessor():
    workflow = (WORKFLOWS / "always_on_accuracy_research.yml").read_text(encoding="utf-8")
    trigger = workflow.split("  workflow_run:\n", 1)[1].split("  pull_request:", 1)[0]
    assert "branches: [main]" in trigger
    header = workflow.split("  publish-research-only:\n", 1)[1].split("    steps:\n", 1)[0]
    assert "github.event.workflow_run.conclusion == 'success'" in header
    assert "github.event.workflow_run.head_branch == 'main'" in header
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in header
    assert "github.event.workflow_run.event != 'pull_request'" in header
