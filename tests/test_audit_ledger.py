from audit_ledger import grade_ticket


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
    from audit_ledger import migrate_legacy, read_csv
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
