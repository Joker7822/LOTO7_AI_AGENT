from historical_reconcile import build_reconciliation, parse_money_yen, summarize


def test_parse_money_yen():
    assert parse_money_yen("1,500円") == 1500
    assert parse_money_yen("6234800 円") == 6234800
    assert parse_money_yen("該当なし") is None


def test_reconcile_recalculates_against_loto_rows():
    preds = [{
        "round": "第101回",
        "training_rows": "100",
        "ticket": "1",
        "predicted_numbers": "01 02 03 04 05 06 07",
        "actual_main_numbers": "01 02 03 04 08 09 10",
        "actual_bonus_numbers": "05 11",
    }]
    loto = [
        {
            "回別": "第100回", "抽せん日": "2014-01-01",
            "本数字": "11 12 13 14 15 16 17", "ボーナス数字": "18 19",
        },
        {
            "回別": "第101回", "抽せん日": "2014-01-08",
            "本数字": "01 02 03 04 08 09 10", "ボーナス数字": "05 11",
            "5等当選金額": "1,500円",
        },
    ]
    rows = build_reconciliation(preds, loto)
    assert len(rows) == 1
    row = rows[0]
    assert row["base_round"] == 100
    assert row["target_round"] == 101
    assert row["main_hits"] == 4
    assert row["bonus_hits"] == 1
    assert row["grade"] == "5等"
    assert row["published_prize_yen"] == 1500
    assert row["reference_net_yen"] == 1200
    assert row["source_consistency"] == "verified_against_loto_csv"


def test_reconcile_fails_closed_on_embedded_result_mismatch():
    preds = [{
        "round": "101", "ticket": "1",
        "predicted_numbers": "01 02 03 04 05 06 07",
        "actual_main_numbers": "01 02 03 04 08 09 10",
        "actual_bonus_numbers": "05 11",
    }]
    loto = [{
        "回別": "第101回", "抽せん日": "2014-01-08",
        "本数字": "01 02 03 04 08 09 12", "ボーナス数字": "05 11",
    }]
    try:
        build_reconciliation(preds, loto)
    except RuntimeError as exc:
        assert "mismatch_actual_main" in str(exc)
    else:
        raise AssertionError("expected mismatch to fail closed")


def test_summary_reference_financials():
    rows = [
        {"target_round": 101, "grade": "はずれ", "published_prize_yen": 0},
        {"target_round": 101, "grade": "5等", "published_prize_yen": 1500},
    ]
    summary = summarize(rows, "p", "l")
    assert summary["evaluated_rounds"] == 1
    assert summary["evaluated_tickets"] == 2
    assert summary["winning_tickets"] == 1
    assert summary["purchase_cost_yen"] == 600
    assert summary["published_reference_payout_yen"] == 1500
    assert summary["published_reference_net_yen"] == 900
    assert summary["published_reference_roi"] == 2.5
