import json
from dashboard_prize_totals import history, summary, money, live

def test_grade_count_and_reference_roi(tmp_path):
    raw={"grade_counts":{"6等":1,"はずれ":4},"evaluated_rounds":1}
    (tmp_path/"historical_reconciliation_summary.json").write_text(json.dumps(raw))
    p={"status":"historical_hypothetical_only","tickets":5,"winning_tickets":1,
       "reference_cost_yen":1500,"reference_payout_yen":1100}
    got=history(tmp_path,{"reference_payout":p})
    assert got["grade_counts"]["1等"]==0 and got["grade_counts"]["6等"]==1
    assert got["reference_roi"]==1100/1500
    p["winning_tickets"]=2
    assert history(tmp_path,{"reference_payout":p})["status"]=="unavailable"

def test_unknown_payout_never_becomes_zero():
    x=summary("issued_production",{"6等":1,"はずれ":4},1,None)
    assert x["status"]=="payout_incomplete" and x["reference_roi"] is None
    assert money("1,100円")==1100
    assert money("該当なし") is None

def test_live_missing_ledger_not_zero(tmp_path):
    assert live(tmp_path,{"latest":{"round":704}},{"published":True,"target_round":"第704回"})["status"]=="unavailable"
