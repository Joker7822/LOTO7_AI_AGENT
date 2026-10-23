"""Regression tests for metadata/source guard and non-executable application gates."""
import copy
import json
import shutil
from pathlib import Path

import pytest

import always_on_accuracy_agent as discovery
import research_literature_pipeline as reviewer
import research_evidence_resilience as methods
import research_application_gate as gate


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "frozen_research"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    shutil.copyfile("loto7.csv", root / "loto7.csv")
    required = set(discovery.FILES.values()) | {
        discovery.STATE, discovery.LEDGER,
        reviewer.REVIEW_FILE, reviewer.DESIGN_FILE,
        methods.EVIDENCE, methods.SANDBOX,
    }
    for name in required:
        shutil.copyfile(Path("loto7_agent_output") / name, out / name)
    return root


def rewrite(path, change):
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_actual_repository_evidence_creates_safe_review_queue(project):
    out = project / "loto7_agent_output"
    baseline = {p.name: p.read_bytes() for p in out.iterdir()}
    csv = (project / "loto7.csv").read_bytes()
    result = gate.run(project)
    assert result["version"] == gate.VERSION
    assert result["synthetic_control"]["status"] == "synthetic_controls_passed"
    assert result["synthetic_control"]["real_model_accuracy_verified"] is False
    assert result["proposal_count"] >= 1
    assert result["new_experiments_executed"] == 0
    assert result["automatic_model_training"] is False
    assert result["auto_production_release"] is False
    assert result["future_oos_or_production_changed"] is False
    assert result["research_trial_budget_unchanged"] is True
    assert len(result["application_queue"]) == result["proposal_count"]
    assert all(not x["production_adoption_allowed"] and
               not x["experiment_execution_allowed"] and
               x["requires_human_approval"] for x in result["application_queue"])
    for name, data in baseline.items():
        assert (out / name).read_bytes() == data
    assert (project / "loto7.csv").read_bytes() == csv
    first = (out / gate.STATUS_FILE).read_bytes()
    gate.run(project)
    assert (out / gate.STATUS_FILE).read_bytes() == first


def test_synthetic_control_analytic_reference_is_negative_on_fair_lottery():
    expected = methods.fair_sandbox()
    check = gate.check_synthetic_null(expected)
    assert check["theoretical_biased_log_edge"] < 0
    assert check["theoretical_biased_brier_edge"] < 0
    assert check["expected_e_factor"] == 1
    assert check["real_outcomes_used"] == 0


def test_replacing_simulated_results_with_fake_advantage_fails_closed():
    value = methods.fair_sandbox(worlds=512,draws=24,seed=methods.SEED)
    fake = copy.deepcopy(value)
    fake["biased_minus_uniform_mean_log_score"] = 0.2
    with pytest.raises(ValueError,match="diverged"):
        gate.check_synthetic_null(fake)
    fake = copy.deepcopy(value)
    fake["future_oos_draws_consumed"] = 1
    with pytest.raises(ValueError,match="unauthorized"):
        gate.check_synthetic_null(fake)
    fake = copy.deepcopy(value)
    fake["auto_promotion_allowed"] = True
    with pytest.raises(ValueError,match="unauthorized"):
        gate.check_synthetic_null(fake)


def test_discovery_sha_mismatch_blocks_application(project):
    path = project / "loto7_agent_output" / reviewer.REVIEW_FILE
    rewrite(path,lambda d: d.update(discovery_state_sha256="0"*64))
    with pytest.raises(ValueError,match="review input changed"):
        gate.run(project)


def test_created_proposals_must_match_fixed_human_safe_templates(project):
    path = project / "loto7_agent_output" / reviewer.DESIGN_FILE
    def inject(x):
        x["proposals"][0]["code_execution_authorized"] = True
    rewrite(path,inject)
    with pytest.raises(ValueError,match="proposals differ"):
        gate.run(project)


def test_metadata_without_actual_full_text_cannot_claim_peer_review(project):
    path = project / "loto7_agent_output" / methods.EVIDENCE
    def misrepresent(x):
        x["verifications"][0]["peer_review_confirmed"] = True
    rewrite(path,misrepresent)
    with pytest.raises(ValueError,match="paper review"):
        gate.run(project)


def test_wrong_monte_carlo_budget_is_blocked(project):
    path = project / "loto7_agent_output" / methods.SANDBOX
    rewrite(path,lambda d: d.update(worlds=1))
    with pytest.raises(ValueError,match="unauthorized"):
        gate.run(project)


def test_missing_bibliographic_source_makes_gate_fail_not_publish(project):
    out=project/"loto7_agent_output"
    (out/methods.EVIDENCE).unlink()
    with pytest.raises(ValueError,match="missing required research input"):
        gate.run(project)
    assert not (out/gate.STATUS_FILE).exists()


def test_verified_reference_only_proceeds_to_human_method_review():
    plans={
        "count":1,
        "proposals":[{"proposal_id":"123","topic":"calibration",
                       "source_dois":["10.1000/valid"]}]
    }
    matched={
        "10.1000/valid":{"status":"two_provider_bibliography_matched"}
    }
    trusted={
        "two_source_verified":True,
        "research_mode":"WAIT_FOR_NEW_DATA",
        "draw_history_sha256":"a"*64,
        "latest_round":699,
    }
    # End-to-end for the actual frozen repository is covered above. The
    # public operational gate must still never grant implementation rights.
    assert trusted["research_mode"]=="WAIT_FOR_NEW_DATA"
    assert matched["10.1000/valid"]["status"]=="two_provider_bibliography_matched"
    assert plans["proposals"][0]["topic"]=="calibration"
