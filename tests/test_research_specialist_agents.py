"""Regression tests for four separately runnable, read-only specialists."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import research_specialist_agents as specialists

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("agent", specialists.AGENTS)
def test_each_specialist_executes_with_bounded_authority(agent):
    result = specialists.execute(ROOT, agent)
    assert result["version"] == specialists.VERSION
    assert result["agent"] == agent
    assert result["status"] in {"pass", "watch", "block"}
    assert result["decision"] == "advisory_only_no_model_release"
    assert not any(result["permissions"].values())
    assert result["new_real_experiments_executed"] == 0
    assert result["model_prediction_skill_claimed"] is False
    assert result["existing_oos_changed"] is False
    assert result["production_changed"] is False
    assert result["inputs_are_read_only"]
    assert 2 <= len(result["checks"]) <= 10
    assert all(v["status"] in {"pass", "watch", "block"} for v in result["checks"])


def test_registered_agents_are_distinct_and_deterministic():
    results = [specialists.execute(ROOT, a) for a in specialists.AGENTS]
    assert len(results) == 4
    assert len({r["agent"] for r in results}) == 4
    assert len({c["code"] for r in results for c in r["checks"]}) == sum(
        len(r["checks"]) for r in results
    )
    for name, record in zip(specialists.AGENTS, results):
        assert record == specialists.execute(ROOT, name)


def test_source_guard_blocks_pinned_699_or_marks_trusted_700():
    item = specialists.execute(ROOT, "source_sentinel")
    assert "draw_sha256" in item["context"]
    verified = item["context"]["claimed_verified"]
    names = {c["code"]: c for c in item["checks"]}
    assert "two_source_trust" in names
    if verified:
        assert names["two_source_trust"]["status"] == "pass"
    else:
        assert names["two_source_trust"]["status"] == "block"
        assert item["status"] == "block"


def test_calibration_never_claims_improved_future_accuracy():
    item = specialists.execute(ROOT, "calibration_analyst")
    assert item["context"]["future_predictive_edge_confirmed"] is False
    assert item["context"]["top7_uniform_expected_matches"] == pytest.approx(49 / 37)
    assert item["context"]["historical_p_value_descriptive_only"] >= 0
    assert item["context"]["historical_p_value_descriptive_only"] <= 1
    assert item["status"] == "watch"


def test_prospective_ledger_remains_locked_and_incomplete():
    item = specialists.execute(ROOT, "prospective_custodian")
    counts = item["context"]["trusted_draws_by_stream"]
    assert all(0 <= n <= 26 for n in counts.values())
    assert item["context"]["fixed_horizon"] == 26
    assert 701 in item["context"]["prefrozen_research_targets"]
    assert item["context"]["formal_automatic_promotion_eligible"] is False


def test_literature_does_not_execute_online_instructions():
    item = specialists.execute(ROOT, "literature_examiner")
    assert item["context"]["paper_method_training_approved"] is False
    assert item["context"]["draft_proposals"] >= 1
    assert item["context"]["full_text_reviewed_count"] == 0
    assert item["status"] == "watch"


def test_trusted_output_only_uses_disposable_result_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fingerprints = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in specialists.safety.READONLY_INPUTS
    }
    for name in specialists.AGENTS:
        report = specialists.execute(ROOT, name)
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(report, ensure_ascii=False))
        assert json.loads(path.read_text())["agent"] == name
    assert len(list(tmp_path.glob("*.json"))) == 4
    for name, old in fingerprints.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == old


def test_forbidden_agent_or_unknown_severity_fail_closed():
    with pytest.raises(ValueError, match="unregistered"):
        specialists.execute(ROOT, "auto_champion_promoter")
    with pytest.raises(ValueError, match="severity"):
        specialists.issue("paper", "promoted", "suspicious")


def test_approval_guard_disallows_human_review_shortcuts(monkeypatch):
    original = specialists.load
    def injected(root, name):
        obj = original(root, name)
        if name.endswith("research_experiment_proposals.json"):
            obj = copy.deepcopy(obj)
            obj["proposals"][0]["code_execution_authorized"] = True
        return obj
    monkeypatch.setattr(specialists, "load", injected)
    with pytest.raises(ValueError, match="unauthorized"):
        specialists.execute(ROOT, "literature_examiner")


def test_bad_registered_future_protocol_fails_closed(monkeypatch):
    original = specialists.future_geometry.register_guard
    def bad(*args):
        raise RuntimeError("source fingerprint lock mismatch")
    monkeypatch.setattr(specialists.future_geometry, "register_guard", bad)
    with pytest.raises(RuntimeError, match="lock mismatch"):
        specialists.execute(ROOT, "prospective_custodian")
    monkeypatch.setattr(specialists.future_geometry, "register_guard", original)


def test_declared_verified_but_untrusted_source_is_rejected(monkeypatch):
    original = specialists.load
    def modified(root, name):
        obj = original(root, name)
        if name.endswith("source_validation.json"):
            obj = copy.deepcopy(obj)
            obj["verification"] = "verified_two_result_sources"
        return obj
    monkeypatch.setattr(specialists, "load", modified)
    monkeypatch.setattr(specialists.source_guard, "validate_trusted_source",
                        lambda *_: {"trusted": False, "round": None})
    with pytest.raises(ValueError, match="failed independent trust guard"):
        specialists.execute(ROOT, "source_sentinel")
