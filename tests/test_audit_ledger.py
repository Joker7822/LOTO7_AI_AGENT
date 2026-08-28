from pathlib import Path

from audit_ledger import (
    active_prediction_rows,
    append_current_predictions,
    append_prediction_invalidations,
    grade_ticket,
    migrate_legacy,
    read_csv,
    write_csv,
    write_prediction_history_view,
    PRED_FIELDS,
)


def test_loto7_grades():
    main=(1,2,3,4,5,6,7); bonus=(8,9)
    assert grade_ticket((1,2,3,4,5,6,7),main,bonus)[2]=="1等"
    assert grade_ticket((1,2,3,4,5,6,8),main,bonus)[2]=="2等"
    assert grade_ticket((1,2,3,4,5,6,10),main,bonus)[2]=="3等"
    assert grade_ticket((1,2,3,4,5,10,11),main,bonus)[2]=="4等"
    assert grade_ticket((1,2,3,4,10,11,12),main,bonus)[2]=="5等"
    assert grade_ticket((1,2,3,8,10,11,12),main,bonus)[2]=="6等"
    assert grade_ticket((1,2,3,10,11,12,13),main,bonus)[2]=="はずれ"


def test_legacy_migration_does_not_claim_current_model(tmp_path):
    import csv
    legacy=tmp_path/"prediction_history.csv"
    with legacy.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["prediction_created_at_jst","base_round","base_draw_date","target_round","target_draw_date_estimate","ticket","predicted_numbers"])
        w.writeheader(); w.writerow({"prediction_created_at_jst":"2026-08-21T08:00:00+09:00","base_round":"第690回","base_draw_date":"2026-08-14","target_round":"第691回","target_draw_date_estimate":"2026-08-21","ticket":"1","predicted_numbers":"01 02 03 04 05 06 07"})
    dest=tmp_path/"predictions.csv"
    migrate_legacy(legacy,dest,{"model_version":"new-model","git_sha":"newsha","data_sha256":"newdata"})
    row=read_csv(dest)[0]
    assert row["model_version"]=="legacy-unknown"
    assert row["git_sha"]==""
    assert row["data_sha256"]==""


def _loto_rows():
    return [{"回別":"第692回","抽せん日":"2026-08-28","本数字":"07 09 15 18 20 28 31","ボーナス数字":"21 34"}]


def _ticket_rows():
    return [
        {"ticket":"1","numbers":"01 02 03 04 05 06 07"},
        {"ticket":"2","numbers":"08 09 10 11 12 13 14"},
        {"ticket":"3","numbers":"15 16 17 18 19 20 21"},
        {"ticket":"4","numbers":"22 23 24 25 26 27 28"},
        {"ticket":"5","numbers":"29 30 31 32 33 34 35"},
    ]


def test_freeze_requires_current_data_provenance(tmp_path):
    preds=tmp_path/"predictions.csv"
    state={
        "latest_round":"第692回",
        "target_round":"第693回",
        "data_sha256":"sha-old",
        "model_version":"baseline-test",
        "git_sha":"abc",
        "expert_weights":{},
    }
    try:
        append_current_predictions(
            _loto_rows(),_ticket_rows(),preds,state,current_data_sha="sha-current"
        )
    except RuntimeError as e:
        assert "data SHA" in str(e)
    else:
        raise AssertionError("stale state must not be frozen")


def test_mismatched_current_prediction_is_invalidated_not_deleted(tmp_path):
    preds=tmp_path/"predictions.csv"
    corrections=tmp_path/"prediction_corrections.csv"
    rows=[]
    for i,tr in enumerate(_ticket_rows(),1):
        rows.append({
            "prediction_id":f"p{i}",
            "prediction_created_at_jst":"2026-08-28T23:30:03+09:00",
            "base_round":"第692回","base_draw_date":"2026-08-28",
            "target_round":"第693回","target_draw_date_estimate":"2026-09-04",
            "ticket":str(i),"predicted_numbers":tr["numbers"],
            "model_version":"baseline-test","git_sha":"abc",
            "data_sha256":"sha-old","strategy_weights_json":"{}",
        })
    write_csv(preds,rows,PRED_FIELDS)
    assert append_prediction_invalidations(_loto_rows(),preds,corrections,"sha-current")==5
    assert len(read_csv(preds))==5
    assert active_prediction_rows(preds,corrections)==[]


def test_prediction_history_view_marks_reconciled_rows_checked(tmp_path):
    preds=tmp_path/"predictions.csv"
    history=tmp_path/"prediction_history.csv"
    row={
        "prediction_id":"p1","prediction_created_at_jst":"2026-08-21T20:19:21+09:00",
        "base_round":"第691回","base_draw_date":"2026-08-21",
        "target_round":"第692回","target_draw_date_estimate":"2026-08-28",
        "ticket":"1","predicted_numbers":"10 18 20 22 24 25 35",
        "model_version":"legacy-unknown","git_sha":"","data_sha256":"","strategy_weights_json":"{}",
    }
    write_csv(preds,[row],PRED_FIELDS)
    rec=[{
        "target_round":"第692回","ticket":"1","predicted_numbers":row["predicted_numbers"],
        "actual_draw_date":"2026-08-28","actual_main_numbers":"07 09 15 18 20 28 31",
        "actual_bonus_numbers":"21 34","main_hits":"2","bonus_hits":"0","grade":"はずれ",
        "prize_amount":"0円","purchase_cost":"300円","net_result":"-300円",
        "model_version":"legacy-unknown","prediction_id":"p1","result_id":"r692",
    }]
    write_prediction_history_view(history,preds,rec)
    out=read_csv(history)[0]
    assert out["status"]=="checked"
    assert out["actual_draw_date"]=="2026-08-28"
    assert out["main_hits"]=="2"


def test_audit_checkpoint_source_does_not_auto_freeze_candidate_tickets():
    text=Path("audit_ledger.py").read_text(encoding="utf-8")
    main_body=text.split("def main()->int:",1)[1]
    assert "append_current_predictions(" not in main_body
