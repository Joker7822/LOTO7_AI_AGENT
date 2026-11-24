"""Governance regression checks from the 2026-11-24 audit follow-up.

Read-only static checks: they never touch production ledgers, champion
state, or registered future-OOS evidence.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_one_time_production_702_recovery_workflow_removed():
    gone = ROOT / ".github" / "workflows" / "production_702_one_time_recovery.yml"
    assert not gone.exists(), (
        "Dormant write-privileged one-time recovery workflow for the "
        "already-completed round 702 must not remain in the workflow inventory."
    )


def test_policy_override_is_registered_as_non_statistical():
    registry = json.loads(
        (ROOT / "policy_overrides" / "roi_cash_v2.json").read_text(encoding="utf-8")
    )
    assert registry["type"] == "operator_policy_override"
    assert registry["statistical_promotion"] is False
    assert registry["number_selection_changed"] is False
    assert registry["accounting"] == "separate_from_statistical_promotion"
    doc = (ROOT / "POLICY_OVERRIDES.md").read_text(encoding="utf-8")
    assert "roi-cash-v2" in doc
    assert "別会計" in doc


def test_research_expansion_policy_has_stop_conditions():
    doc = (ROOT / "RESEARCH_EXPANSION_POLICY.md").read_text(encoding="utf-8")
    assert "net-zero" in doc
    assert "holdout" in doc


def test_license_present():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
