"""Cross-layer ROI-first: strict prefix, replay risk, issued-vs-research separation."""
from __future__ import annotations

from datetime import date,timedelta
from pathlib import Path

import pytest

import audit_ledger as ledger
from roi_first_governance import evaluate_roi_first
from roi_online_selector import SelectionConfig, backtest_shadow, choose_from_prefix
from roi_operational_risk import BudgetLimits, evaluate_budget_risk
from research.roi_issued_financial_audit import audit_issued


def rounds(n=170):
    rows=[]
    for t in range(2,n+2):
        rows.append({
            "round":t,
            "draw_date":(date(2013,4,12)+timedelta(days=7*(t-2))).isoformat(),
            "public_payout_complete":"True",
            "baseline_payout_complete":"True",
            "public_payout_yen":1200 if t%2 else 1800,
            "baseline_payout_yen":900,
            "portfolio_score":2.8,"baseline_score":3.0,
        })
    return rows


def test_rolling_cashflow_decision_is_available_only_after_52_past_settled_draws():
    data=rounds(180)
    result=backtest_shadow(data)
    choices=result["policy_decisions"]
    assert choices[0]["choice"]=="incumbent"
    assert all(row["choice"]=="incumbent" for row in choices if row["round"] <= 152)
    assert choices[151]["round"]==153
    assert choices[151]["choice"]=="combination"
    assert choices[151]["prefix_trained_rounds"]==52
    assert result["combination_chosen_draws"]>0
    assert result["cost_yen_per_arm"]==180*1500
    assert result["selected_roi"]==pytest.approx(
        result["selected_payout_yen"]/(180*1500))
    assert result["production_tickets_modified"] is False
    assert result["buying_authorized"] is False


def test_counterfactual_outcome_mutation_never_changes_same_round_choice():
    data=rounds(180)
    original=backtest_shadow(data)
    mutated=[dict(r) for r in data]
    mutated[-1]["public_payout_yen"]=99999999
    mutated[-1]["baseline_payout_yen"]=0
    result=backtest_shadow(mutated)
    assert result["policy_decisions"][:-1]==original["policy_decisions"][:-1]
    assert result["policy_decisions"][-1]["choice"]==original["policy_decisions"][-1]["choice"]
    assert result["policy_decisions"][-1]["prefix_cashflow_delta_yen"]==original["policy_decisions"][-1]["prefix_cashflow_delta_yen"]


def test_no_selection_on_unsettled_or_one_big_payout():
    data=rounds(104)
    for row in data:
        row["public_payout_yen"]=row["baseline_payout_yen"]
    data[102]["public_payout_yen"]=100000
    decision=choose_from_prefix(data,SelectionConfig())
    assert decision["choice"]=="incumbent"
    assert decision["reason"]=="past_cashflow_robustness_fail"
    data[-1]["public_payout_complete"]="False"
    decision=choose_from_prefix(data)
    assert decision["choice"]=="incumbent"
    assert decision["reason"]=="incomplete_prior_payout"
    with pytest.raises(ValueError,match="unknown payout"):
        backtest_shadow(data)


def test_budget_risk_reconciles_cashflows_and_never_executes_purchase():
    data=rounds(170)
    roi=evaluate_roi_first(data)
    shadow=backtest_shadow(data)
    risk=evaluate_budget_risk(data,roi,shadow)
    assert risk["current_ticket_cost_yen"]==1500
    assert risk["historical_combination_total_spend_yen"]==170*1500
    assert risk["historical_combination_total_payout_yen"]==roi["periods"]["all_2_plus"]["combo_payout_yen"]
    assert risk["historical_combination_net_yen"]==roi["periods"]["all_2_plus"]["combo_profit_yen"]
    assert risk["hypothetical_four_draw_spend_yen"]==6000
    assert risk["hypothetical_thirteen_draw_spend_yen"]==19500
    assert risk["automated_purchase_enabled"] is False
    assert risk["purchase_recommended"] is False
    assert risk["expected_future_roi"]=="not_verified"
    assert risk["production_tickets_modified"] is False
    with pytest.raises(ValueError,match="mismatched cashflow"):
        evaluate_budget_risk(data[:-1],roi,shadow)
    with pytest.raises(ValueError,match="invalid risk budget"):
        evaluate_budget_risk(data,roi,shadow,BudgetLimits(max_tickets_per_draw=7))


def issued_fixtures(root:Path):
    preds=root/"predictions.csv"
    correct=root/"prediction_corrections.csv"
    actual=root/"actual_results.csv"
    tickets=[
        {
            "prediction_id":f"id-{i}","target_round":"第702回",
            "ticket":str(i),
            "model_version":"baseline+production-disjoint35-layout-v1",
            "prediction_created_at_jst":"2026-11-01T13:00:00+09:00",
            "predicted_numbers":" ".join(f"{n:02d}" for n in range(7*(i-1)+1,7*i+1)),
        } for i in range(1,6)
    ]
    ledger.write_csv(preds,tickets,ledger.PRED_FIELDS)
    outcome=[
        {
            "result_id":"a","round":"第702回","draw_date":"2026-11-06",
            "main_numbers":"01 02 03 08 09 10 11",
            "bonus_numbers":"04 12",
            "5等当選金額":"1900円","6等当選金額":"1000円",
        }
    ]
    ledger.write_csv(actual,outcome,ledger.ACTUAL_FIELDS)
    return preds,correct,actual


def test_issued_cash_audit_is_distinct_from_research_and_never_claims_real_purchase(tmp_path):
    p,c,a=issued_fixtures(tmp_path)
    report=audit_issued(p,c,a)
    assert report["status"]=="settled_issued_replay_only"
    assert report["settled_rounds"]==1
    assert report["reference_cost_yen"]==1500
    assert report["reference_payout_yen"]==2900
    assert report["reference_roi"]==pytest.approx(2900/1500)
    assert report["strictly_prospective_rounds"]==[702]
    assert report["actual_purchase_receipts_verified"] is False
    assert report["realized_personal_cash_return"] is None
    assert report["production_ledger_modified"] is False
    assert report["scope"]=="frozen_issued_predictions_only_not_research_replay"


def test_issued_audit_excludes_unsettled_and_blocks_unknown_realized_prizes(tmp_path):
    p,c,a=issued_fixtures(tmp_path)
    outcome=ledger.read_csv(a)
    outcome[0]["5等当選金額"]=""
    ledger.write_csv(a,outcome,ledger.ACTUAL_FIELDS)
    rep=audit_issued(p,c,a)
    assert rep["status"]=="incomplete_published_payouts"
    assert rep["reference_payout_yen"] is None
    assert rep["reference_roi"] is None
    a.unlink()
    rep=audit_issued(p,c,a)
    assert rep["status"]=="no_settled_issued_tickets"
    assert rep["unsettled_round_numbers"]==[702]
    assert rep["reference_roi"] is None


def test_roi_production_guards_appear_on_new_candidate_state():
    import inspect
    import production_ticket_geometry35 as prod
    import audit_ledger as audit
    s=inspect.getsource(prod.prepare_new_production_outputs)
    assert '"production_purchase_automation": False' in s
    assert '"production_expected_future_roi": None' in s
    assert '"production_roi_primary_kpi"' in s
    guard=inspect.getsource(audit.append_current_predictions)
    assert 'refusing combination Production without ROI financial governance' in guard
