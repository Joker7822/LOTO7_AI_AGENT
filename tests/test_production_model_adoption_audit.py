"""Keep historical AI research from silently becoming Production lottery tickets."""
import json
import subprocess
import sys

import production_model_adoption_audit as audit


def complete_report(candidate=audit.PROPOSAL):
    good = {
        "trusted_draws": 26,
        "mean_score_delta": 0.10,
        "win_rate": 0.60,
        "e_value": 25.0,
        "passes_all": True,
    }
    return {
        "locked_candidate_version": candidate,
        "confirmed": True,
        "claim_status": "confirmed_operational_future_oos_edge",
        "confirmation_policy_registered_at_trusted_draws": 0,
        "protocol_lock": {
            "verified": True,
            "stored_sha256": "lock123",
            "observed_sha256": "lock123",
        },
        "confirmation_policy": {
            "claim_requires_full_horizon": True,
            "horizon_trusted_draws": 26,
        },
        "progress": {
            "horizon_trusted_draws": 26,
            "trusted_draws": 26,
            "matched_ensemble_trusted_draws": 26,
            "full_horizon_complete": True,
        },
        "comparators": {
            "uniform_random": dict(good),
            "matched_ensemble32": dict(good),
        },
    }


def assess(holdout):
    return audit.audit(
        champion={"model_version": "baseline-5fdb8dc2ad"},
        holdout=holdout,
        issued={
            "target_round": "第701回",
            "model_version": "baseline-5fdb8dc2ad",
            "ticket_policy": "champion_original",
        },
    )


def test_real_repository_report_never_borrows_other_candidate_evidence():
    from pathlib import Path
    report = json.loads(Path("loto7_agent_output/future_holdout_evidence.json").read_text())
    result = assess(report)
    assert result["status"] == "blocked_no_independent_evidence"
    assert "missing_candidate_specific_future_evidence" in result["reasons"]
    assert result["candidate_automatically_adopted"] is False
    assert result["production_changed"] is False


def test_missing_evidence_fails_closed():
    result = assess({})
    assert "missing_candidate_specific_future_evidence" in result["reasons"]
    assert "incomplete_26_draw_future_holdout" in result["reasons"]
    assert result["candidate_review_ready"] is False


def test_previous_candidate_evidence_must_not_transfer():
    result = assess(complete_report("global-previous-candidate"))
    assert "missing_candidate_specific_future_evidence" in result["reasons"]
    assert not result["candidate_review_ready"]


def test_post_outcome_registration_fails_closed():
    report = complete_report()
    report["confirmation_policy_registered_at_trusted_draws"] = 4
    result = assess(report)
    assert "confirmation_rule_not_prefrozen_before_first_outcome" in result["reasons"]


def test_interim_results_or_false_flags_cannot_authorize():
    report = complete_report()
    report["progress"]["trusted_draws"] = 8
    report["comparators"]["uniform_random"]["mean_score_delta"] = -0.3
    report["comparators"]["uniform_random"]["passes_all"] = True
    result = assess(report)
    assert "incomplete_26_draw_future_holdout" in result["reasons"]
    assert "random_baseline_promotion_gate_not_met" in result["reasons"]


def test_nonfinite_and_wrong_types_do_not_pass_comparators():
    report = complete_report()
    report["comparators"]["matched_ensemble32"]["e_value"] = "NaN"
    assert "matched_ensemble_promotion_gate_not_met" in assess(report)["reasons"]
    report = complete_report()
    report["comparators"]["uniform_random"]["trusted_draws"] = True
    assert "random_baseline_promotion_gate_not_met" in assess(report)["reasons"]


def test_perfect_synthetic_report_only_reaches_review_not_adoption():
    result = assess(complete_report())
    assert result["status"] == "human_release_review_required"
    assert result["candidate_review_ready"] is True
    assert result["candidate_automatically_adopted"] is False
    assert result["proposal_is_implemented_model"] is False


def test_cli_is_read_only_and_only_writes_named_temporary_report(tmp_path):
    champion = tmp_path / "champion.json"
    holdout = tmp_path / "holdout.json"
    issued = tmp_path / "issued.json"
    output = tmp_path / "audit.json"
    champion.write_text('{"model_version": "baseline"}', encoding="utf-8")
    holdout.write_text("{}", encoding="utf-8")
    issued.write_text('{"target_round": "第701回"}', encoding="utf-8")
    before = tuple(f.read_bytes() for f in (champion, holdout, issued))
    r = subprocess.run(
        [sys.executable, "production_model_adoption_audit.py",
         "--champion", str(champion), "--holdout", str(holdout),
         "--issued", str(issued), "--output", str(output)],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(r.stdout)["status"] == "blocked_no_independent_evidence"
    assert json.loads(output.read_text())["production_changed"] is False
    assert before == tuple(f.read_bytes() for f in (champion, holdout, issued))


def test_production_publisher_includes_audit_before_freeze():
    from pathlib import Path
    yml = Path(".github/workflows/weekly_production_publisher.yml").read_text(encoding="utf-8")
    assert "production_model_adoption_audit.py" in yml
    assert yml.index("production_model_adoption_audit.py") < yml.index("Freeze or safely republish canonical Production")
