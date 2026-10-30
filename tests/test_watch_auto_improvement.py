"""Automated remediation of current WATCH alerts must never touch Production."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

import agent_role_council as council
import watch_auto_improvement as auto
from loto7_evolving_agent import expert_probabilities, make_history, read_csv_flexible

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 29, 10, tzinfo=timezone.utc)


@pytest.fixture
def project(tmp_path, monkeypatch):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    for p in ["loto7.csv", "loto7_evolving_agent.py",
              "agent_role_council.py", "watch_auto_improvement.py"]:
        shutil.copyfile(ROOT / p, tmp_path / p)
    for p in ["agent_role_council_summary.json", "research_cycle_guard.json",
              "source_validation.json", "model_champion.json"]:
        shutil.copyfile(ROOT / "loto7_agent_output" / p, out / p)
    csv = tmp_path / "loto7.csv"
    x, clean = make_history(read_csv_flexible(csv))
    current = council.round_id(clean["回別"].iloc[-1])
    sha = hashlib.sha256(csv.read_bytes()).hexdigest()
    update(out / "agent_role_council_summary.json", lambda j: j.update(
        latest_resolved_round=current,
        handoff_tasks=[
            {"priority": "watch", "issue_code": "PAIR_CONTEXT_INT8_OVERFLOW"},
            {"priority": "watch", "issue_code": "NO_EARLY_PORTFOLIO_CLAIM"},
        ]
    ))
    update(out / "research_cycle_guard.json", lambda j: j.update(data_sha256=sha))
    update(out / "source_validation.json", lambda j: j.update(
        latest={"round": current},
        status="ok", verification="verified_two_result_sources",
        verification_provenance={"draw_csv_sha256": sha},
    ))
    monkeypatch.setattr(
        auto, "validate_trusted_source",
        lambda *_: {"round": current, "trusted": True},
    )
    return tmp_path


def update(path, fn):
    obj = json.loads(path.read_text(encoding="utf-8"))
    fn(obj)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def sample(n=130):
    h = np.zeros((n, 37), dtype=np.int8)
    h[:, :7] = 1
    return h


def test_versioned_wide_pair_context_valid_and_no_uint8_int8_wraparound():
    h = sample(128)
    assert council.pair_context_overflow_count(h) == 49
    result = auto.wide_pair_context(h)
    assert result.shape == (37,)
    assert result.sum() == pytest.approx(1.0)
    assert np.isfinite(result).all()
    assert (result > 0).all()
    assert not np.allclose(result, expert_probabilities(h)["pair_context"])


def test_wide_candidate_matches_direct_big_integer_formula_even_at_700_draws():
    h = sample(700)
    q = auto.wide_pair_context(h)
    wide = h.astype(np.int64)
    c = wide.T @ wide
    den = wide.sum(axis=0)
    pair = np.array([np.mean([c[j, k] / max(int(den[k]), 1)
                              for k in range(7)]) for j in range(37)])
    from loto7_evolving_agent import zsoftmax
    assert np.allclose(q, zsoftmax(pair, 1.40), atol=1e-14)
    assert council.pair_context_overflow_count(h) == 49


def test_versioned_candidate_rejects_incorrect_or_future_data():
    h = sample(128)
    for data in (h[:19], np.ones((128, 36), dtype=np.int8),
                 np.ones((128, 37), dtype=np.int8),
                 h.astype(float), np.full((128, 37), -1)):
        with pytest.raises(ValueError, match="require"):
            auto.wide_pair_context(data)


def test_retro_diagnostics_use_prior_prefix_only():
    h = sample(135)
    d = auto.compare_prefixes(h, n=20)
    assert d["first_historical_round"] == 116
    assert d["last_historical_round"] == 135
    assert d["rounds"] == 20
    assert d["independent_oos"] is False
    assert d["retrospective_optimized_model_selection_authorized"] is False
    assert d == auto.compare_prefixes(h, n=20)


def test_max_bounded_history_and_no_false_prospective_claim():
    with pytest.raises(ValueError, match="bounded"):
        auto.compare_prefixes(sample(), n=121)


def test_live_council_watch_auto_improvement_is_research_only(project):
    report = auto.evaluate(project, now=NOW)
    assert report["version"] == auto.VERSION
    assert report["source_two_result_verified"]
    assert report["status"] == "research_fix_checked_only_not_production_resolved"
    assert report["new_optimizer_trials"] == 0
    assert not report["registered_future_oos_modified"]
    assert not report["production_modified"]
    assert not report["champion_modified"]
    assert not report["verified_predictive_edge"]
    assert {x["code"] for x in report["issues"]} == {
        "PAIR_CONTEXT_INT8_OVERFLOW", "NO_EARLY_PORTFOLIO_CLAIM"
    }
    pair = report["issues"][0]
    assert pair["candidate_numerical_overflow_cells"] == 0
    assert pair["legacy_corrupted_cooccurrence_cells"] > 0
    assert pair["historical_diagnostics"]["rounds"] == 120
    assert pair["requires_independent_future_oos_before_promotion"]
    assert not pair["production_fix_deployed"]
    assert pair["corrected_distribution_sum"] == pytest.approx(1.0)
    assert report["issues"][1]["does_not_count_as_broken_software"]


def test_no_file_written_during_read_only_audit(project):
    before = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob("*") if p.is_file()}
    auto.evaluate(project, now=NOW)
    assert before == {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in project.rglob("*") if p.is_file()}


def test_unverified_source_is_never_scored(project, monkeypatch):
    monkeypatch.setattr(auto, "validate_trusted_source",
                        lambda *_: {"round": 700, "trusted": False})
    report = auto.evaluate(project, now=NOW)
    assert report["status"] == "awaiting_independent_draw_verification"
    assert report["issues"][0]["historical_diagnostics"]["rounds"] == 0


def test_stale_council_and_csv_guard_refuse_to_publish_auto_resolved(project):
    p = project / "loto7_agent_output/agent_role_council_summary.json"
    # Use an actually stale round rather than a number that becomes
    # current when the next real draw arrives.
    current = council.round_id(make_history(read_csv_flexible(project / "loto7.csv"))[1]["回別"].iloc[-1])
    update(p, lambda j: j.update(latest_resolved_round=current - 1))
    with pytest.raises(ValueError, match="stale council"):
        auto.evaluate(project, now=NOW)


def test_corrupted_guard_sha_fails_closed(project):
    p = project / "loto7_agent_output/research_cycle_guard.json"
    update(p, lambda j: j.update(data_sha256="0" * 64))
    with pytest.raises(ValueError, match="stale council"):
        auto.evaluate(project, now=NOW)


def test_duplicate_watch_issue_is_rejected(project):
    p = project / "loto7_agent_output/agent_role_council_summary.json"
    update(p, lambda j: j["handoff_tasks"].append(
        {"priority": "watch", "issue_code": "PAIR_CONTEXT_INT8_OVERFLOW"}
    ))
    with pytest.raises(ValueError, match="duplicate"):
        auto.evaluate(project, now=NOW)


def test_unrecognized_watch_is_reported_as_human_escalation(project):
    p = project / "loto7_agent_output/agent_role_council_summary.json"
    update(p, lambda j: j["handoff_tasks"].append(
        {"priority": "block", "issue_code": "UNKNOWN_PROSPECTIVE_INTEGRITY"}
    ))
    result = auto.evaluate(project, now=NOW)
    assert result["status"] == "needs_existing_workflow_or_human_review"
    assert result["issues"][-1]["resolution"] == "safety_escalation_not_automatically_resolved"
    assert result["fully_automatic_promotion_authorized"] is False


def test_result_stable_at_fixed_time_and_timestamp_must_be_aware(project):
    assert auto.evaluate(project, now=NOW) == auto.evaluate(project, now=NOW)
    with pytest.raises(ValueError, match="timezone"):
        auto.evaluate(project, now=datetime(2026, 10, 29))


def test_workflow_has_only_two_report_outputs_and_trigger_from_council():
    workflow = (ROOT / ".github/workflows/watch_auto_improvement.yml").read_text()
    assert "LOTO7 Agent Role Council" in workflow
    assert "workflow_run:" in workflow
    assert "watch_auto_improvement.py" in workflow
    assert "loto7_agent_output/watch_auto_improvement_report.json" in workflow
    assert "loto7_agent_output/watch_auto_improvement_report.md" in workflow
    assert "model_champion.json" not in workflow.split("git add --", 1)[1].split("\n", 4)[0]
