"""Online literature verifier: rotate all DOIs, retain strict evidence limits."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import pytest

import always_on_accuracy_agent as discovery
import online_literature_auto_verify as agent
import research_evidence_resilience as paper_guard
import research_literature_pipeline as reviewer

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 28, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo(tmp_path):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    for name in (discovery.STATE, discovery.LEDGER, paper_guard.EVIDENCE):
        shutil.copy(ROOT / "loto7_agent_output" / name, out / name)
    return tmp_path


def papers_at(root):
    out = root / "loto7_agent_output"
    return reviewer.checked_papers(discovery.read_json(out / discovery.STATE),
                                   discovery.read_chain(out / discovery.LEDGER))


def provider_fetch(root):
    papers = {p["doi"]: p for p in papers_at(root)}
    def fetch(url):
        prefix = "https://doi.org/"
        doi = unquote(url.split("/works/", 1)[1])
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
        paper = papers[doi]
        if "crossref.org" in url:
            return {"message": {
                "DOI": paper["doi"], "title": [paper["title"]],
                "published": {"date-parts": [[paper["year"], 1, 1]]},
                "type": "journal-article",
            }}, 0
        if "openalex.org" in url:
            return {"doi": prefix + doi, "title": paper["title"],
                    "publication_year": paper["year"]}, 0
        raise AssertionError("untrusted provider")
    return fetch


def persist(repo, report):
    (repo / "loto7_agent_output" / paper_guard.EVIDENCE).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def test_actual_repository_records_are_bounded_and_provenanced():
    report = agent.build(ROOT, fetch=provider_fetch(ROOT), now=NOW)
    assert report["version"] == paper_guard.VERSION
    assert report["auto_verifier_version"] == agent.VERSION
    assert report["rotation_total_candidates"] == len(papers_at(ROOT))
    assert len(report["rotation_attempted_dois"]) == 3
    assert sum(report["verification_status_counts"].values()) == len(papers_at(ROOT))
    assert report["latest_round"] == 699
    assert not report["automatic_adoption"]
    assert not report["production_changed"]
    assert not report["future_registry_changed"]
    assert report["full_text_reviewed_count"] == 0
    assert all(p["peer_review_confirmed"] is False and
               p["lottery_prediction_improved"] is False for p in report["verifications"])
    assert "not peer-review status" in agent.markdown(report)


def test_round_robin_covers_entire_bibliography_not_only_first_three(repo):
    ids = [p["doi"] for p in papers_at(repo)]
    visited = []
    for _ in range((len(ids) + 2) // 3):
        report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
        visited.extend(report["rotation_attempted_dois"])
        persist(repo, report)
    assert len(visited) == len(ids) or len(visited) == len(ids) + 1 or len(visited) == len(ids) + 2
    assert set(visited) == set(ids)
    assert all(p["status"] in {
        "two_provider_bibliography_matched", "previously_verified_not_refreshed"
    } for p in report["verifications"])


def test_two_sources_confirm_identity_but_not_scientific_methods(repo):
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    checked = set(report["rotation_attempted_dois"])
    assert checked
    for paper in report["verifications"]:
        if paper["doi"] in checked:
            assert paper["status"] == "two_provider_bibliography_matched"
            assert paper["crossref_consistent"] and paper["openalex_consistent"]
            assert paper["last_two_provider_matched_at_utc"]
        for key in agent.SAFETY_FLAGS:
            assert paper[key] is False


def test_prior_verified_is_stale_and_network_outage_does_not_forge_recency(repo):
    first = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    persist(repo, first)
    # Move over the entire DOI queue before its first DOI is retried.
    report = first
    for _ in range((report["rotation_total_candidates"] + 2) // 3):
        report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
        persist(repo, report)
    old_idx = first["rotation_start_index"]
    old_doi = papers_at(repo)[old_idx]["doi"]
    records = {p["doi"]: p for p in report["verifications"]}
    assert records[old_doi]["status"] in (
        "two_provider_bibliography_matched", "previously_verified_not_refreshed"
    )
    def unavailable(url):
        raise urllib.error.HTTPError(url, 503, "temporary", {}, None)
    outage = agent.build(repo, fetch=unavailable, now=NOW)
    assert any(p["status"] == "previously_verified_not_refreshed"
               for p in outage["verifications"])


def test_single_provider_and_conflicts_are_not_promoted(repo):
    def wrong(url):
        data, retries = provider_fetch(repo)(url)
        if "openalex.org" in url:
            data["title"] = "An unrelated record in a different discipline"
        return data, retries
    result = agent.build(repo, fetch=wrong, now=NOW)
    assert "conflict_do_not_use" in result["verification_status_counts"]
    assert result["two_provider_matches_this_cycle"] == 0


def test_sha_chain_tampering_rejected_and_no_source_writes(repo):
    data_file = repo / "loto7_agent_output" / discovery.LEDGER
    before = data_file.read_bytes()
    data_file.write_bytes(before.replace(b"literature_search", b"fake_literature", 1))
    with pytest.raises(ValueError):
        agent.build(repo, fetch=provider_fetch(repo), now=NOW)


def test_unreviewed_paper_claim_approval_refused(repo):
    path = repo / "loto7_agent_output" / paper_guard.EVIDENCE
    prev = json.loads(path.read_text())
    prev["verifications"][0]["peer_review_confirmed"] = True
    path.write_text(json.dumps(prev))
    with pytest.raises(ValueError, match="unapproved methodological claims"):
        agent.build(repo, fetch=provider_fetch(repo), now=NOW)


def test_bad_previous_verified_status_does_not_bypass_two_source(repo):
    path = repo / "loto7_agent_output" / paper_guard.EVIDENCE
    prev = json.loads(path.read_text())
    prev["verifications"][0]["status"] = "two_provider_bibliography_matched"
    prev["verifications"][0]["openalex_consistent"] = False
    path.write_text(json.dumps(prev))
    with pytest.raises(ValueError, match="forged two-provider"):
        agent.build(repo, fetch=provider_fetch(repo), now=NOW)


def test_rotation_cursor_bad_input_rejected(repo):
    path = repo / "loto7_agent_output" / paper_guard.EVIDENCE
    prev = json.loads(path.read_text())
    prev["rotation_next_index"] = 40_000
    path.write_text(json.dumps(prev))
    with pytest.raises(ValueError, match="cursor"):
        agent.build(repo, fetch=provider_fetch(repo), now=NOW)


def test_only_verified_discovery_state_matters_not_old_lottery_snapshot(repo):
    # No loto7.csv exists in the isolated fixture, intentionally. The DOI
    # reviewer may continue safely; it cannot grade lottery predictions.
    assert not (repo / "loto7.csv").exists()
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    assert report["latest_round"] == 699
    assert report["research_mode"] == "WAIT_FOR_NEW_DATA"
    assert report["automatic_adoption"] is False


def test_deterministic_with_fixed_timestamp_and_no_repo_mutation(repo):
    original = {p.relative_to(repo): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in repo.rglob("*") if p.is_file()}
    one = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    two = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    assert one == two
    assert agent.markdown(one) == agent.markdown(two)
    assert original == {p.relative_to(repo): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in repo.rglob("*") if p.is_file()}


def test_previous_discovery_sha_change_resets_untrusted_old_matches(repo):
    path = repo / "loto7_agent_output" / paper_guard.EVIDENCE
    prev = json.loads(path.read_text())
    prev["discovery_state_sha256"] = "0"*64
    path.write_text(json.dumps(prev))
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    assert report["rotation_start_index"] == 0
    assert report["verification_status_counts"]["not_yet_checked"] == (
        report["rotation_total_candidates"] - 3
    )


def test_existing_hourly_verifier_preserves_dedicated_rotation_cursor(repo, monkeypatch):
    # The hourly research pipeline may resume once its #700 science SHA
    # catches up. It must not silently reset the independent DOI rotation.
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    persist(repo, report)
    assert report["rotation_next_index"] == 3
    state = discovery.read_json(repo / "loto7_agent_output" / discovery.STATE)
    assert state["current_phase"] != "literature_search"
    monkeypatch.setattr(paper_guard.discovery, "inspect_evidence",
                        lambda _: {"research_mode": state["research_mode"],
                                   "latest_round": state["latest_resolved_round"]})
    def should_not_call_api(url):
        raise AssertionError("non-literature research phase should not query DOI API")
    output = paper_guard.run(repo, fetch=should_not_call_api)
    assert output["evidence"]["rotation_next_index"] == 3
    assert output["evidence"]["rotation_attempted_dois"] == []
    assert output["evidence"]["automatic_adoption"] is False


def test_priority_queue_checks_conflict_before_rotation_without_starving_others(repo):
    out = repo / "loto7_agent_output"
    path = out / paper_guard.EVIDENCE
    pub = json.loads(path.read_text(encoding="utf-8"))
    assert len(pub["verifications"]) >= 5
    pub["verifications"][0]["status"] = "conflict_do_not_use"
    pub["verifications"][1]["status"] = "not_yet_checked"
    path.write_text(json.dumps(pub), encoding="utf-8")
    plan = {
        "version": "research-priority-orchestrator-v1",
        "source_two_verified": True,
        "input_evidence_sha256": {"bibliography": agent.digest(path)},
        "authority": {"workflows_dispatched": False,
                      "production_or_champion_update": False},
        "tasks": [
            {"code": "REVIEW_BIBLIO_CONFLICTS", "lane": "bibliography",
             "safe_autonomous_action": "report_only",
             "forecast_or_production_change_authorized": False,
             "new_optimizer_trials_authorized": False},
            {"code": "VERIFY_UNCHECKED_DOIS", "lane": "bibliography",
             "safe_autonomous_action": "report_only",
             "forecast_or_production_change_authorized": False,
             "new_optimizer_trials_authorized": False},
        ]
    }
    (out / "research_autonomy_priority_queue.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    assert len(report["rotation_attempted_dois"]) == 3
    assert report["rotation_attempted_dois"][0] == pub["verifications"][0]["doi"]
    assert len(set(report["rotation_attempted_dois"])) == 3
    assert report["priority_dois_checked"] == [pub["verifications"][0]["doi"]]
    assert report["priority_queue_sha256"] == agent.digest(
        out / "research_autonomy_priority_queue.json"
    )
    assert report["rotation_next_index"] == 2
    assert report["priority_rotation_cursor"] == 1


def test_stale_priority_queue_does_not_override_independent_rotation(repo):
    out = repo / "loto7_agent_output"
    (out / "research_autonomy_priority_queue.json").write_text(
        json.dumps({
            "version": "research-priority-orchestrator-v1",
            "input_evidence_sha256": {"bibliography": "0"*64},
            "source_two_verified": True, "tasks": [],
            "authority": {"workflows_dispatched": False,
                          "production_or_champion_update": False}
        }), encoding="utf-8")
    report = agent.build(repo, fetch=provider_fetch(repo), now=NOW)
    assert report["priority_dois_checked"] == []
    assert report["rotation_attempted_dois"] == [
        p["doi"] for p in papers_at(repo)[:3]
    ]


def test_priority_queue_rejects_elevated_external_actions(repo):
    out = repo / "loto7_agent_output"
    evidence = out / paper_guard.EVIDENCE
    plan = {
        "version": "research-priority-orchestrator-v1",
        "source_two_verified": True,
        "input_evidence_sha256": {"bibliography": agent.digest(evidence)},
        "authority": {"workflows_dispatched": False,
                      "production_or_champion_update": False},
        "tasks": [{"code": "REVIEW_BIBLIO_CONFLICTS", "lane": "bibliography",
                   "safe_autonomous_action": "run_paper_code",
                   "forecast_or_production_change_authorized": True,
                   "new_optimizer_trials_authorized": True}],
    }
    (out / "research_autonomy_priority_queue.json").write_text(
        json.dumps(plan), encoding="utf-8")
    with pytest.raises(ValueError, match="elevate"):
        agent.build(repo, fetch=provider_fetch(repo), now=NOW)
