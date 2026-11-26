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


def test_v2_live_cohort_separates_legacy_pending_and_settled(tmp_path):
    import csv
    from dashboard_prize_totals import ROI_CASH_VERSION
    old = "baseline-5fdb8dc2ad+production-disjoint35-layout-v1"
    new = "baseline-5fdb8dc2ad+" + ROI_CASH_VERSION
    def write(name, rows, fields=None):
        with (tmp_path / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    predictions = []
    for rnd, day, model in [(704,"2026-11-20",old),(705,"2026-11-27",new)]:
        for i in range(5):
            predictions.append(dict(prediction_id=f"{rnd}-{i}",ticket=i+1,
                target_round=f"第{rnd}回",base_round=f"第{rnd-1}回",
                prediction_created_at_jst=day+"T13:00:00+09:00",
                target_draw_date_estimate=day,model_version=model,
                predicted_numbers=" ".join(str(n) for n in range(i*7+1,i*7+8))))
    def actual(rnd, day):
        return {"round":f"第{rnd}回","draw_date":day,"source_status":"ok",
                "source_verification":"verified_two_result_sources",
                "main_numbers":"1 2 3 4 5 6 7","bonus_numbers":"36 37","1等当選金額":"100円"}
    def source(rnd):
        return {"latest":{"round":rnd,"main":[1,2,3,4,5,6,7],"bonus":[36,37]},
                "status":"ok","verification":"verified_two_result_sources"}
    write("predictions.csv",predictions)
    write("prediction_corrections.csv",[],["prediction_id","action"])
    write("actual_results.csv",[actual(704,"2026-11-20")])
    pub={"published":True,"target_round":"第705回","model_version":new}
    pending=live(tmp_path,source(704),pub,v2_only=True)
    assert pending["status"]=="awaiting_first_settlement"
    assert pending["rounds"]==0 and pending["pending_rounds"]==1
    assert pending["reference_roi"] is None
    write("actual_results.csv",[actual(704,"2026-11-20"),actual(705,"2026-11-27")])
    settled=live(tmp_path,source(705),pub,v2_only=True)
    assert settled["rounds"]==1 and settled["tickets"]==5
    assert settled["grade_counts"]["1等"]==1 and settled["reference_payout_yen"]==100
    assert settled["first_settled"]["round"]==705
    assert live(tmp_path,source(705),pub)["rounds"]==2
    predictions[-1]["model_version"]=old
    write("predictions.csv",predictions)
    assert live(tmp_path,source(705),pub,v2_only=True)["status"]=="unavailable"
