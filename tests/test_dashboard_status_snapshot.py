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
        "joint_set_v2_signal_oos_results.csv",
        "continuous_learning_agent_state.json",
        "continuous_learning_agent_results.jsonl",
        "predictions.csv",
        "prediction_corrections.csv",
        "actual_results.csv",
    ]:
        # Isolated CI also replays the pinned 699 fixture where no future
        # result has been graded yet. The actual scored ledgers are optional
        # there; if present (701+), copy the *real* matching evidence.
        evidence_path = src / filename
        if evidence_path.is_file():
            shutil.copyfile(evidence_path, out / filename)
    shutil.copyfile("loto7.csv", root / "loto7.csv")
    return root


def test_real_portfolio_oos_is_exactly_prefrozen_and_no_fabricated_future_signal(project):
    snapshot = d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    assert snapshot["version"] == d.VERSION
    assert snapshot["source_commit"] == "a" * 40
    # The first 701 pre-draw forecasts may now be legitimately graded.
    # Never assume the once-empty prospective ledgers stay empty forever.
    assert (len(snapshot["series"]["v2"]) ==
            snapshot["sources"]["signal"]["trusted_draws"])
    assert (len(snapshot["series"]["adaptive"]) ==
            snapshot["sources"]["learning"]["trusted_draws"])
    assert all(r["round"] >= 701 for r in snapshot["series"]["v2"])
    assert all(r["round"] >= 701 for r in snapshot["series"]["adaptive"])
    rows = snapshot["series"]["portfolio"]
    assert len(rows) == snapshot["sources"]["holdout"]["trusted_draws"]
    assert rows[0]["round"] == snapshot["sources"]["holdout"]["start_target_round"]
    # Untrusted draws can occur between trusted rounds (e.g. round 700).
    # Skipping them is mandatory, rather than inventing a contiguous graded
    # sequence. Require the public view to match only truly trusted rows.
    ledger = d.rows(project / "loto7_agent_output/future_holdout_results.csv")
    trusted_rounds = [int(r["round"]) for r in ledger if d.result_is_trusted(r)]
    assert [r["round"] for r in rows] == trusted_rounds
    assert trusted_rounds == sorted(set(trusted_rounds))
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
    # Tamper with a TRUSTED result, not the most recent diagnostic-only
    # untrusted result (round 700 is allowed to be explicitly untrusted).
    last_verified = next(i for i in range(len(original_rows) - 1, -1, -1)
                         if original_rows[i]["trusted"].lower() == "true")
    original_rows[last_verified]["source_verification"] = "single_untrusted_result"
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
    state = out / "joint_set_v2_signal_oos_state.json"
    summary = out / "joint_set_v2_signal_oos_summary.json"
    for path in (state, summary):
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["trusted_draws"] = 0
        if path == state:
            obj["graded_rounds"] = []
        path.write_text(json.dumps(obj), encoding="utf-8")
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
    shutil.copyfile(Path("loto7.csv"), project / "loto7.csv")
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



def test_always_on_activity_optional_and_public_whitelist(project):
    out = project / "loto7_agent_output"
    empty, digest = d.always_on_research_projection(out)
    assert empty == {"status": "not_yet_started"}
    assert digest is None
    state = {
        "version": "always-on-accuracy-research-v1",
        "status": "active_bounded_research",
        "sequence": 9, "last_activity_jst": "2026-10-20T10:17:00+09:00",
        "current_phase": "literature_search", "current_activity": "文献調査",
        "online_search_status": "searched", "research_mode": "VALIDATION_ONLY",
        "two_source_verified": False, "new_papers_count": 1,
        "papers": [{"title": "Online forecasting", "year": 2026,
                    "doi": "10.1234/abc",
                    "url": "https://doi.org/10.1234/abc",
                    "review_status": "unreviewed"}],
        "review_notes": ["外部結果は未検証"],
        "promotion_authorized": False,
        "read_only_scientific_activity": True,
        "secret_api_key": "never expose me",
    }
    p = out / "always_on_accuracy_research_state.json"
    p.write_text(json.dumps(state, ensure_ascii=False))
    projected, hash_ = d.always_on_research_projection(out)
    assert hash_
    assert projected["status"] == "active_bounded_research"
    assert projected["papers"][0]["review_status"] == "unreviewed"
    assert "secret_api_key" not in json.dumps(projected)
    state["promotion_authorized"] = True
    p.write_text(json.dumps(state, ensure_ascii=False))
    unsafe, _ = d.always_on_research_projection(out)
    assert unsafe["status"] == "invalid_or_unsafe"



def test_latest_published_five_tickets_are_only_issued_production(project):
    result = d.create_snapshot(project, all_workflows(), now=FIXED, ref="a" * 40)
    forecast = result["latest_prediction"]
    assert forecast["status"] == "published"
    state = json.loads((project / "loto7_agent_output" /
                        "weekly_production_prediction_state.json").read_text())
    target = int(state["target_round"].strip("第回"))
    assert forecast["target_round"] == target
    assert len(forecast["tickets"]) == 5
    assert all(len(set(row["numbers"])) == len(row["numbers"]) == 7
               for row in forecast["tickets"])
    if target == 701:
        assert forecast["tickets"][0]["numbers"] == [6, 16, 22, 23, 24, 25, 28]
    assert forecast["result_status"] == (
        "independently_verified" if forecast["current_result"]
        else "awaiting_independently_verified_draw")
    if forecast["latest_verified"] is not None:
        assert forecast["latest_verified"]["round"] == target - 1
        assert forecast["latest_verified"]["source_verification"] == d.TRUST
    assert "prediction_ledger" not in result["sources"]
    assert not any("candidate_ticket" in k for k in result.keys())


def test_no_unpublished_or_invalidated_prediction_can_be_rendered(project):
    state_path = project / "loto7_agent_output" / "weekly_production_prediction_state.json"
    state=json.loads(state_path.read_text(encoding="utf-8"))
    state["published"]=False
    state_path.write_text(json.dumps(state),encoding="utf-8")
    doc=d.create_snapshot(project,all_workflows(),now=FIXED,ref="b"*40)
    assert doc["latest_prediction"]["tickets"] == []
    assert doc["latest_prediction"]["status"] == "not_published"



def test_application_projection_is_missing_until_first_safe_report(project):
    data, checksum = d.research_application_projection(project, project / "loto7_agent_output")
    assert data["status"] == "not_yet_published"
    assert checksum is None


def test_application_projection_rejects_publication_and_unregistered_claims(project):
    from loto7_evolving_agent import fingerprint_file
    out = project / "loto7_agent_output"
    sample = {
        "version": "research-application-gate-v1",
        "input_draw_sha256": fingerprint_file(project / "loto7.csv"),
        "research_mode": json.loads((out / "research_cycle_guard.json").read_text())["mode"],
        "actual_prediction_accuracy_improvement_verified": False,
        "automatic_model_training": False, "auto_production_release": False,
        "future_oos_or_production_changed": False, "new_experiments_executed": 0,
        "reviewed_publication_count": 4, "two_provider_bibliographic_matches": 1,
        "synthetic_control": {"status": "synthetic_controls_passed"},
        "proposal_count": 1,
        "application_queue": [{
            "topic": "calibration",
            "status": "awaiting_full_text_and_methodology_review",
            "two_provider_matched_dois": ["10.1234/test"],
            "experiment_execution_allowed": False,
            "production_adoption_allowed": False,
            "requires_human_approval": True,
        }],
        "injected_secret": "never expose this",
    }
    p = out / "research_application_readiness.json"
    p.write_text(json.dumps(sample))
    projected, digest = d.research_application_projection(project, out)
    assert digest
    assert projected["status"] == "research_review_ready_only"
    assert projected["tasks"][0]["two_provider_matches"] == 1
    assert "injected_secret" not in json.dumps(projected)
    sample["auto_production_release"] = True
    p.write_text(json.dumps(sample))
    invalid, _ = d.research_application_projection(project, out)
    assert invalid["status"] == "stale_or_unsafe"



def test_autonomous_research_priority_snapshot_is_absent_until_verified(project):
    out = project / "loto7_agent_output"
    view, fp = d.research_priority_projection(project, out)
    assert view == {"status": "not_yet_published", "tasks": []}
    assert fp is None


def test_priority_projection_whitelists_actions_and_rejects_autonomous_promotions(project):
    from loto7_evolving_agent import fingerprint_file
    out = project / "loto7_agent_output"
    source = json.loads((out / "source_validation.json").read_text())
    guard = json.loads((out / "research_cycle_guard.json").read_text())
    trusted = source["status"] == "ok" and source["verification"] == "verified_two_result_sources"
    task = {
        "id": "a" * 16, "priority": "block",
        "lane": "source_integrity", "owner": "source_verifier",
        "title": "公式ソースを確認", "reason": "単一ソースのみ",
        "next_step": "公開結果を独立照合",
        "safe_autonomous_action": "report_only",
        "human_approval_required_for_model_change": True,
        "forecast_or_production_change_authorized": False,
        "new_optimizer_trials_authorized": False,
        "secret": "never display",
    }
    payload = {
        "version": "research-priority-orchestrator-v1",
        "draw_history_sha256": fingerprint_file(project / "loto7.csv"),
        "research_mode": guard["mode"],
        "source_two_verified": trusted,
        "latest_source_round": source["latest"]["round"],
        "counts": {"block": 1, "watch": 0, "info": 0},
        "tasks": [task],
        "authority": {
            "automated_model_training": False,
            "research_budget_override": False,
            "retroactive_future_freeze": False,
            "registered_oos_modification": False,
            "production_or_champion_update": False,
            "workflows_dispatched": False,
        },
        "api_key": "never display",
    }
    path = out / "research_autonomy_priority_queue.json"
    path.write_text(json.dumps(payload, ensure_ascii=False))
    safe, fingerprint = d.research_priority_projection(project, out)
    assert fingerprint
    assert safe["status"] == "audited_research_plan"
    assert safe["tasks"][0]["title"] == "公式ソースを確認"
    assert "api_key" not in json.dumps(safe)
    assert "secret" not in json.dumps(safe)
    payload["authority"]["production_or_champion_update"] = True
    path.write_text(json.dumps(payload, ensure_ascii=False))
    rejected, _ = d.research_priority_projection(project, out)
    assert rejected["status"] == "stale_or_unsafe"
    payload["authority"]["production_or_champion_update"] = False
    payload["tasks"][0]["safe_autonomous_action"] = "write_predictions"
    path.write_text(json.dumps(payload, ensure_ascii=False))
    rejected, _ = d.research_priority_projection(project, out)
    assert rejected["status"] == "stale_or_unsafe"


def test_incomplete_existing_v2_csv_fails_closed_before_any_scoring(project):
    out = project / "loto7_agent_output"
    csv_path = out / "joint_set_v2_signal_oos_results.csv"
    csv_path.write_text(
        "round,draw_date,source_verification,trusted,frozen_at_jst\n"
        "701,2026-10-30,verified_two_result_sources,true,2026-10-24T18:31:02+09:00\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="v2 signal"):
        d.read_future_series(out, d.read_sources(out)[0])


@pytest.mark.parametrize("bad_hits", ["2.5", "nan", "inf", "-1", "8"])
def test_future_signal_rejects_noninteger_or_impossible_top7_hits(project, bad_hits):
    out = project / "loto7_agent_output"
    file = out / "joint_set_v2_signal_oos_results.csv"
    if not file.is_file():
        pytest.skip("pinned historical fixture predates the first v2 grade")
    with file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    if not rows:
        pytest.skip("no preregistered result yet")
    rows[0]["top7_hits"] = bad_hits
    with file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="v2 signal"):
        d.read_future_series(out, d.read_sources(out)[0])
