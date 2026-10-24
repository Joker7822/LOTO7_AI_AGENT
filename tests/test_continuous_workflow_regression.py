"""Regression checks for v4 workflow bootstrap triggers.

The v4 job runs the complete pytest suite before its research loop. Changes to
tests or their shared inputs must therefore start a fresh workflow on main;
otherwise a test-only fix can leave the last research run marked as failed.
"""
from pathlib import Path


WORKFLOW = Path(".github/workflows/continuous_loto7_v4.yml")


def test_v4_push_paths_track_full_suite_and_shared_inputs():
    text = WORKFLOW.read_text(encoding="utf-8")
    paths = text.split("    paths:", 1)[1].split("  schedule:", 1)[0]
    for path in (
        '"tests/**"',
        '"requirements.txt"',
        '"loto7.csv"',
        '"loto7_evolving_agent.py"',
        '"agent_role_council.py"',
    ):
        assert f"- {path}" in paths, f"missing v4 push trigger: {path}"


def test_v4_checks_run_before_research_loop():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.index("name: Verify code once per runner") < text.index(
        "name: Run continuous v4 research"
    )
    assert "python -m pytest -q" in text
