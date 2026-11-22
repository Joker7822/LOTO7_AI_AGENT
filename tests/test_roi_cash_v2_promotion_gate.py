"""Prevent spurious historic cash-ROI windfalls from forcing Production promotion."""
from __future__ import annotations

from research.roi_cash_agent_v2 import VERSION
from research.roi_cash_v2_promotion_gate import evaluate_promotion


def retro(*,robust=False):
    return {
        "candidate_version":VERSION,
        "source_trust":"verified_two_result_sources",
        "production_promotion":False,
        "last_round":704,
        "retrospective_roi_all_checks_passed":robust,
    }


def future(n=26):
    return {
        "candidate_version":VERSION,
        "source_verification":"verified_two_result_sources",
        "protocol_frozen_before_first_draw":True,
        "independent_snapshot_audit_passed":True,
        "paired_rounds":[{
            "round":705+j,
            "source_verification":"verified_two_result_sources",
            "prediction_frozen_before_draw":True,
            "candidate_version":VERSION,
            "same_35_numbers_validated":True,
            "public_payout_complete":True,
            "cost_yen_per_arm":1500,
            "pre_draw_candidate_sha256":f"{j+1:064x}",
            "pre_draw_production_sha256":f"{j+80:064x}",
            "candidate_payout_yen":2000,
            "production_payout_yen":1000,
        } for j in range(n)],
    }


def test_no_future_data_is_never_evidence_even_with_large_historical_roi():
    result=evaluate_promotion(retro(robust=True))
    assert "incomplete_candidate_specific_26_round_future_oos" in result["reasons"]
    assert result["candidate_specific_future_review_ready"] is False
    assert result["auto_production_promotion"] is False


def test_historical_outlier_warning_can_be_overridden_only_by_verified_future():
    historical=evaluate_promotion(retro(robust=False))
    assert historical["retrospective_robust_roi_warning"] is True
    assert historical["eligible_for_independent_release_review"] is False
    independently_verified=evaluate_promotion(retro(robust=False),future())
    assert independently_verified["retrospective_robust_roi_warning"] is True
    assert independently_verified["eligible_for_independent_release_review"] is True
    assert independently_verified["auto_production_promotion"] is False


def test_future_roi_improvement_can_make_human_review_ready_only_after_valid_lock():
    result=evaluate_promotion(retro(robust=True),future())
    assert result["trusted_future_draws"]==26
    assert result["candidate_future_roi"]==2000/1500
    assert result["production_future_roi"]==1000/1500
    assert result["candidate_specific_future_review_ready"] is True
    assert result["auto_production_promotion"] is False


def test_future_cash_decline_blocks_release():
    data=future()
    for p in data["paired_rounds"]:
        p["candidate_payout_yen"]=0
    result=evaluate_promotion(retro(robust=True),data)
    assert "future_roi_not_greater_than_incumbent" in result["reasons"]
    assert result["candidate_specific_future_review_ready"] is False


def test_four_wins_cannot_prove_robust_roi():
    data=future()
    for p in data["paired_rounds"]:
        p["candidate_payout_yen"]=1000
    for p in data["paired_rounds"][:4]:
        p["candidate_payout_yen"]=100000
    result=evaluate_promotion(retro(robust=True),data)
    assert "future_roi_gain_depends_on_top_four_wins" in result["reasons"]
    assert not result["eligible_for_independent_release_review"]


def test_bad_provenance_wrong_cost_and_missing_rounds_block():
    sample=future()
    sample["paired_rounds"][5]["cost_yen_per_arm"]=1200
    result=evaluate_promotion(retro(robust=True),sample)
    assert "future_payouts_or_freezes_invalid" in result["reasons"]
    sample=future(25)
    result=evaluate_promotion(retro(robust=True),sample)
    assert "incomplete_candidate_specific_26_round_future_oos" in result["reasons"]
    sample=future()
    sample["paired_rounds"][1]["round"]=715
    result=evaluate_promotion(retro(robust=True),sample)
    assert "future_payouts_or_freezes_invalid" in result["reasons"]
    sample=future()
    sample["independent_snapshot_audit_passed"]=False
    assert not evaluate_promotion(retro(robust=True),sample)["candidate_specific_future_review_ready"]


def test_never_promote_from_missing_or_recycled_candidate_evidence():
    sample=future()
    sample["candidate_version"]="some-other-research"
    result=evaluate_promotion(retro(robust=True),sample)
    assert "no_matching_future_candidate_registration" in result["reasons"]
    assert result["auto_production_promotion"] is False
    sample=future()
    sample["paired_rounds"][0]["pre_draw_candidate_sha256"]="not-a-valid-digest"
    result=evaluate_promotion(retro(robust=True),sample)
    assert result["candidate_specific_future_review_ready"] is False
