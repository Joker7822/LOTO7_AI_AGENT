"""Autonomous research scheduler: safe plans, never unregistered experiments."""
import copy
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import always_on_accuracy_agent as discovery
import research_application_gate as gate
import research_evidence_resilience as literature
import research_literature_pipeline as pipeline
import research_autonomy_orchestrator as agent

NOW=datetime(2026,10,24,7,30,tzinfo=timezone(timedelta(hours=9)))


@pytest.fixture()
def project(tmp_path):
    root=tmp_path/"research-science"
    out=root/"loto7_agent_output"
    out.mkdir(parents=True)
    shutil.copyfile("loto7.csv",root/"loto7.csv")
    names={
        *discovery.FILES.values(),
        discovery.STATE, discovery.LEDGER,
        pipeline.REVIEW_FILE,pipeline.DESIGN_FILE,
        literature.EVIDENCE,literature.SANDBOX,
        gate.STATUS_FILE,
    }
    for filename in names:
        shutil.copyfile(Path("loto7_agent_output")/filename,out/filename)
    return root


def test_current_research_queue_prioritizes_source_without_inventing_future(project):
    out=project/"loto7_agent_output"
    input_data={p.name:p.read_bytes() for p in out.iterdir() if p.is_file()}
    first=agent.run(project,now=NOW)
    assert first["version"]==agent.VERSION
    assert first["source_two_verified"] is False
    assert first["research_mode"]=="WAIT_FOR_NEW_DATA"
    assert first["tasks"][0]["code"]=="VERIFY_RESULT_SOURCES"
    codes={v["code"] for v in first["tasks"]}
    assert "CHECK_SOURCE_FRESHNESS" in codes
    assert "HOLD_SAME_DATA_SEARCH" in codes
    assert "AWAIT_GENUINE_OOS" in codes
    assert first["counts"]["block"] >= 1
    assert first["authority"]["workflows_dispatched"] is False
    assert all(v["safe_autonomous_action"]=="report_only" and
               v["forecast_or_production_change_authorized"] is False and
               v["new_optimizer_trials_authorized"] is False
               for v in first["tasks"])
    second=agent.run(project,now=NOW)
    assert second==first
    assert set(p.name for p in out.iterdir()) == set(input_data)|{agent.QUEUE,agent.REPORT}
    for name,data in input_data.items():
        assert (out/name).read_bytes()==data
    assert "改善" not in first["evaluation_limit"]


def test_unverified_source_remains_priority_even_with_newer_report(project):
    raw=discovery.read_json(project/"loto7_agent_output"/discovery.FILES["source"])
    info, plans, _, _, _=gate.verify_inputs(project)
    readiness=gate.load(project/"loto7_agent_output"/gate.STATUS_FILE)
    pubs=gate.load(project/"loto7_agent_output"/literature.EVIDENCE)
    raw["latest"]["date"]="2026-10-23"
    tasks=agent.build_queue(info,readiness,raw,plans,pubs,NOW)
    assert tasks[0]["code"]=="VERIFY_RESULT_SOURCES"
    assert "CHECK_SOURCE_FRESHNESS" not in {t["code"] for t in tasks}


def test_research_mode_not_reopened_after_guard_stops(project):
    info, plans, _, _, _=gate.verify_inputs(project)
    readiness=gate.load(project/"loto7_agent_output"/gate.STATUS_FILE)
    pubs=gate.load(project/"loto7_agent_output"/literature.EVIDENCE)
    source=discovery.read_json(project/"loto7_agent_output"/discovery.FILES["source"])
    for mode in ("VALIDATION_ONLY","WAIT_FOR_NEW_DATA"):
        cfg={**info,"research_mode":mode,"search_enabled":False}
        app={**readiness,"research_mode":mode}
        acts=agent.build_queue(cfg,app,source,plans,pubs,NOW)
        assert "HOLD_SAME_DATA_SEARCH" in {t["code"] for t in acts}
        assert "AUDIT_ENABLED_RESEARCH_BUDGET" not in {t["code"] for t in acts}
    cfg={**info,"research_mode":"SEARCH","search_enabled":True}
    app={**readiness,"research_mode":"SEARCH"}
    acts=agent.build_queue(cfg,app,source,plans,pubs,NOW)
    assert "HOLD_SAME_DATA_SEARCH" not in {t["code"] for t in acts}
    assert "AUDIT_ENABLED_RESEARCH_BUDGET" in {t["code"] for t in acts}
    assert all(x["new_optimizer_trials_authorized"] is False for x in acts)


def test_bibliographic_conflicts_are_not_treated_as_verified(project):
    info, plans, _, _, _=gate.verify_inputs(project)
    app=gate.load(project/"loto7_agent_output"/gate.STATUS_FILE)
    original=gate.load(project/"loto7_agent_output"/literature.EVIDENCE)
    verified=copy.deepcopy(original)
    verified["verifications"][0]["status"]="not_yet_checked"
    verified["verifications"][1]["status"]="conflict_do_not_use"
    verified["verifications"][2]["status"]="single_provider_only"
    source=discovery.read_json(project/"loto7_agent_output"/discovery.FILES["source"])
    events=agent.build_queue(info,app,source,plans,verified,NOW)
    codes={item["code"] for item in events}
    assert "VERIFY_UNCHECKED_DOIS" in codes
    assert "REVIEW_BIBLIO_CONFLICTS" in codes
    assert "RETRY_SINGLE_PROVIDER" in codes


def test_action_approval_mismatch_aborts_without_outputs(project):
    out=project/"loto7_agent_output"
    p=out/gate.STATUS_FILE
    doc=json.loads(p.read_text())
    doc["auto_production_release"]=True
    p.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match="automatic training or production authority"):
        agent.run(project,now=NOW)
    assert not (out/agent.QUEUE).exists()
    assert not (out/agent.REPORT).exists()


def test_stale_source_sha_or_bad_null_sandbox_blocks_schedule(project):
    out=project/"loto7_agent_output"
    csv=project/"loto7.csv"
    csv.write_bytes(csv.read_bytes()+b"\nmodified")
    with pytest.raises(ValueError,match="different draw-history SHA"):
        agent.run(project,now=NOW)
    shutil.copyfile("loto7.csv",csv)
    p=out/literature.SANDBOX
    data=json.loads(p.read_text())
    data["real_model_experiments_executed"]=1
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="unauthorized real experiment"):
        agent.run(project,now=NOW)


def test_no_hindsight_untrusted_action_or_invalid_do_i_can_be_published(project):
    info,plans,_,_,_=gate.verify_inputs(project)
    app=gate.load(project/"loto7_agent_output"/gate.STATUS_FILE)
    pubs=gate.load(project/"loto7_agent_output"/literature.EVIDENCE)
    source=discovery.read_json(project/"loto7_agent_output"/discovery.FILES["source"])
    broken=copy.deepcopy(app)
    broken["application_queue"][0]["experiment_execution_allowed"]=True
    with pytest.raises(ValueError,match="untrusted action"):
        agent.build_queue(info,broken,source,plans,pubs,NOW)
    with pytest.raises(ValueError,match="invalid DOI"):
        agent.task("BAD","watch","bibliography","literature_verifier",
                   "a","b","c","d",doi="javascript:alert(1)")


def test_future_dated_source_rejected(project):
    info,plans,_,_,_=gate.verify_inputs(project)
    app=gate.load(project/"loto7_agent_output"/gate.STATUS_FILE)
    pubs=gate.load(project/"loto7_agent_output"/literature.EVIDENCE)
    source=discovery.read_json(project/"loto7_agent_output"/discovery.FILES["source"])
    source["latest"]["date"]="2027-01-01"
    with pytest.raises(ValueError,match="future-dated"):
        agent.build_queue(info,app,source,plans,pubs,NOW)


def test_conflicts_and_papers_never_create_execute_or_elevate_permission(project):
    data=agent.run(project,now=NOW)
    allowed=set(agent.SEVERITY)
    assert all(task["priority"] in allowed for task in data["tasks"])
    assert all(task["owner"] in agent.ALLOWED_OWNERS for task in data["tasks"])
    assert all(task["lane"] in agent.ALLOWED_LANES for task in data["tasks"])
    assert len({task["id"] for task in data["tasks"]}) == len(data["tasks"])
    assert data["counts"]=={
        priority:sum(task["priority"]==priority for task in data["tasks"])
        for priority in ("block","watch","info")
    }


def test_recurrence_and_backlog_reorder_only_within_severity(project):
    info, plans, _, _, _ = gate.verify_inputs(project)
    app = gate.load(project / "loto7_agent_output" / gate.STATUS_FILE)
    pubs = gate.load(project / "loto7_agent_output" / literature.EVIDENCE)
    source = discovery.read_json(project / "loto7_agent_output" / discovery.FILES["source"])
    pubs = copy.deepcopy(pubs)
    pubs["verifications"][0]["status"] = "not_yet_checked"
    pubs["verifications"][1]["status"] = "conflict_do_not_use"
    initial = agent.build_queue(info, app, source, plans, pubs, NOW)
    assert all(t["priority_score"] >= 0 for t in initial)
    previous = {"tasks": initial}
    next_round = agent.build_queue(info, app, source, plans, pubs, NOW, previous=previous)
    assert {t["id"] for t in next_round} == {t["id"] for t in initial}
    assert all(t["recurrence_cycles"] == 2 for t in next_round)
    assert [agent.SEVERITY[t["priority"]] for t in next_round] == sorted(
        agent.SEVERITY[t["priority"]] for t in next_round
    )
    assert all(t["safe_autonomous_action"] == "report_only" for t in next_round)


def test_quality_block_is_not_automatically_repaired_or_trusted(project):
    import research_data_quality as quality_guard

    info, plans, _, _, _ = gate.verify_inputs(project)
    app = gate.load(project / "loto7_agent_output" / gate.STATUS_FILE)
    pubs = gate.load(project / "loto7_agent_output" / literature.EVIDENCE)
    source = discovery.read_json(project / "loto7_agent_output" / discovery.FILES["source"])
    quality = {
        "version": quality_guard.VERSION,
        "draw_csv_sha256": info["draw_history_sha256"],
        "source_csv_modified": False,
        "source_attestation_modified": False,
        "production_or_oos_modified": False,
        "status": "block",
        "issues": [{"severity": "block", "code": "DRAW_SHA_MISMATCH"}],
    }
    tasks = agent.build_queue(info, app, source, plans, pubs, NOW, quality=quality)
    flagged = next(t for t in tasks if t["code"] == "REVIEW_DATA_QUALITY")
    assert flagged["priority"] == "block"
    assert flagged["forecast_or_production_change_authorized"] is False
    quality["status"] = "pass"
    with pytest.raises(ValueError, match="data quality severity mismatch"):
        agent.build_queue(info, app, source, plans, pubs, NOW, quality=quality)


def test_weekly_freshness_waits_until_result_window(project):
    import research_data_quality as quality_guard

    last = datetime(2026, 10, 23, tzinfo=timezone(timedelta(hours=9))).date()
    source = {"latest": {"round": 700, "date": "2026-10-23"},
              "sources": {"official_schedule": {"round": 701, "date": "2026-10-30"}}}
    threshold = quality_guard.next_result_deadline(last, source)
    assert threshold == datetime(2026, 10, 30, 20, 30, tzinfo=timezone(timedelta(hours=9)))
    assert datetime(2026, 10, 30, 7, tzinfo=timezone(timedelta(hours=9))) < threshold
