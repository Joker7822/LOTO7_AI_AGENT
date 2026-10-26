"""Online literature's operational QA use, without grants of research authority."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

import online_research_operational_audit as ops

REPO = Path(__file__).resolve().parents[1]


def verified_repository_or_skip():
    status = ops.trust.validate_trusted_source(
        REPO / "loto7.csv",
        REPO / "loto7_agent_output" / "source_validation.json",
    )
    if status.get("trusted") is not True:
        # The repository's full regression suite deliberately runs against
        # pinned 699 historical evidence with degraded verification. The
        # operational report MUST reject that fixture rather than granting
        # it trusted scientific status. Dedicated CI exercises current 700.
        with pytest.raises(ValueError, match="not independently verified"):
            ops.make_operational_report(REPO)
        pytest.skip("pinned regression fixture has untrusted source by design")
    return ops.make_operational_report(REPO)


def load_checked(path):
    return json.loads((REPO / "loto7_agent_output" / path).read_text())


def test_real_repository_creates_guarded_operational_diagnostic_in_memory():
    result = verified_repository_or_skip()
    assert result["version"] == ops.VERSION
    assert result["latest_verified_draw"] >= 700
    assert result["input_provenance"]["source_status"] == "verified_two_result_sources"
    assert result["pre_registered_future_streams"]["existing_holdout"]["horizon"] == 26
    assert result["pre_registered_future_streams"]["joint_v2"]["horizon"] == 26
    assert result["pre_registered_future_streams"]["disjoint35_research"]["horizon"] == 26
    assert len(result["applied_operational_uses"]) > 0
    assert not result["forecast_skill_established"]
    assert not result["automatic_promotion_allowed"]
    assert not result["production_changed"]
    assert not result["existing_oos_changed"]
    assert not result["research_budget_increased"]
    assert result["new_research_experiments_executed"] == 0
    assert result["fair_world_geometry_controls"]["disjoint35_score"] > (
        result["fair_world_geometry_controls"]["one_overlap34_score"]
    )
    assert "read_only" in result["purpose"]
    assert "Operational Quality Audit" in ops.report_text(result)


def test_stale_699_research_is_not_presented_as_current():
    # Old reports must never be silently considered current, regardless of
    # which trusted draw is latest in this checkout.
    # Update this invariant when the authorized research pipeline catches up.
    record = verified_repository_or_skip()
    gate = load_checked("research_application_readiness.json")
    if gate["latest_round"] < record["latest_verified_draw"]:
        assert record["input_provenance"]["online_readiness_data_match"] is False
        assert "online_research_readiness_stale" in record["blockers"]
        assert "Refresh science/review inputs" in record["recommended_next_step"]


@pytest.mark.parametrize("field,value", [
    ("auto_production_release", True),
    ("automatic_model_training", True),
    ("new_experiments_executed", 1),
    ("future_oos_or_production_changed", True),
])
def test_reject_unsafe_gate_mutations(field, value):
    gate = load_checked("research_application_readiness.json")
    plans = load_checked("research_experiment_proposals.json")
    bibliography = load_checked("research_verified_publications.json")
    gate[field] = value
    with pytest.raises(ValueError):
        ops.validate_no_unapproved_execution(gate, plans, bibliography)


@pytest.mark.parametrize("field,value", [
    ("executed_experiments", 1),
    ("new_trials_consumed", 1),
    ("production_modified", True),
    ("requires_human_approval", False),
])
def test_refuse_paper_queue_authority_escalation(field, value):
    gate = load_checked("research_application_readiness.json")
    plans = load_checked("research_experiment_proposals.json")
    bibliography = load_checked("research_verified_publications.json")
    plans[field] = value
    with pytest.raises(ValueError):
        ops.validate_no_unapproved_execution(gate, plans, bibliography)


def test_reject_new_paper_as_approved_or_source_to_new_trials():
    gate = load_checked("research_application_readiness.json")
    plans = load_checked("research_experiment_proposals.json")
    bibliography = load_checked("research_verified_publications.json")
    plans["proposals"][0]["code_execution_authorized"] = True
    with pytest.raises(ValueError, match="unauthorized trial"):
        ops.validate_no_unapproved_execution(gate, plans, bibliography)


def test_reject_new_approval_in_work_queue():
    gate = load_checked("research_application_readiness.json")
    plans = load_checked("research_experiment_proposals.json")
    bibliography = load_checked("research_verified_publications.json")
    gate["application_queue"][0]["production_adoption_allowed"] = True
    with pytest.raises(ValueError, match="application gate queue"):
        ops.validate_no_unapproved_execution(gate, plans, bibliography)


def test_in_memory_audit_leaves_all_protected_data_bytes_unchanged():
    originals = {
        path: hashlib.sha256((REPO / path).read_bytes()).hexdigest()
        for path in ops.READONLY_INPUTS
    }
    first = verified_repository_or_skip()
    second = verified_repository_or_skip()
    assert first == second
    for path, checksum in originals.items():
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == checksum


def test_operational_report_is_reproducible_and_omits_number_predictions():
    record = verified_repository_or_skip()
    text = ops.report_text(record)
    assert text == ops.report_text(record)
    assert record["forecast_skill_established"] is False
    assert record["unreviewed_external_code_executed"] is False
    assert record["automatic_promotion_allowed"] is False
    assert "first-prize probability" in text
    assert "new trial budget" in text
    assert "prediction_tickets" not in json.dumps(record)
