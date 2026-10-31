import csv
import json
from pathlib import Path

import pytest

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


def test_post_payload_checks_credential_generation(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok":true,"credential_generation":"gen-2"}'

    captured = {}

    def fake_urlopen(request, timeout=30):
        captured["generation"] = request.headers.get("X-loto7-credential-generation")
        return FakeResponse()

    monkeypatch.setattr(dbs.urllib.request, "urlopen", fake_urlopen)
    payload = {"schema_version": dbs.SCHEMA_VERSION, "predictions": [], "results": []}
    got = dbs.post_payload(
        "https://example.invalid/api",
        "x" * 32,
        payload,
        credential_generation="gen-2",
    )
    assert got["credential_generation"] == "gen-2"
    assert captured["generation"] == "gen-2"


def test_post_payload_rejects_credential_generation_mismatch(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok":true,"credential_generation":"old-gen"}'

    monkeypatch.setattr(dbs.urllib.request, "urlopen", lambda request, timeout=30: FakeResponse())
    payload = {"schema_version": dbs.SCHEMA_VERSION, "predictions": [], "results": []}
    try:
        dbs.post_payload(
            "https://example.invalid/api",
            "x" * 32,
            payload,
            credential_generation="new-gen",
        )
    except RuntimeError as exc:
        assert "generation mismatch" in str(exc)
    else:
        raise AssertionError("credential generation mismatch must fail closed")


def test_configured_credential_generation_uses_public_pin(monkeypatch, tmp_path):
    pin = tmp_path / "credential_generation.txt"
    pin.write_text("gen-verified\n", encoding="utf-8")
    monkeypatch.delenv("SAKURA_CREDENTIAL_GENERATION", raising=False)
    monkeypatch.setattr(dbs, "DEFAULT_CREDENTIAL_GENERATION_FILE", pin)
    assert dbs.configured_credential_generation() == "gen-verified"


def test_configured_credential_generation_env_overrides_pin(monkeypatch, tmp_path):
    pin = tmp_path / "credential_generation.txt"
    pin.write_text("gen-file\n", encoding="utf-8")
    monkeypatch.setattr(dbs, "DEFAULT_CREDENTIAL_GENERATION_FILE", pin)
    monkeypatch.setenv("SAKURA_CREDENTIAL_GENERATION", "gen-env")
    assert dbs.configured_credential_generation() == "gen-env"


def test_sakura_sync_rejects_all_incomplete_or_overlapping_702_portfolios(tmp_path):
    import production_ticket_geometry35 as geometry
    fields = [
        "prediction_id", "prediction_created_at_jst", "base_round", "base_draw_date",
        "target_round", "target_draw_date_estimate", "ticket", "predicted_numbers",
        "model_version", "git_sha", "data_sha256", "strategy_weights_json",
    ]
    rows = [
        {"prediction_id": f"702-{i}", "prediction_created_at_jst": "2026-11-06T15:00:00+09:00",
         "base_round": "第701回", "base_draw_date": "2026-10-30",
         "target_round": "第702回", "target_draw_date_estimate": "2026-11-06",
         "ticket": str(i), "predicted_numbers": " ".join(f"{n:02d}" for n in ticket),
         "model_version": "baseline-test+" + geometry.VERSION,
         "git_sha": "sha", "data_sha256": "sha", "strategy_weights_json": "{}"}
        for i, ticket in enumerate(geometry.portfolio_for_target(702), 1)
    ]
    preds = tmp_path / "predictions.csv"
    corrections = tmp_path / "corrections.csv"
    results = tmp_path / "results.csv"
    write_csv(preds, fields, rows)
    valid = dbs.build_payload(preds, corrections, results)
    assert len(valid["predictions"]) == 5

    bad = [dict(r) for r in rows]
    bad[1]["predicted_numbers"] = bad[0]["predicted_numbers"]
    write_csv(preds, fields, bad)
    with pytest.raises(ValueError, match="overlap"):
        dbs.build_payload(preds, corrections, results)

    write_csv(preds, fields, rows[:4])
    with pytest.raises(ValueError, match="five"):
        dbs.build_payload(preds, corrections, results)

    bad = [dict(r) for r in rows]
    bad[0]["model_version"] = "baseline-test"
    write_csv(preds, fields, bad)
    with pytest.raises(ValueError, match="policy"):
        dbs.build_payload(preds, corrections, results)


def rotation_proof(generation="gen-rotated"):
    return {
        "version": "sakura-credential-rotation-verification-v1",
        "status": "rotation_attested_and_live_verified",
        "credential_generation": generation,
        "live_verification": {
            "hmac_authentication": "verified",
            "credential_generation_match": True,
            "database_connection_and_transaction": "verified",
        },
    }


def test_network_sync_requires_verified_rotation(tmp_path):
    status = tmp_path / "rotation.json"
    pin = tmp_path / "credential_generation.txt"
    pin.write_text("gen-rotated\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="rotation status"):
        dbs.require_verified_rotation("gen-rotated", status_path=status, generation_path=pin)

    record = rotation_proof()
    record["status"] = "pending_external_rotation_verification"
    status.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RuntimeError, match="verified credential rotation"):
        dbs.require_verified_rotation("gen-rotated", status_path=status, generation_path=pin)


def test_network_sync_accepts_only_matching_verified_generation(tmp_path):
    status = tmp_path / "rotation.json"
    pin = tmp_path / "credential_generation.txt"
    status.write_text(json.dumps(rotation_proof()), encoding="utf-8")
    pin.write_text("gen-rotated\n", encoding="utf-8")
    dbs.require_verified_rotation("gen-rotated", status_path=status, generation_path=pin)

    with pytest.raises(RuntimeError, match="matching"):
        dbs.require_verified_rotation("wrong-generation", status_path=status, generation_path=pin)
    pin.write_text("wrong-generation\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="matching"):
        dbs.require_verified_rotation("wrong-generation", status_path=status, generation_path=pin)

    pin.write_text("gen-rotated\n", encoding="utf-8")
    proof = rotation_proof()
    proof["live_verification"]["database_connection_and_transaction"] = "pending"
    status.write_text(json.dumps(proof), encoding="utf-8")
    with pytest.raises(RuntimeError, match="verified credential rotation"):
        dbs.require_verified_rotation("gen-rotated", status_path=status, generation_path=pin)
