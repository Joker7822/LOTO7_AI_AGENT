"""Public dashboard telemetry must not change or fabricate scientific evidence."""
import csv
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import dashboard_status_snapshot as d

JST = timezone(timedelta(hours=9))
FIXED = datetime(2026, 10, 18, 21, 16, tzinfo=JST)


def all_workflows():
    return [
        {"file": filename, "label": label, "health": "ok", "status": "completed",
         "conclusion": "success", "run_id": 123, "url": None,
         "updated_at": FIXED.isoformat(), "recent_failure_count": 0}
        for filename, label in d.WORKFLOWS.items()
    ]


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "testrepo"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    src = Path("loto7_agent_output")
    for filename in d.SOURCE_FILES.values():
        shutil.copyfile(src / filename, out / filename)
    for filename in [
        "future_holdout_results.csv",
        "joint_set_v2_signal_oos_state.json",
        "continuous_learning_agent_state.json",
    ]:
        shutil.copyfile(src / filename, out / filename)
    return root


def test_real_portfolio_oos_is_exactly_prefrozen_and_no_fabricated_future_signal(project):
    snapshot = d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    assert snapshot["version"] == d.VERSION
    assert snapshot["source_commit"] == "a" * 40
    assert snapshot["sources"]["signal"]["trusted_draws"] == 0
    assert snapshot["sources"]["learning"]["trusted_draws"] == 0
    assert snapshot["series"]["v2"] == []
    assert snapshot["series"]["adaptive"] == []
    rows = snapshot["series"]["portfolio"]
    assert len(rows) == snapshot["sources"]["holdout"]["trusted_draws"]
    assert rows[0]["round"] == snapshot["sources"]["holdout"]["start_target_round"]
    assert rows[-1]["round"] == rows[0]["round"] + len(rows) - 1
    assert rows[-1]["mean_delta_vs_random"] < 0  # currently not a validated edge
    assert snapshot["series"]["scope"].startswith("genuinely_prospective")


def test_only_minimal_public_state_no_tickets_or_private_sources(project):
    sources, _ = d.read_sources(project / "loto7_agent_output")
    assert "config" not in sources["champion"]
    assert "predicted_numbers" not in json.dumps(sources)
    assert "api_key" not in json.dumps(sources)
    assert "db_password" not in json.dumps(sources)
    assert set(sources["production"]) == {"published", "target_round", "published_at_jst"}
    assert "mizuho" not in sources["source"]["sources"]
    assert "main" in sources["source"]["latest"]  # actual winning numbers are public


def test_reject_missing_or_mismatched_future_evidence(project):
    p = project / "loto7_agent_output" / "future_holdout_results.csv"
    original = p.read_bytes()
    p.unlink()
    with pytest.raises(ValueError, match="portfolio"):
        d.create_snapshot(project, all_workflows(), now=FIXED, ref="b" * 40)
    p.write_bytes(original)
    with p.open(encoding="utf-8-sig", newline="") as f:
        original_rows = list(csv.DictReader(f))
    original_rows[-1]["source_verification"] = "single_untrusted_result"
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=original_rows[0].keys())
        writer.writeheader()
        writer.writerows(original_rows)
    with pytest.raises(ValueError, match="unverified"):
        d.create_snapshot(project, all_workflows(), now=FIXED, ref="b" * 40)


def test_no_retrospective_portfolio_freeze(project):
    path = project / "loto7_agent_output" / "future_holdout_results.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        values = list(csv.DictReader(f))
    values[0]["frozen_at_jst"] = "2026-09-04T21:00:00+09:00"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=values[0].keys())
        w.writeheader()
        w.writerows(values)
    with pytest.raises(ValueError, match="non-prefrozen"):
        d.read_portfolio(project / "loto7_agent_output",
                         d.read_sources(project / "loto7_agent_output")[0]["holdout"])


def test_fail_closed_invented_v2_results_without_graded_state(project):
    out = project / "loto7_agent_output"
    (out / "joint_set_v2_signal_oos_results.csv").write_text(
        "round,source_verification,trusted,frozen_at_jst,draw_date\n"
        "701,verified_two_result_sources,true,2026-10-29T10:00:00+09:00,2026-10-30\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="v2 signal"):
        d.read_future_series(out, d.read_sources(out)[0])


def test_tampered_continuous_learning_hash_is_blocked(project):
    out = project / "loto7_agent_output"
    (out / "continuous_learning_agent_results.jsonl").write_text(
        '{"target_round":701,"previous_record_sha256":"GENESIS","record_sha256":"fake"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA integrity"):
        d.read_future_series(out, d.read_sources(out)[0])


def test_snapshot_is_deterministic_and_run_list_must_be_complete(project):
    first = d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    second = d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    assert first == second
    with pytest.raises(ValueError, match="workflow telemetry"):
        d.create_snapshot(project, all_workflows()[:-1], now=FIXED, ref="a" * 40)


def test_source_evidence_is_not_modified(project):
    before = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    after = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    assert after == before
    assert all(not filename.endswith("registry.json") for filename in d.SOURCE_FILES.values())



def test_optional_scientific_lab_is_hidden_until_registered(project):
    value, fingerprint = d.scientific_research_projection(
        project, project / "loto7_agent_output")
    assert value == {"status": "not_yet_published", "future_draws": None}
    assert fingerprint is None


def test_scientific_projection_whitelists_scores_and_detects_stale_inputs(project):
    from loto7_evolving_agent import fingerprint_file
    out = project / "loto7_agent_output"
    for name in ("accuracy_extension_agent_registration.json",
                 "accuracy_extension_agent_state.json"):
        shutil.copyfile(Path("loto7_agent_output") / name, out / name)
    reg = json.loads((out / "accuracy_extension_agent_registration.json").read_text())
    source_sha = fingerprint_file(project / "loto7.csv")
    report = {
        "version": "advanced-validation-lab-v1",
        "historical_data_sha256": source_sha,
        "source_model_manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "production_secret_key": "this must never be visible",
        "historical_exploratory": {
            "round_start": 640, "round_end": 699,
            "original_four": {"mean_log_edge": .000017, "mean_top7_hits": 1.4333},
            "candidate_five": {"mean_log_edge": -.000026, "mean_top7_hits": 1.3833},
            "paired_block_bootstrap": {"low95": -.001, "high95": .001,
                                       "mean_five_minus_four": -.000043},
            "matched_full_budget_fair_draws": {
                "worlds": 32,
                "max_statistic_selection_adjusted_empirical_tail_p": .42
            },
        },
        "future_e_monitor": {
            "verified_prefrozen_draws": 0,
            "current_e_value": 1.0, "max_e_value": 1.0,
            "ville_threshold": 20.0, "threshold_crossed": False, "series": [],
        },
    }
    path = out / "advanced_validation_lab_summary.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    result, digest = d.scientific_research_projection(project, out)
    assert result["status"] == "verified_diagnostic_only"
    assert result["future_e_series"] == []
    assert result["future_current_e"] == 1.0
    assert result["future_draws"] == 0
    assert "production_secret_key" not in json.dumps(result)
    assert digest
    report["historical_data_sha256"] = "obsolete"
    path.write_text(json.dumps(report), encoding="utf-8")
    stale, _ = d.scientific_research_projection(project, out)
    assert stale["status"] == "stale_or_mismatched_evidence"
    assert stale["future_draws"] is None
