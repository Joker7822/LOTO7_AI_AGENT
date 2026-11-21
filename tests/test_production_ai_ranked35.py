"""Regression tests: Champion-ranked 35-number Production, effective 705+."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import audit_ledger as ledger
import loto7_v2_runner as v2
import production_disjoint35_policy as policy
import production_ticket_geometry35 as geometry
import weekly_production_prediction as weekly
from loto7_evolving_agent import fingerprint_file


def descending_score_ranking():
    # Number 37 has highest score, 1 is lowest.
    return np.arange(1, 38, dtype=float) / sum(range(1, 38))


def test_ranked_top35_exactly_five_nonoverlapping_tickets():
    tickets, ranking = geometry.ranked_portfolio_from_scores(descending_score_ranking())
    assert ranking == list(range(37, 0, -1))
    assert tickets == [
        tuple(range(31, 38)),
        tuple(range(24, 31)),
        tuple(range(17, 24)),
        tuple(range(10, 17)),
        tuple(range(3, 10)),
    ]
    assert {number for ticket in tickets for number in ticket} == set(range(3, 38))
    assert all(len(ticket) == 7 for ticket in tickets)


def test_equal_scores_use_stable_numeric_tiebreaker():
    tickets, ranking = geometry.ranked_portfolio_from_scores(np.full(37, 1 / 37))
    assert ranking == list(range(1, 38))
    assert {n for ticket in tickets for n in ticket} == set(range(1, 36))


@pytest.mark.parametrize("bad", [
    np.ones(36) / 36, np.full(37, float("nan")),
    np.full(37, float("inf")), np.ones(37),
    np.array([-1.0] + [2 / 36] * 36),
])
def test_bad_scores_never_fallback_to_random(bad):
    with pytest.raises(ValueError, match="Champion ranking"):
        geometry.ranked_portfolio_from_scores(bad)


def test_new_publication_policy_keeps_old_issued_versions_valid():
    assert policy.publication_policy_for_target(702) == policy.VERSION
    assert policy.publication_policy_for_target(704) == policy.VERSION
    assert policy.publication_policy_for_target(705) == policy.RANKED_VERSION
    with pytest.raises(ValueError):
        policy.publication_policy_for_target(701)

    legacy = [
        {"ticket": i, "model_version": "baseline+" + policy.VERSION,
         "predicted_numbers": " ".join(f"{n:02d}" for n in range((i-1)*7+1, i*7+1))}
        for i in range(1, 6)
    ]
    # Frozen old-style 705 prediction remains valid after deploying the new code.
    policy.validate_issued_rows(legacy, 705)
    assert policy.issued_policy(legacy, 705) == policy.VERSION
    ranked = [
        {**r, "model_version": "baseline+" + policy.RANKED_VERSION}
        for r in legacy
    ]
    policy.validate_issued_rows(ranked, 705)
    with pytest.raises(ValueError, match="ineligible"):
        policy.validate_issued_rows(ranked, 704)
    ranked[0]["model_version"] = "baseline+" + policy.VERSION
    with pytest.raises(ValueError, match="mixed"):
        policy.validate_issued_rows(ranked, 705)


def prepared_ranked_output(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("synthetic-history-only", encoding="utf-8")
    out_dir = tmp_path / "out"
    cfg = v2.DEFAULT_CHAMPION
    monkeypatch.setattr(geometry, "production_window_guard", lambda *_: None)
    monkeypatch.setattr(geometry, "verify_source", lambda *_: {"trusted": True, "round": 704})

    invoked = []
    def fake_walk(history, *, min_train, eta, decay, expert_uniform_mix):
        invoked.append((len(history), min_train, eta, decay, expert_uniform_mix))
        return SimpleNamespace(keys=["test-expert"], final_weights=np.array([1.0]))
    monkeypatch.setattr(geometry, "walk_forward_evolve", fake_walk)
    monkeypatch.setattr(geometry, "final_score",
                        lambda history, bt, *, uniform_mix: descending_score_ranking())
    state = geometry.prepare_new_production_outputs(
        csv_path=csv_path, out_dir=out_dir,
        champion_version=cfg.version(),
        data_sha=fingerprint_file(csv_path),
        latest_round=704, target_round=705,
        latest_draw_date="2026-11-20", git_sha="test",
        source_path=out_dir / "source_validation.json",
        history=np.zeros((704, 37)), champion_config=cfg,
    )
    assert invoked == [(704, 100, cfg.eta, cfg.decay, cfg.expert_uniform_mix)]
    return csv_path, out_dir, state


def test_ranked_publication_writes_full_provenance_and_csv(tmp_path, monkeypatch):
    csv_path, out_dir, state = prepared_ranked_output(tmp_path, monkeypatch)
    assert state["production_ticket_policy_version"] == policy.RANKED_VERSION
    assert state["signal_champion_version"] == v2.DEFAULT_CHAMPION.version()
    assert state["production_rank_order"] == list(range(37, 0, -1))
    assert state["production_rank_top35"] == list(range(37, 2, -1))
    assert state["production_rank_excluded_numbers"] == [2, 1]
    assert len(state["production_rank_sha256"]) == 64
    assert state["production_rank_base_data_sha256"] == fingerprint_file(csv_path)
    assert state["first_prize_odds_unchanged"] is True
    rows = ledger.read_csv(out_dir / "candidate_tickets.csv")
    assert len(rows) == 5
    assert [tuple(map(int, row["numbers"].split())) for row in rows] == [
        tuple(range(start, start+7)) for start in (31, 24, 17, 10, 3)
    ]
    ranks = ledger.read_csv(out_dir / "prediction_ranking.csv")
    assert len(ranks) == 37
    assert [int(row["number"]) for row in ranks] == list(range(37, 0, -1))


def test_ranked_append_rejects_ticket_replacement_and_bad_rank(tmp_path, monkeypatch):
    csv_path, out_dir, state = prepared_ranked_output(tmp_path, monkeypatch)
    base_history = [{"回別": "第704回", "抽せん日": "2026-11-20"}]
    tickets = ledger.read_csv(out_dir / "candidate_tickets.csv")
    preds = out_dir / "predictions.csv"
    altered = [dict(row) for row in tickets]
    altered[0]["numbers"] = altered[1]["numbers"]
    with pytest.raises(RuntimeError, match="ranking"):
        ledger.append_current_predictions(base_history, altered, preds, state,
                                          current_data_sha=fingerprint_file(csv_path))
    assert not preds.exists()

    tampered_state = {**state, "production_rank_order": list(range(1, 38))}
    with pytest.raises(RuntimeError, match="ranking"):
        ledger.append_current_predictions(base_history, tickets, preds, tampered_state,
                                          current_data_sha=fingerprint_file(csv_path))
    assert not preds.exists()

    count = ledger.append_current_predictions(base_history, tickets, preds, state,
                                              current_data_sha=fingerprint_file(csv_path))
    assert count == 5
    assert all(row["model_version"].endswith("+" + policy.RANKED_VERSION)
               for row in ledger.read_csv(preds))
    published = {
        "published": True, "target_round": "第705回",
        "ticket_policy": policy.RANKED_VERSION,
        "model_version": state["model_version"],
    }
    (out_dir / "weekly_production_prediction_state.json").write_text(
        json.dumps(published), encoding="utf-8"
    )
    assert geometry.verify_canonical_publication(out_dir)["status"] == "disjoint35_pass"
    assert ledger.append_current_predictions(base_history, tickets, preds, state,
                                             current_data_sha=fingerprint_file(csv_path)) == 0


def test_ranked_preparation_never_falls_back_if_champion_missing(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("immutable", encoding="utf-8")
    monkeypatch.setattr(geometry, "production_window_guard", lambda *_: None)
    monkeypatch.setattr(geometry, "verify_source", lambda *_: {"trusted": True})
    with pytest.raises(RuntimeError, match="approved Champion"):
        geometry.prepare_new_production_outputs(
            csv_path=csv_path, out_dir=tmp_path / "out",
            champion_version=v2.DEFAULT_CHAMPION.version(),
            data_sha=fingerprint_file(csv_path), latest_round=704, target_round=705,
            latest_draw_date="2026-11-20", git_sha="test",
            source_path=tmp_path / "source.json",
        )
    assert not (tmp_path / "out").exists()


def test_weekly_ranked_requires_valid_champion_file(tmp_path):
    # A synthetic single row is enough to reach the ranked Champion gate.
    csv_path = tmp_path / "loto7.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["回別", "抽せん日", "本数字"])
        writer.writerow(["第704回", "2026-11-20", "01 02 03 04 05 06 07"])
    with pytest.raises(RuntimeError, match="approved Champion file"):
        weekly.publish(csv_path=csv_path, out_dir=tmp_path / "out",
                       champion_file=tmp_path / "missing.json",
                       research_state=tmp_path / "missing2.json")
