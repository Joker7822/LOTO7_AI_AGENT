import verify_sakura_rotation as verify


def test_rotation_verification_requires_post_incident_timestamps(monkeypatch):
    monkeypatch.setattr(
        verify.dbs,
        "post_payload",
        lambda *args, **kwargs: {
            "ok": True,
            "credential_generation": "gen-2",
            "predictions_upserted": 0,
            "results_upserted": 0,
        },
    )
    try:
        verify.verify_rotation(
            "https://example.invalid/api",
            "x" * 32,
            "gen-2",
            "2026-09-01T00:00:00Z",
            "2026-09-07T00:00:00Z",
        )
    except ValueError as exc:
        assert "after the 2026-09-06" in str(exc)
    else:
        raise AssertionError("pre-incident DB rotation timestamp must be rejected")


def test_rotation_verification_records_no_secret_values(monkeypatch):
    def fake_post(endpoint, secret, payload, credential_generation=""):
        assert secret == "x" * 32
        assert credential_generation == "gen-2"
        assert payload["predictions"] == []
        assert payload["results"] == []
        return {
            "ok": True,
            "credential_generation": "gen-2",
            "predictions_upserted": 0,
            "results_upserted": 0,
        }

    monkeypatch.setattr(verify.dbs, "post_payload", fake_post)
    status = verify.verify_rotation(
        "https://example.invalid/api",
        "x" * 32,
        "gen-2",
        "2026-09-07T01:00:00Z",
        "2026-09-07T01:05:00Z",
    )
    assert status["status"] == "rotation_attested_and_live_verified"
    assert status["credential_generation"] == "gen-2"
    assert status["live_verification"]["hmac_authentication"] == "verified"
    assert status["live_verification"]["database_connection_and_transaction"] == "verified"
    assert status["limitations"]["secret_values_recorded"] is False
    assert "x" * 32 not in str(status)
