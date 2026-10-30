"""Online collected scholarly data: bounded, SHA-anchored analytic tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import online_research_intelligence as intel

ROOT = Path(__file__).resolve().parents[1]


def test_real_collected_papers_are_reconciled_and_not_approved():
    r = intel.run(ROOT)
    snap = r["research_snapshot"]
    assert 1 <= snap["paper_count"] <= 36
    assert snap["topic_count"] == 6
    assert 1 <= snap["proposal_count"] <= 6
    assert r["quality_checks"]["audit_chain_verified"]
    assert r["quality_checks"]["metadata_lineage_verified"]
    assert sum(r["provider_status_distribution"].values()) == snap["paper_count"]
    assert len(r["topic_analytics"]) == 6
    assert all(t["bibliometric_scope"] == "nonrepresentative_capped_title_filtered_intake"
               and t["full_text_examined"] == 0 and not t["lottery_skill_established"]
               for t in r["topic_analytics"])


def test_stale_or_untrusted_latest_source_is_not_falsely_promoted():
    r = intel.run(ROOT)
    src, previous = r["source"], r["research_snapshot"]
    stale = (previous["draw_sha256"] != src["sha256"]
             or previous["last_resolved_round"] != src["round"])
    assert r["quality_checks"]["literature_synced_to_current_draw"] is not stale
    assert ("online_literature_analysis_uses_older_draw_snapshot" in r["blockers"]) == stale
    # The live research pipeline can catch up within round 700. Trust and
    # freshness must be evaluated from hashes, not a hardcoded round number.
    assert src["round"] >= 1
    assert ("latest_draw_requires_independent_source_corroboration" in
            r["blockers"]) is not src["independent_two_source_verified"]


def test_snapshot_freshness_transitions_do_not_depend_on_lottery_round(monkeypatch):
    baseline = intel.run(ROOT)
    original = baseline["source"]
    # Reproduce the stale evidence path even when a regularly scheduled job
    # has already updated the collected research journal.
    stale_source = dict(original, round=original["round"] + 1)
    monkeypatch.setattr(intel, "current_source", lambda _: stale_source)
    outdated = intel.run(ROOT)
    assert outdated["quality_checks"]["literature_synced_to_current_draw"] is False
    assert "online_literature_analysis_uses_older_draw_snapshot" in outdated["blockers"]
    for field in ("new_real_experiments", "new_predictions_generated"):
        assert outdated[field] == 0
    assert outdated["production_or_champion_changed"] is False
    # Restore the verified source and require a consistent fresh judgment.
    monkeypatch.setattr(intel, "current_source", lambda _: original)
    current = intel.run(ROOT)
    expected = (current["source"]["sha256"] ==
                current["research_snapshot"]["draw_sha256"] and
                current["source"]["round"] ==
                current["research_snapshot"]["last_resolved_round"])
    assert current["quality_checks"]["literature_synced_to_current_draw"] == expected


def test_real_analytical_controls_do_not_run_new_predictors():
    r = intel.run(ROOT)
    null = r["executed_fixed_analytical_controls"]
    assert null["uniform_seven_of_37_expected_top7_hits"] == pytest.approx(49/37)
    assert null["disjoint35_expected_composite"] > null["one_shared34_expected_composite"]
    assert null["first_prize_probability_five_distinct_tickets"] == pytest.approx(
        5 / 10_295_472
    )
    assert r["new_predictions_generated"] == r["new_real_experiments"] == 0
    assert not r["auto_promotion_authorized"]
    assert not r["production_or_champion_changed"]
    assert not r["future_oos_registry_modified"]
    assert not r["registered_protocols_changed"]
    assert not r["automatic_paper_method_execution"]


def test_theme_metrics_are_reconcilable_for_multitag_papers():
    r = intel.run(ROOT)
    for t in r["topic_analytics"]:
        assert t["papers_tagged"] == (
            t["currently_two_provider_matched"] +
            t["previously_matched_not_refreshed"] + t["pending_or_conflicting"]
        )
        assert sum(t["publication_year_counts"].values()) == t["papers_tagged"]
        assert t["distinct_dois"] == sorted(set(t["distinct_dois"]))


def test_practical_handoffs_are_fixed_not_untrusted_external_commands():
    r = intel.run(ROOT)
    a = r["practical_handoffs"]
    assert len(a) == r["research_snapshot"]["proposal_count"]
    assert len({v["action_id"] for v in a}) == len(a)
    for v in a:
        assert v["safe_operational_application"] == intel.SAFE_METHODS[v["topic"]][0]
        assert v["handoff_priority"] in {
            "verify_bibliographic_identity", "review_full_text_methods_and_license"
        }
        for field in ("method_from_external_paper_executed", "experiment_authorized",
                      "new_budget_granted", "future_oos_registered",
                      "production_promotion_allowed"):
            assert v[field] is False


def test_csv_export_is_safe_and_reproducible():
    result = intel.run(ROOT)
    content = intel.csv_export(result)
    assert content.count("\n") == 7
    assert "=HYPERLINK" not in content
    assert "https://" not in content
    assert content == intel.csv_export(result)
    assert intel.markdown(result) == intel.markdown(result)


def test_read_only_inputs_remain_bit_identical_and_run_is_repeatable():
    targets = [
        "loto7.csv", "loto7_agent_output/always_on_accuracy_research_journal.jsonl",
        "loto7_agent_output/always_on_accuracy_research_state.json",
        "loto7_agent_output/research_verified_publications.json",
        "loto7_agent_output/research_cycle_guard.json",
        "loto7_agent_output/research_experiment_proposals.json",
        "research/disjoint_future_oos/freeze_0701.json",
        "loto7_agent_output/model_champion.json",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in targets}
    assert intel.run(ROOT) == intel.run(ROOT)
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
               for p, h in hashes.items())


def test_real_research_inputs_have_provenance_chain():
    papers, reviewed, plans, pub, readiness, guard, statuses = intel.frozen_inputs(ROOT)
    assert len(papers) == len(statuses) == reviewed["count"]
    assert plans["count"] == len(plans["proposals"])
    assert pub["discovery_state_sha256"] == reviewed["discovery_state_sha256"]
    assert readiness["input_draw_sha256"] == plans["draw_history_sha256"]


@pytest.mark.parametrize("name,field,value", [
    ("research_literature_reviews.json", "triage", 999),
    ("research_experiment_proposals.json", "grant", True),
    ("research_verified_publications.json", "verify", False),
    ("research_application_readiness.json", "auto_production_release", True),
])
def test_modified_external_metadata_or_privileges_fail_closed(monkeypatch, name, field, value):
    original = intel.read
    def fake(path):
        obj = original(path)
        if path.name == name:
            obj = copy.deepcopy(obj)
            if field == "triage":
                obj["reviews"][0]["triage_score_not_accuracy"] = value
            elif field == "grant":
                obj["proposals"][0]["new_trial_budget_granted"] = value
            elif field == "verify":
                obj["verifications"][0]["status"] = "two_provider_bibliography_matched"
                obj["verifications"][0]["openalex_consistent"] = value
            else:
                obj[field] = value
        return obj
    monkeypatch.setattr(intel, "read", fake)
    with pytest.raises(ValueError):
        intel.run(ROOT)


def test_unknown_doi_from_bibliography_is_rejected(monkeypatch):
    original = intel.read
    def fake(path):
        obj = original(path)
        if path.name == "research_verified_publications.json":
            obj = copy.deepcopy(obj)
            obj["verifications"][0]["doi"] = "10.9999/forged"
        return obj
    monkeypatch.setattr(intel, "read", fake)
    with pytest.raises(ValueError, match="forged or unknown"):
        intel.run(ROOT)


def test_corrupt_audit_chain_is_rejected(tmp_path, monkeypatch):
    # Mutate the actual serialized journal, then use the real cryptographic
    # SHA-chain verifier. Forging its validated return value would bypass the
    # protected trust boundary and would not be a meaningful test.
    chain_file = ROOT / "loto7_agent_output/always_on_accuracy_research_journal.jsonl"
    corrupted = tmp_path / "mutated.jsonl"
    rows = chain_file.read_text().splitlines()
    first = json.loads(rows[0])
    first["record_sha256"] = "0" * 64
    rows[0] = json.dumps(first, separators=(",", ":"))
    corrupted.write_text("\n".join(rows) + "\n")
    actual_reader = intel.discovery.read_chain
    monkeypatch.setattr(intel.discovery, "read_chain",
                        lambda path: actual_reader(corrupted))
    with pytest.raises(ValueError, match="tampered"):
        intel.run(ROOT)


def test_claimed_source_verification_cannot_override_independent_guard(monkeypatch):
    monkeypatch.setattr(intel.operations.trust, "validate_trusted_source",
                        lambda *_: {"trusted": False, "round": None})
    src = intel.read(ROOT / "loto7_agent_output/source_validation.json")
    if src["verification"] == "verified_two_result_sources":
        with pytest.raises(ValueError, match="fails trust guard"):
            intel.current_source(ROOT)
    else:
        assert not intel.current_source(ROOT)["independent_two_source_verified"]
