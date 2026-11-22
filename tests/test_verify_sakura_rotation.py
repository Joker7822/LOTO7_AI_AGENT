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


def test_verification_workflow_never_auto_closes_credential_incident():
    from pathlib import Path

    workflow = Path(".github/workflows/verify_sakura_credential_rotation.yml").read_text(
        encoding="utf-8"
    )
    # Live verification proves only that NEW credentials work. It cannot
    # independently prove revoked old credentials or real Prediction sync.
    assert "gh issue close" not in workflow
    assert "Close credential exposure follow-up" not in workflow
    assert "issues: write" not in workflow
    assert "contents: write" in workflow
    assert "Report successful verifier scope and remaining incident work" in workflow
    assert "not proof of old-credential revocation" in workflow
    assert "normal Production sync succeeded" in workflow


def test_sakura_rotation_verifier_is_main_only_before_any_network_or_git_write():
    from pathlib import Path

    workflow = Path(".github/workflows/verify_sakura_credential_rotation.yml").read_text(
        encoding="utf-8"
    )
    first = workflow.index("      - name: Require main ref for credential rotation verification")
    checkout = workflow.index("      - name: Checkout")
    post = workflow.index("      - name: Perform live signed rotation verification")
    commit = workflow.index("      - name: Commit public non-secret verification status")
    assert first < checkout < post < commit
    gate = workflow[first:checkout]
    assert 'if [ "${GITHUB_REF}" != "refs/heads/main" ]; then' in gate
    assert 'exit 1' in gate
    assert "workflow_dispatch:" in workflow
    assert 'SAKURA_PREDICTION_API_URL: ${{ secrets.SAKURA_PREDICTION_API_URL }}' in workflow
    assert 'SAKURA_PREDICTION_HMAC_SECRET: ${{ secrets.SAKURA_PREDICTION_HMAC_SECRET }}' in workflow
