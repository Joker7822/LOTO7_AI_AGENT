"""Safe online research validation, fair-null methods and bounded recovery."""
import json
import shutil
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

import always_on_accuracy_agent as discovery
import research_evidence_resilience as system

NOW = datetime(2026, 10, 22, 9, 0, tzinfo=timezone(timedelta(hours=9)))
PAPER = {
    "doi": "10.1234/forecast.2026",
    "title": "Sequential probabilistic forecast calibration",
    "year": 2026,
    "url": "https://doi.org/10.1234/forecast.2026",
    "review_status": "unreviewed",
}


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "isolated"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    shutil.copyfile("loto7.csv", root / "loto7.csv")
    for f in discovery.FILES.values():
        shutil.copyfile(Path("loto7_agent_output") / f, out / f)
    discovery.run(root, now=NOW, fetcher=lambda topic, date: [PAPER])
    return root


def good_fetch(url):
    if url.startswith("https://api.crossref.org/"):
        return {"message": {
            "DOI": PAPER["doi"], "title": [PAPER["title"]],
            "published": {"date-parts": [[2026, 10, 1]]},
            "type": "journal-article",
            "abstract": "<jats:p>Sequential probabilistic forecasting calibration provides "
                        "online forecasts evaluated before observing realized "
                        "outcomes and helps avoid selection mistakes in training. "
                        "Its assumptions should be checked independently, including data leakage, "
                        "future-only evaluation, multiple comparisons, proper scoring rules, "
                        "conditional fairness, sequential testing and model selection bias "
                        "under repeated research attempts.</jats:p>",
        }}, 0
    if url.startswith("https://api.openalex.org/"):
        return {
            "doi": PAPER["url"], "title": PAPER["title"],
            "publication_year": 2026,
            "abstract_inverted_index": {"sequential": [0], "calibration": [1],
                                        "proper": [2], "scoring": [3]},
        }, 0
    raise AssertionError("unapproved host queried")


def fake_network_http(code):
    def reject(url):
        raise urllib.error.HTTPError(url, code, "unavailable", {}, None)
    return reject


def test_crossref_openalex_bibliography_and_real_methods_sandbox(repo):
    before = {p.relative_to(repo):p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    result = system.run(repo, fetch=good_fetch)
    assert result["evidence"]["two_provider_matches_this_cycle"] == 1
    assert result["evidence"]["verifications"][0]["status"] == "two_provider_bibliography_matched"
    assert result["evidence"]["verifications"][0]["abstract_metadata_present"]
    assert result["evidence"]["verifications"][0]["peer_review_confirmed"] is False
    assert result["evidence"]["verifications"][0]["full_text_reviewed"] is False
    assert result["sandbox"]["future_oos_draws_consumed"] == 0
    assert result["sandbox"]["real_model_experiments_executed"] == 0
    assert result["sandbox"]["biased_sum_inclusion_p"] == pytest.approx(7)
    assert result["sandbox"]["no_claim_about_actual_lottery_predictability"] is True
    assert result["recovery"]["requires_human_review_for_code_or_protocol_bugs"]
    for path,data in before.items():
        assert (repo / path).read_bytes() == data


def test_mismatched_doi_and_title_fail_closed(repo):
    def wrong(url):
        doc, n = good_fetch(url)
        if "crossref" in url:
            doc["message"]["DOI"] = "10.1234/other"
        else:
            doc["title"] = "Incompatible unrelated paper"
        return doc, n
    result = system.run(repo, fetch=wrong)
    assert result["evidence"]["verifications"][0]["status"] == "conflict_do_not_use"
    assert result["evidence"]["two_provider_matches_this_cycle"] == 0


def test_one_provider_does_not_count_as_independent_verification(repo):
    def one(url):
        if "openalex" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return good_fetch(url)
    result = system.run(repo, fetch=one)
    assert result["evidence"]["verifications"][0]["status"] == "single_provider_only"
    assert result["evidence"]["two_provider_matches_this_cycle"] == 0


def test_auto_repair_previously_verified_record_preserved_but_stale(repo):
    first = system.run(repo, fetch=good_fetch)
    assert first["evidence"]["two_provider_matches_this_cycle"] == 1
    second = system.run(repo, fetch=fake_network_http(503))
    p = second["evidence"]["verifications"][0]
    assert p["status"] == "previously_verified_not_refreshed"
    assert second["evidence"]["two_provider_matches_this_cycle"] == 0
    assert second["recovery"]["previously_verified_records_preserved_without_fresh_claim"] == 1
    assert second["recovery"]["provider_errors_or_conflicts"] == 2
    assert second["recovery"]["actions_prohibited"]


def test_bad_derived_report_can_be_reconstructed_from_unmodified_sources(repo):
    system.run(repo, fetch=good_fetch)
    out=repo/"loto7_agent_output"
    (out/system.EVIDENCE).write_text("corrupt, local derived JSON")
    result=system.run(repo, fetch=good_fetch)
    assert result["evidence"]["verifications"][0]["status"] == "two_provider_bibliography_matched"
    assert json.loads((out/system.EVIDENCE).read_text())["version"] == system.VERSION


def test_corrupted_sha_chain_never_self_healed(repo):
    path=repo/"loto7_agent_output"/discovery.LEDGER
    path.write_text(path.read_text().replace("literature_search","recovered_success"))
    with pytest.raises(ValueError, match="tampered"):
        system.run(repo, fetch=good_fetch)
    assert not (repo/"loto7_agent_output"/system.REPAIRS).exists()


def test_guard_modified_never_repaired_as_healthy(repo):
    path=repo/"loto7_agent_output"/discovery.FILES["budget"]
    x=json.loads(path.read_text())
    x["data_sha256"]="unexpected"
    path.write_text(json.dumps(x))
    with pytest.raises(ValueError, match="different draw-history SHA"):
        system.run(repo, fetch=good_fetch)


def test_only_allowlisted_hosts_and_transient_failures_are_retried():
    with pytest.raises(ValueError, match="unapproved"):
        system.public_get_json("http://api.crossref.org/works/10.1234/abc")
    with pytest.raises(ValueError, match="unapproved"):
        system.public_get_json("https://evil.example/works/10.1234/abc")
    with pytest.raises(ValueError, match="retry budget"):
        system.public_get_json("https://api.crossref.org/works/10.1234/abc", tries=100)

    attempts=[]
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self,_size): return b'{"message":{"type":"journal-article"}}'
    def server(request, timeout):
        attempts.append(request.full_url)
        assert timeout == 8
        if len(attempts)<3:
            raise urllib.error.HTTPError(request.full_url,503,"Unavailable",{},None)
        return Reply()
    result, retries=system.public_get_json(
        "https://api.crossref.org/works/10.1234/example", opener=server,sleep=lambda _: None)
    assert retries==2
    assert result["message"]["type"] == "journal-article"
    assert len(attempts)==3

    rejected=[]
    def access_denied(req,timeout):
        rejected.append(1)
        raise urllib.error.HTTPError(req.full_url,403,"Forbidden",{},None)
    with pytest.raises(urllib.error.HTTPError):
        system.public_get_json("https://api.openalex.org/works/10.1234/ex",opener=access_denied,
                               sleep=lambda _: None)
    assert len(rejected)==1


def test_fair_null_sanity_is_fixed_budget_reproducible_and_non_predictive():
    x=system.fair_sandbox(worlds=128,draws=24)
    y=system.fair_sandbox(worlds=128,draws=24)
    assert x==y
    assert x["biased_minus_uniform_mean_log_score"] < 0
    assert x["null_max_e_threshold_rate"] < 0.1
    assert 0.95 < x["observed_null_mean_e_factor"] < 1.05
    assert x["auto_promotion_allowed"] is False
    with pytest.raises(ValueError, match="computation cap"):
        system.fair_sandbox(worlds=10_000)


def test_absent_abstract_does_not_masquerade_as_full_text(repo):
    def no_abstract(url):
        v,n=good_fetch(url)
        if "crossref" in url: v["message"].pop("abstract")
        else: v.pop("abstract_inverted_index")
        return v,n
    data=system.run(repo, fetch=no_abstract)["evidence"]["verifications"][0]
    assert data["status"]=="two_provider_bibliography_matched"
    assert data["abstract_metadata_present"] is False
    assert data["full_text_reviewed"] is False


def test_off_literature_phase_makes_no_outbound_requests(repo):
    system.run(repo,fetch=good_fetch)
    discovery.run(repo,now=NOW+timedelta(hours=1),
                  fetcher=lambda *_: (_ for _ in ()).throw(RuntimeError("not due")))
    count=[0]
    def should_not_fetch(_):
        count[0]+=1
        raise AssertionError("not scheduled")
    state=system.run(repo,fetch=should_not_fetch)
    assert count[0]==0
    assert state["evidence"]["verifications"][0]["status"]=="previously_verified_not_refreshed"
