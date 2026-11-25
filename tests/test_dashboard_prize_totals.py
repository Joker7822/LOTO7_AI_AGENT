import json
from dashboard_prize_totals import history, summary, money, live

def test_v2_grade_count_and_reference_roi(tmp_path):
    got=history(tmp_path,{})
    assert got["model"]=="production-ai-ranked35-roi-cash-v2"
    assert got["rounds"]==703 and got["tickets"]==3515
    assert got["grade_counts"]=={"1等":0,"2等":0,"3等":1,"4等":4,"5等":52,"6等":90,"はずれ":3368}
    assert got["winning_tickets"]==147
    assert got["reference_payout_yen"]==922400
    assert got["reference_roi"]==922400/1054500

def test_unknown_payout_never_becomes_zero():
    x=summary("issued_production",{"6等":1,"はずれ":4},1,None)
    assert x["status"]=="payout_incomplete" and x["reference_roi"] is None
    assert money("1,100円")==1100
    assert money("該当なし") is None

def test_live_missing_ledger_not_zero(tmp_path):
    assert live(tmp_path,{"latest":{"round":704}},{"published":True,"target_round":"第704回"})["status"]=="unavailable"
