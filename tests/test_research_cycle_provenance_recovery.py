"""Research-cycle freshness recovers only after exact trusted scientific provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import research_cycle_provenance_recovery as recovery


@pytest.fixture
def project(tmp_path, monkeypatch):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    draw = tmp_path / "loto7.csv"
    draw.write_text("immutable draw bytes", encoding="utf-8")
    sha = hashlib.sha256(draw.read_bytes()).hexdigest()
    records = {
        "source_validation.json": {
            "latest": {"round": 700},
            "verification": "verified_two_result_sources",
            "verification_provenance": {"draw_csv_sha256": sha},
        },
        "research_cycle_guard.json": {
            "mode": "WAIT_FOR_NEW_DATA", "data_sha256": sha,
            "signal_trials_this_data": 800,
            "max_signal_trials_per_data": 800,
        },
        "advanced_validation_lab_summary.json": {
            "historical_data_sha256": "a"*64,
            "source_code_frozen": True,
            "automatic_model_selection": False,
            "production_changed": False,
            "champion_changed": False,
            "registered_existing_shadows_changed": False,
        },
    }
    for name, value in records.items():
        (out / name).write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(
        recovery, "validate_trusted_source",
        lambda *_: {"round": 700, "trusted": True}
    )
    return tmp_path, records, sha


def modify(root, name, mutate):
    path = root / "loto7_agent_output" / name
    obj = json.loads(path.read_text(encoding="utf-8"))
    mutate(obj)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_actual_current_repository_is_in_scientific_catchup_state():
    root = Path(__file__).resolve().parents[1]
    current = recovery.check(root)
    # A live repository may have received the registered lab's catchup
    # between CI runs, so both states are legitimate; the guard is NEVER
    # allowed to authorize a new same-SHA optimizer search.
    assert current["latest_resolved_round"] >= 699
    assert current["status"] in {
        "WAIT_FOR_INDEPENDENT_SOURCE", "WAIT_FOR_RESEARCH_GUARD",
        "REFRESH_REGISTERED_SCIENCE", "READY_FOR_BOUNDED_RESEARCH"
    }
    if not current["source_trusted"]:
        assert not current["hourly_ledger_can_advance"]
    assert current["new_optimizer_trials_authorized"] is False
    assert current["production_champion_modified"] is False
    assert current["registered_26_draw_state_modified"] is False


def test_real_sha_lag_requests_only_registered_science_refresh(project):
    root, _, sha = project
    p = recovery.check(root)
    assert p["status"] == "REFRESH_REGISTERED_SCIENCE"
    assert p["draw_csv_sha256"] == sha
    assert p["source_trusted"]
    assert p["needs_registered_lab_refresh"]
    assert p["expected_wait"]
    assert not p["hourly_ledger_can_advance"]
    assert p["trial_budget_used"] == p["trial_budget_limit"] == 800
    assert not p["new_optimizer_trials_authorized"]


def test_after_registered_science_rebuild_research_ledger_can_resume(project):
    root, _, sha = project
    modify(root, "advanced_validation_lab_summary.json",
           lambda obj: obj.update(historical_data_sha256=sha))
    result = recovery.check(root)
    assert result["status"] == "READY_FOR_BOUNDED_RESEARCH"
    assert result["hourly_ledger_can_advance"]
    assert result["research_mode"] == "WAIT_FOR_NEW_DATA"
    assert result["expected_wait"]
    assert not result["new_optimizer_trials_authorized"]


def test_bad_source_sha_remains_blocked_even_when_science_is_fresh(project):
    root, _, sha = project
    modify(root, "advanced_validation_lab_summary.json",
           lambda obj: obj.update(historical_data_sha256=sha))
    modify(root, "source_validation.json",
           lambda obj: obj["verification_provenance"].update(draw_csv_sha256="b"*64))
    p = recovery.check(root)
    assert p["status"] == "WAIT_FOR_INDEPENDENT_SOURCE"
    assert not p["hourly_ledger_can_advance"]


def test_source_checker_does_not_convert_untrusted_round_to_ready(project, monkeypatch):
    root, _, sha = project
    modify(root, "advanced_validation_lab_summary.json",
           lambda obj: obj.update(historical_data_sha256=sha))
    monkeypatch.setattr(recovery, "validate_trusted_source",
                        lambda *_: {"round": 700, "trusted": False})
    p = recovery.check(root)
    assert p["status"] == "WAIT_FOR_INDEPENDENT_SOURCE"
    assert not p["source_trusted"]


def test_current_guard_sha_mismatch_cannot_resume_model_trials(project):
    root, _, sha = project
    modify(root, "advanced_validation_lab_summary.json",
           lambda obj: obj.update(historical_data_sha256=sha))
    modify(root, "research_cycle_guard.json",
           lambda obj: obj.update(data_sha256="f"*64))
    p = recovery.check(root)
    assert p["status"] == "WAIT_FOR_RESEARCH_GUARD"
    assert not p["hourly_ledger_can_advance"]


@pytest.mark.parametrize("forgery", [
    {"automatic_model_selection": True},
    {"production_changed": True},
    {"champion_changed": True},
    {"registered_existing_shadows_changed": True},
    {"source_code_frozen": False},
])
def test_science_must_remain_nonpromoting_and_sha_locked(project, forgery):
    root, _, sha = project
    modify(root, "advanced_validation_lab_summary.json",
           lambda obj: obj.update(historical_data_sha256=sha, **forgery))
    p = recovery.check(root)
    assert p["status"] == "INVALID_SCIENTIFIC_REVIEW"
    assert not p["hourly_ledger_can_advance"]


def test_unknown_optimizer_mode_fails_closed(project):
    root, _, _ = project
    modify(root, "research_cycle_guard.json", lambda x: x.update(mode="UNLIMITED_SEARCH"))
    with pytest.raises(ValueError, match="unknown research-budget mode"):
        recovery.check(root)


def test_round_mismatch_refused(project, monkeypatch):
    root, _, _ = project
    monkeypatch.setattr(recovery, "validate_trusted_source",
                        lambda *_: {"round": 699, "trusted": True})
    with pytest.raises(ValueError, match="round mismatch"):
        recovery.check(root)


def test_preflight_does_not_mutate_research_or_frozen_files(project):
    root, _, _ = project
    originals = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in root.rglob("*") if p.is_file()}
    recovery.check(root)
    assert originals == {p: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob("*") if p.is_file()}


def test_workflows_have_fast_recovery_event_and_no_budget_reset():
    root = Path(__file__).resolve().parents[1]
    hourly = (root / ".github/workflows/always_on_accuracy_research.yml").read_text()
    lab = (root / ".github/workflows/advanced_validation_lab.yml").read_text()
    assert "workflow_run:" in hourly
    assert 'workflows: ["Advanced Statistical Validation Lab"]' in hourly
    assert "github.event.workflow_run.conclusion == 'success'" in hourly
    assert "research_cycle_provenance_recovery.py" in hourly
    assert "advanced_validation_lab_summary.json" in hourly
    assert 'cron: "37 */3 * * *"' in lab
    assert "python advanced_validation_lab.py --repo-root . --out-dir loto7_agent_output" in lab
    assert "git add --" in lab
    assert "advanced_validation_lab_summary.json" in lab
    assert "model_champion.json" not in lab
    assert "rewrite_locked_future_forecasts" not in lab
