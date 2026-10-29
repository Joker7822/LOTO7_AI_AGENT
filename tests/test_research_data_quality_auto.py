"""Data integrity and autonomous priority recovery: fail-closed regressions."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import research_data_quality_auto as quality
import research_autonomy_orchestrator as queue
import online_literature_auto_verify as rotate
import always_on_accuracy_agent as discovery
import research_evidence_resilience as biblios
import research_literature_pipeline as literature

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
BEFORE = datetime(2026, 10, 30, 7, 10, tzinfo=JST)
AFTER = datetime(2026, 10, 30, 21, 0, tzinfo=JST)


def put(path, fn):
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def project(tmp_path, monkeypatch):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    shutil.copy(ROOT / "loto7.csv", tmp_path / "loto7.csv")
    for name in ("source_validation.json", "research_cycle_guard.json",
                 "advanced_validation_lab_summary.json",
                 "research_autonomy_priority_queue.json",
                 "research_verified_publications.json",
                 discovery.STATE, discovery.LEDGER):
        shutil.copy(ROOT / "loto7_agent_output" / name, out / name)
    digest = hashlib.sha256((tmp_path / "loto7.csv").read_bytes()).hexdigest()
    import loto7_v4_runner as v4
    from loto7_evolving_agent import read_csv_flexible, make_history
    x, clean = make_history(read_csv_flexible(tmp_path / "loto7.csv"))
    final = v4.parse_round(clean["回別"].iloc[-1])
    assert final == len(x)
    put(out / "source_validation.json", lambda s: (
        s.update(verification="verified_two_result_sources",
                 status="ok",
                 verification_provenance={"draw_csv_sha256": digest}),
        s.setdefault("sources", {}).update(
            official_schedule={"round": final+1, "date": "2026-10-30"})
    ))
    put(out / "research_cycle_guard.json",
        lambda s: s.update(data_sha256=digest))
    put(out / "advanced_validation_lab_summary.json",
        lambda s: s.update(historical_data_sha256=digest))
    put(out / "research_autonomy_priority_queue.json",
        lambda s: s.update(
            draw_history_sha256=digest,
            input_evidence_sha256={
                **s["input_evidence_sha256"],
                "source": hashlib.sha256((out / "source_validation.json").read_bytes()).hexdigest(),
                "bibliography": hashlib.sha256((out / "research_verified_publications.json").read_bytes()).hexdigest(),
            }
        ))
    monkeypatch.setattr(quality, "validate_trusted_source",
                        lambda *_: {"round": final, "trusted": True})
    return tmp_path


def test_morning_of_next_friday_draw_is_not_misdiagnosed_as_stale(project):
    report = quality.audit(project, now=BEFORE)
    assert report["quality_condition"] == "checked_healthy"
    assert report["before_next_draw_result_deadline"] is True
    assert not report["quality_issues"]
    assert report["requested_recovery_workflow"] is None
    assert report["historical_rows_checked"] >= 699
    assert report["source_two_independently_verified"]


def test_only_real_post_result_deadline_enters_trusted_recovery(project):
    r = quality.audit(project, now=AFTER)
    assert r["requested_recovery_workflow"] == "friday_result_check_watchdog.yml"
    assert "OFFICIAL_RESULT_PAST_DUE" in r["quality_issues"]
    assert r["before_next_draw_result_deadline"] is False
    assert not r["auto_corrected_lottery_numbers"]


def test_trust_failure_prevents_new_graded_facts(project, monkeypatch):
    monkeypatch.setattr(quality, "validate_trusted_source",
                        lambda *_: {"round": quality.v4.parse_round(
                            quality.make_history(quality.read_csv_flexible(
                                project / "loto7.csv"))[1]["回別"].iloc[-1]),
                            "trusted": False})
    report = quality.audit(project, now=BEFORE)
    assert "SOURCE_TWO_PROVIDER_CONFIRMATION_REQUIRED" in report["quality_issues"]
    assert not report["source_two_independently_verified"]
    assert report["latest_verified_round"] is None


def test_stale_scientific_lab_dispatches_only_existing_registered_workflow(project):
    p = project / "loto7_agent_output/advanced_validation_lab_summary.json"
    put(p, lambda s: s.update(historical_data_sha256="0"*64))
    result = quality.audit(project, now=BEFORE)
    assert result["requested_recovery_workflow"] == "advanced_validation_lab.yml"
    assert "REGISTERED_SCIENCE_OUTDATED" in result["quality_issues"]


def test_guard_data_sha_mismatch_blocks_science_dispatch(project):
    put(project / "loto7_agent_output/research_cycle_guard.json",
        lambda x: x.update(data_sha256="b"*64))
    put(project / "loto7_agent_output/advanced_validation_lab_summary.json",
        lambda x: x.update(historical_data_sha256="0"*64))
    report = quality.audit(project, now=BEFORE)
    assert "RESEARCH_BUDGET_GUARD_STALE" in report["quality_issues"]
    assert report["requested_recovery_workflow"] is None


def test_duplicate_missing_or_corrupt_main_draw_fails_closed(project):
    p = project / "loto7.csv"
    original = p.read_text(encoding="utf-8")
    p.write_text(original + original.splitlines()[-1] + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        quality.audit(project, now=BEFORE)


def test_bad_bonus_overlap_is_not_silently_cleaned(project):
    from loto7_evolving_agent import make_history, read_csv_flexible
    import pandas as pd
    df = read_csv_flexible(project/"loto7.csv")
    # Direct mutate a bonus field in a temporary CSV (never the main repo).
    main = sorted(map(int, df.iloc[0]["本数字"].split()))
    df.loc[df.index[0], "ボーナス数字"] = f"{main[0]:02d} {main[1]:02d}"
    df.to_csv(project/"loto7.csv", index=False)
    with pytest.raises(ValueError, match="bonus overlaps"):
        quality.audit(project, now=BEFORE)


def test_no_production_and_no_trial_override_and_read_only(project):
    sources = {p: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in project.rglob("*") if p.is_file()}
    report = quality.audit(project, now=BEFORE)
    assert report["new_optimizer_trials"] == 0
    assert report["production_or_champion_modified"] is False
    assert report["registered_future_oos_modified"] is False
    assert report["auto_corrected_lottery_numbers"] is False
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources} == sources


def test_rejects_forged_queue_model_authority(project):
    put(project/"loto7_agent_output/research_autonomy_priority_queue.json",
        lambda q: q["authority"].update(production_or_champion_update=True))
    with pytest.raises(ValueError, match="forbidden model"):
        quality.audit(project, now=BEFORE)


def test_source_report_sha_drift_detected_as_an_issue(project):
    put(project / "loto7_agent_output/source_validation.json",
        lambda x: x["verification_provenance"].update(draw_csv_sha256="0"*64))
    report = quality.audit(project, now=BEFORE)
    assert "SOURCE_TWO_PROVIDER_CONFIRMATION_REQUIRED" in report["quality_issues"]
    assert not report["source_two_independently_verified"]


def test_official_schedule_must_be_a_real_friday(project):
    put(project / "loto7_agent_output/source_validation.json",
        lambda s: s["sources"].update(
            official_schedule={"round": s["latest"]["round"]+1,
                               "date": "2026-10-29"}))
    with pytest.raises(ValueError, match="Friday"):
        quality.audit(project, now=BEFORE)


def test_priorities_do_not_exec_untrusted_task_text(project):
    out = project/"loto7_agent_output"
    state = discovery.read_json(out/discovery.STATE)
    chain = discovery.read_chain(out/discovery.LEDGER)
    papers = literature.checked_papers(state, chain)
    prev = json.loads((out/biblios.EVIDENCE).read_text())
    known = {p["doi"]: p for p in prev["verifications"]}
    q = out/"research_autonomy_priority_queue.json"
    put(q, lambda x: x["tasks"][0].update(
        next_step="os.system('rm -rf /')"))
    indices, qsha, cursor = rotate._priority_indices(
        out, rotate.digest(out/discovery.STATE),
        chain[-1]["record_sha256"], papers, known, prev
    )
    assert len(indices) <= len(papers)
    assert all(isinstance(x, int) for x in indices)
    assert "rm -rf" not in str([papers[i] for i in indices])


def test_priority_status_cannot_launder_changed_review_permissions(project):
    out = project/"loto7_agent_output"
    put(out/"research_autonomy_priority_queue.json",
        lambda x: next(t for t in x["tasks"] if
                       t["lane"] == "bibliography").update(
                           forecast_or_production_change_authorized=True
                       ))
    state = discovery.read_json(out/discovery.STATE)
    chain = discovery.read_chain(out/discovery.LEDGER)
    papers = literature.checked_papers(state, chain)
    prior = json.loads((out/biblios.EVIDENCE).read_text())
    known = {p["doi"]: p for p in prior["verifications"]}
    # Authenticate all prerequisites so the forged action is actually
    # inspected. Stale/unauthenticated queues are correctly ignored instead.
    put(out/"research_autonomy_priority_queue.json",
        lambda q: q.update(
            version="research-priority-orchestrator-v1",
            source_two_verified=True,
            input_evidence_sha256={
                **q["input_evidence_sha256"],
                "bibliography": rotate.digest(out/biblios.EVIDENCE),
            },
            authority={
                "workflows_dispatched": False,
                "production_or_champion_update": False,
            },
        ))
    with pytest.raises(ValueError, match="elevate"):
        rotate._priority_indices(out, rotate.digest(out/discovery.STATE),
                                 chain[-1]["record_sha256"], papers, known, prior)


def test_seven_day_gap_is_not_a_problem_until_next_result_published(project):
    from research_autonomy_orchestrator import build_queue
    import research_application_gate as gate
    import research_evidence_resilience as verify
    import research_literature_pipeline as lit
    # Exercise the precise scheduling rule separately from the locked
    # research-science fixture.
    out = project/"loto7_agent_output"
    original = discovery.read_json(out/"source_validation.json")
    original["latest"]["date"] = "2026-10-23"
    original["latest"]["round"] = 700
    original["sources"]["official_schedule"] = {"round": 701, "date": "2026-10-30"}
    info = {"latest_round": 700, "two_source_verified": True,
            "research_mode": "WAIT_FOR_NEW_DATA",
            "same_data_trials": 800, "max_same_data_trials": 800,
            "draw_history_sha256": "d"*64,
            "source_verification": "verified_two_result_sources",
            "candidate_future_draws": 0, "v2_future_draws": 0}
    application = {"auto_production_release": False,
                   "automatic_model_training": False,
                   "future_oos_or_production_changed": False,
                   "new_experiments_executed": 0,
                   "research_mode": "WAIT_FOR_NEW_DATA",
                   "input_draw_sha256": "d"*64,
                   "trusted_result_source": True,
                   "proposal_count": 0,
                   "application_queue": []}
    proposals = {"executed_experiments": 0, "new_trials_consumed": 0,
                 "requires_human_approval": True, "proposals": [], "count": 0}
    publications = {"automatic_adoption": False, "verifications": []}
    a = build_queue(info, application, original, proposals, publications, BEFORE)
    b = build_queue(info, application, original, proposals, publications, AFTER)
    assert "CHECK_SOURCE_FRESHNESS" not in {t["code"] for t in a}
    assert "CHECK_SOURCE_FRESHNESS" in {t["code"] for t in b}


def test_stale_priority_queue_automatically_uses_existing_hourly_research(project):
    path = project / "loto7_agent_output/research_autonomy_priority_queue.json"
    put(path, lambda q: q["input_evidence_sha256"].update(bibliography="0"*64))
    result = quality.audit(project, now=BEFORE)
    assert result["candidate_priority_queue_stale"]
    assert "REGENERATE_PRIORITY_QUEUE_AFTER_SOURCE_UPDATE" in result["quality_issues"]
    assert result["requested_recovery_workflow"] == "always_on_accuracy_research.yml"
    assert result["production_or_champion_modified"] is False


def test_untrusted_source_cannot_dispatch_hourly_research_from_stale_queue(project, monkeypatch):
    path = project / "loto7_agent_output/research_autonomy_priority_queue.json"
    put(path, lambda q: q["input_evidence_sha256"].update(bibliography="0"*64))
    from loto7_evolving_agent import read_csv_flexible, make_history
    count = len(make_history(read_csv_flexible(project/"loto7.csv"))[0])
    monkeypatch.setattr(quality, "validate_trusted_source",
                        lambda *_: {"round": count, "trusted": False})
    result = quality.audit(project, now=BEFORE)
    assert result["requested_recovery_workflow"] is None
    assert not result["source_two_independently_verified"]
