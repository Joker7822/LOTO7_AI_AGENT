"""Cash ROI is first; fail closed on missing payouts, short-run noise and tail risk."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, timedelta

import pytest

import loto7_v2_runner as v2
from roi_first_governance import evaluate_roi_first, roi_markdown
from research import production_combination_round2_replay as replay


def rows(count: int = 130) -> list[dict]:
    data=[]
    for t in range(2, count+2):
        data.append({
            "round": t,
            "draw_date": (date(2013,4,12)+timedelta(days=7*(t-2))).isoformat(),
            "public_payout_complete": "True",
            "baseline_payout_complete": "True",
            "public_payout_yen": 900 if t%2 == 0 else 1200,
            "baseline_payout_yen": 600,
            "portfolio_score": "2.50",
            "baseline_score": "2.60",
        })
    return data


def test_roi_is_payout_divided_by_exact_purchase_spend():
    inp=rows(130)
    report=evaluate_roi_first(inp)
    p=report["periods"]["all_2_plus"]
    assert p["draws"]==130
    assert p["ticket_count_per_arm"]==650
    assert p["purchase_cost_yen_per_arm"]==195000
    assert p["combo_payout_yen"]==65*900+65*1200
    assert p["baseline_payout_yen"]==130*600
    assert p["combo_roi"]==pytest.approx((65*900+65*1200)/195000)
    assert p["baseline_roi"]==pytest.approx(78000/195000)
    assert p["roi_delta_percentage_points"]==pytest.approx(
        100*(p["combo_payout_yen"]-78000)/195000)
    assert len(report["annual"])>=2
    assert "第101回" in roi_markdown(report)
    assert report["authorizes_model_promotion"] is False
    assert report["requires_new_frozen_prospective_oos"] is True


def test_high_total_roi_alone_fails_gate_if_short_term_declines():
    inp=rows(190)
    for r in inp[-60:]:
        r["public_payout_yen"]=0
    out=evaluate_roi_first(inp)
    assert not out["cashflow_checks_all_pass"]
    assert not out["cashflow_adoption_checks"]["positive_recent_60_cashflow"]
    assert out["periods"]["recent_60"]["combo_roi"]==0


def test_large_rare_win_does_not_fake_robust_payout_advantage():
    inp=rows(180)
    for r in inp:
        r["public_payout_yen"]=r["baseline_payout_yen"]
    inp[-1]["public_payout_yen"]=20000
    result=evaluate_roi_first(inp)
    p=result["periods"]["trained_101_plus"]
    assert p["payout_delta_yen"]>0
    assert p["largest_four_positive_gain_rounds_yen"]>p["payout_delta_yen"]-1
    assert p["delta_excluding_four_largest_positive_gain_rounds_yen"]==0
    assert result["cashflow_adoption_checks"]["not_driven_by_four_best_positive_rounds"] is False


def test_missing_prize_amounts_cannot_be_silently_valued_at_zero():
    inp=rows(110)
    inp[-2]["public_payout_complete"]="False"
    result=evaluate_roi_first(inp)
    assert result["periods"]["all_2_plus"]["valid"] is False
    assert result["periods"]["all_2_plus"]["adoption_eligible"] is False
    assert result["cashflow_adoption_checks"]["all_payout_data_complete"] is False


@pytest.mark.parametrize("bad", [
    {"round": 900},
    {"public_payout_yen": -100},
    {"public_payout_yen": "NaN"},
    {"public_payout_yen": "unknown"},
    {"baseline_payout_complete": "unknown"},
    {"draw_date": "2027-99-99"},
])
def test_invalid_cashflows_fail_closed(bad):
    inp=rows(104)
    inp[1].update(bad)
    with pytest.raises(ValueError):
        evaluate_roi_first(inp)


def test_roi_reporting_is_deterministic_and_keeps_scores_secondary():
    inp=rows(132)
    a=evaluate_roi_first(inp)
    b=evaluate_roi_first(inp)
    assert a==b
    assert a["primary_kpi"]=="public_historical_payout_yen_divided_by_1500_yen_per_round"
    assert a["periods"]["all_2_plus"]["combo_mean_diagnostic_score"]==pytest.approx(2.5)
    assert a["exact_null"]["fair_draw_unchanged_by_repartition"] is True


def test_replay_explicitly_uses_roi_first_governance():
    source=__import__("inspect").getsource(replay.run)
    assert "roi_report = evaluate_roi_first(round_rows)" in source
    assert '"roi_priority": roi_report' in source
