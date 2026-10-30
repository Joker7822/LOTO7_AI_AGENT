"""Protect the separately issued round-701 disjoint proposal and original ledger."""
import json
from pathlib import Path

import pytest

import audit_ledger as ledger
import balanced_uniform_portfolio as balanced
import production_ticket_geometry35 as geometry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research" / "round701_disjoint35_supplement.json"


def snapshot():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_exact_35_different_numbers_match_seeded_702_geometry_algorithm():
    doc = snapshot()
    assert doc["version"] == "round701-user-requested-disjoint35-supplement-v1"
    assert doc["kind"] == "separate_user_requested_noncanonical_ticket_alternative"
    assert doc["target_round"] == 701
    assert doc["source_latest_completed_round"] == 700
    assert doc["target_draw_date"] == "2026-10-30"
    assert doc["seed"] == geometry.SEED_BASE + 701 * geometry.SEED_MULTIPLIER
    tickets = [tuple(t["numbers"]) for t in doc["five_tickets"]]
    assert [t["ticket"] for t in doc["five_tickets"]] == [1, 2, 3, 4, 5]
    assert tickets == balanced.disjoint_portfolio(doc["seed"])
    balanced.validate_portfolio(tickets)
    assert len({n for ticket in tickets for n in ticket}) == 35
    assert doc["covered_distinct_numbers"] == 35
    assert doc["omitted_numbers"] == sorted(set(range(1, 38)) -
                                            {n for ticket in tickets for n in ticket})


def test_original_canonical_701_prediction_ledger_is_separate_and_preserved():
    doc = snapshot()
    all_rows = ledger.read_csv(ROOT / "loto7_agent_output" / "predictions.csv")
    old = [r for r in all_rows if ledger.rno(r.get("target_round", "")) == 701]
    assert len(old) == 5
    old.sort(key=lambda r: int(r["ticket"]))
    assert [int(r["ticket"]) for r in old] == [1, 2, 3, 4, 5]
    assert {r["model_version"] for r in old} == {doc["canonical_production_model_version"]}
    assert {r["prediction_created_at_jst"] for r in old} == {
        doc["canonical_production_issued_at_jst"]}
    assert {r["data_sha256"] for r in old} == {doc["source_draw_history_sha256"]}
    original = [tuple(int(x) for x in r["predicted_numbers"].split()) for r in old]
    proposed = [tuple(t["numbers"]) for t in doc["five_tickets"]]
    assert original != proposed
    assert len({n for ticket in original for n in ticket}) < 35
    assert doc["canonical_prediction_ledger_preserved"] is True
    assert geometry.MIN_TARGET_ROUND == 702
    with pytest.raises(ValueError):
        geometry.portfolio_for_target(701)


def test_supplement_does_not_claim_official_issue_or_future_oos():
    doc = snapshot()
    policy = doc["registration"]
    assert policy["scope"] == "supplement_only_not_registered_future_oos"
    assert policy["official_production_issuance"] is False
    assert policy["immutable_production_predictions_modified"] is False
    assert policy["prospective_skill_established"] is False
    assert policy["first_prize_probability_improved"] is False
    assert policy["automatic_champion_promotion"] is False
    assert "model_champion" not in str(REPORT)
    assert "prediction" not in REPORT.name
