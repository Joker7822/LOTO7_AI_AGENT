import csv
from pathlib import Path

import prediction_db_sync as dbs


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def test_yen_int_parses_signed_currency():
    assert dbs.yen_int("1,200円") == 1200
    assert dbs.yen_int("-300円") == -300
    assert dbs.yen_int("", 300) == 300


def test_signature_is_deterministic():
    body = b'{"a":1}'
    sig1 = dbs.signature("x" * 32, 123456, body)
    sig2 = dbs.signature("x" * 32, 123456, body)
    assert sig1 == sig2
    assert len(sig1) == 64


def test_build_payload_preserves_invalidation_and_filters_invalid_result(tmp_path):
    preds = tmp_path / "predictions.csv"
    corr = tmp_path / "prediction_corrections.csv"
    rec = tmp_path / "reconciliation.csv"

    write_csv(
        preds,
        [
            "prediction_id", "prediction_created_at_jst", "base_round", "base_draw_date",
            "target_round", "target_draw_date_estimate", "ticket", "predicted_numbers",
            "model_version", "git_sha", "data_sha256", "strategy_weights_json",
        ],
        [
            {
                "prediction_id": "active1", "prediction_created_at_jst": "2026-08-28T15:00:00+09:00",
                "base_round": "第692回", "base_draw_date": "2026-08-28", "target_round": "第693回",
                "target_draw_date_estimate": "2026-09-04", "ticket": "1", "predicted_numbers": "01 02 03 04 05 06 07",
                "model_version": "baseline", "git_sha": "abc", "data_sha256": "def", "strategy_weights_json": "{}",
            },
            {
                "prediction_id": "bad1", "prediction_created_at_jst": "2026-08-28T14:00:00+09:00",
                "base_round": "第692回", "base_draw_date": "2026-08-28", "target_round": "第693回",
                "target_draw_date_estimate": "2026-09-04", "ticket": "1", "predicted_numbers": "08 09 10 11 12 13 14",
                "model_version": "stale", "git_sha": "old", "data_sha256": "old", "strategy_weights_json": "{}",
            },
        ],
    )
    write_csv(
        corr,
        ["prediction_id", "corrected_at_jst", "action", "reason", "observed_data_sha256", "expected_data_sha256"],
        [{
            "prediction_id": "bad1", "corrected_at_jst": "2026-08-29T07:00:00+09:00", "action": "invalidate",
            "reason": "stale_sha", "observed_data_sha256": "old", "expected_data_sha256": "new",
        }],
    )
    write_csv(
        rec,
        [
            "target_round", "ticket", "predicted_numbers", "actual_draw_date", "actual_main_numbers",
            "actual_bonus_numbers", "main_hits", "bonus_hits", "grade", "prize_amount", "purchase_cost",
            "net_result", "model_version", "prediction_id", "result_id",
        ],
        [
            {
                "target_round": "第693回", "ticket": "1", "predicted_numbers": "01 02 03 04 05 06 07",
                "actual_draw_date": "2026-09-04", "actual_main_numbers": "01 10 11 12 13 14 15",
                "actual_bonus_numbers": "02 03", "main_hits": "1", "bonus_hits": "2", "grade": "はずれ",
                "prize_amount": "0円", "purchase_cost": "300円", "net_result": "-300円",
                "model_version": "baseline", "prediction_id": "active1", "result_id": "r1",
            },
            {
                "target_round": "第693回", "ticket": "1", "predicted_numbers": "08 09 10 11 12 13 14",
                "actual_draw_date": "2026-09-04", "actual_main_numbers": "01 10 11 12 13 14 15",
                "actual_bonus_numbers": "02 03", "main_hits": "5", "bonus_hits": "0", "grade": "x",
                "prize_amount": "1000円", "purchase_cost": "300円", "net_result": "700円",
                "model_version": "stale", "prediction_id": "bad1", "result_id": "r1",
            },
        ],
    )

    payload = dbs.build_payload(preds, corr, rec)
    by_id = {row["prediction_id"]: row for row in payload["predictions"]}
    assert by_id["active1"]["is_active"] is True
    assert by_id["bad1"]["is_active"] is False
    assert by_id["bad1"]["invalidation_reason"] == "stale_sha"
    assert [row["prediction_id"] for row in payload["results"]] == ["active1"]
    assert payload["results"][0]["net_result_yen"] == -300


def test_post_payload_requires_https():
    try:
        dbs.post_payload("http://example.invalid/api", "x" * 32, {"schema_version": dbs.SCHEMA_VERSION})
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP endpoint should have been rejected")
