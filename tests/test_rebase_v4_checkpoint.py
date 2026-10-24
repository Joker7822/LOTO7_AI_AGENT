"""Regression for two concurrent bots updating historical research and source proof."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rebase_v4_checkpoint.sh"


def git(directory: Path, *args: str, check=True):
    return subprocess.run(
        ["git", *args], cwd=directory, text=True, capture_output=True,
        check=check, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    )


def setup_race(tmp_path: Path, remote_is_verified=True):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    setup = tmp_path / "init"
    setup.mkdir()
    git(setup, "init", "-b", "main")
    git(setup, "config", "user.email", "ci@example.invalid")
    git(setup, "config", "user.name", "CI")
    (setup / "loto7_agent_output").mkdir()
    shutil.copyfile(ROOT / "loto7.csv", setup / "loto7.csv")
    # CI also replays tests against a pinned 699 snapshot, which may be
    # degraded. Create a *clearly synthetic* corroboration inside this
    # disposable Git test fixture only, never in the real repository.
    from fetch_validate import latest_row, read_rows, validate_row
    latest = validate_row(latest_row(read_rows(setup / "loto7.csv")))
    original = {
        "status": "ok", "verification": "verified_two_result_sources",
        "latest": latest,
        "sources": {"synthetic_fixture_publisher": dict(latest)},
        "checked_at_jst": "2026-10-24T16:00:00+09:00",
    }
    base = dict(original)
    base["status"] = "degraded"
    base["verification"] = "degraded_single_result_source"
    base["checked_at_jst"] = "2026-10-24T10:00:00+09:00"
    # No separate official evidence needs to be manufactured in this test.
    (setup / "loto7_agent_output/source_validation.json").write_text(json.dumps(base))
    (setup / "loto7_agent_output/v4_research_state.json").write_text('{"generation":1}')
    git(setup, "add", ".")
    git(setup, "commit", "-m", "baseline")
    git(setup, "remote", "add", "origin", str(remote))
    git(setup, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    researcher = tmp_path / "researcher"
    verifier = tmp_path / "verifier"
    git(tmp_path, "clone", str(remote), str(researcher))
    git(tmp_path, "clone", str(remote), str(verifier))
    for clone in (researcher, verifier):
        git(clone, "config", "user.email", "ci@example.invalid")
        git(clone, "config", "user.name", "CI")
    # Long-running v4 cloned the outdated source and then changed it locally.
    local = dict(base)
    local["checked_at_jst"] = "2026-10-24T15:00:00+09:00"
    (researcher / "loto7_agent_output/source_validation.json").write_text(json.dumps(local))
    (researcher / "loto7_agent_output/v4_research_state.json").write_text('{"generation":2}')
    git(researcher, "add", ".")
    git(researcher, "commit", "-m", "local research checkpoint")
    incoming = original if remote_is_verified else {**base, "checked_at_jst": "2026-10-24T16:00:00+09:00"}
    (verifier / "loto7_agent_output/source_validation.json").write_text(json.dumps(incoming))
    git(verifier, "add", ".")
    git(verifier, "commit", "-m", "new remote independent source")
    git(verifier, "push", "origin", "main")
    return researcher, original


def test_concurrent_verified_source_is_never_downgraded(tmp_path):
    researcher, verified = setup_race(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=researcher, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)}, timeout=50
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    state = json.loads((researcher / "loto7_agent_output/v4_research_state.json").read_text())
    assert state == {"generation": 2}
    published = json.loads((researcher / "loto7_agent_output/source_validation.json").read_text())
    assert published == verified
    git(researcher, "push", "origin", "main")


def test_conflicting_unverified_remote_stays_unpublished(tmp_path):
    researcher, _ = setup_race(tmp_path, remote_is_verified=False)
    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=researcher, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)}, timeout=50
    )
    assert result.returncode != 0
    assert "Cannot safely reconcile" in result.stdout + result.stderr
    assert not (researcher / ".git/rebase-merge").exists()
