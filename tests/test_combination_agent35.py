"""Tests of the independent 35-number pairing agent and its replay controls."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

import balanced_uniform_portfolio as fair
import loto7_v2_runner as v2
from loto7_evolving_agent import fingerprint_file
from research import combination_agent35 as agent


def example_history(size: int = 125, change_last: bool = False) -> np.ndarray:
    x = np.zeros((size, 37), dtype=np.int8)
    for t in range(size):
        labels = [(t * 13 + j * 5) % 37 for j in range(7)]
        assert len(set(labels)) == 7
        if t == size-1 and change_last:
            labels = list(range(7))
        x[t, labels] = 1
    return x


def example_csv(path: Path, n: int = 104, change_last: bool = False) -> None:
    x = example_history(n, change_last=change_last)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["抽せん日", "本数字", "ボーナス数字", "回別",
                         "4等当選金額", "5等当選金額", "6等当選金額"])
        for t, row in enumerate(x):
            winners = (np.flatnonzero(row)+1).tolist()
            bonus = [v for v in range(1, 38) if v not in winners][:2]
            writer.writerow([
                (date(2013,4,5)+timedelta(days=7*t)).isoformat(),
                " ".join(str(n) for n in winners),
                " ".join(str(n) for n in bonus),
                f"第{t+1}回",
                "10000円", "1700円", "900円",
            ])


def champion_file(path: Path) -> None:
    cfg = v2.DEFAULT_CHAMPION
    path.write_text(json.dumps({
        "model_version": cfg.version(), "config": asdict(cfg),
    }), encoding="utf-8")


def test_pair_posterior_is_symmetric_shrunk_and_fair_centered():
    x = example_history()
    cfg = agent.AgentConfig()
    edge, info = agent.fit_pairwise_edges(x[:120], cfg)
    assert edge.shape == (37,37)
    assert np.all(np.isfinite(edge))
    assert np.allclose(edge, edge.T)
    assert np.allclose(np.diag(edge), 0)
    assert info["lookback_used"] == 120
    assert 0 < info["effective_sample_size"] <= 120
    assert 0 < info["posterior_data_weight"] < 0.5
    assert info["fair_draw_pair_probability"] == pytest.approx(42 / (37*36))
    with pytest.raises(ValueError, match="at least 100"):
        agent.fit_pairwise_edges(x[:99], cfg)
    with pytest.raises(ValueError, match="valid past draws"):
        agent.fit_pairwise_edges(np.zeros((120,37), dtype=int), cfg)


def test_optimizer_can_group_historically_affiliated_pairs_without_changing_top35():
    ranking = list(range(1,38))
    edge = np.zeros((37,37), dtype=float)
    edge[0,7] = edge[7,0] = 1.0
    tickets, info = agent.optimize_partition(
        ranking, edge, agent.AgentConfig(max_swaps=5)
    )
    assert info["swap_count"] >= 1
    assert info["training_objective_gain"] > 0
    assert any(1 in ticket and 8 in ticket for ticket in tickets)
    assert [len(t) for t in tickets] == [7]*5
    assert sorted(v for ticket in tickets for v in ticket) == list(range(1,36))
    assert all(tuple(sorted(t)) == t for t in tickets)
    assert 36 not in (v for ticket in tickets for v in ticket)
    assert 37 not in (v for ticket in tickets for v in ticket)


def test_uniform_or_zero_posterior_does_not_make_random_unnecessary_swaps():
    ranking = list(range(1,38))
    tickets, info = agent.optimize_partition(
        ranking, np.zeros((37,37)), agent.AgentConfig()
    )
    assert info["swap_count"] == 0
    assert tickets == [tuple(range(i,i+7)) for i in (1,8,15,22,29)]
    assert info["training_objective_gain"] == 0


def test_ranking_integrity_and_matrix_validation():
    with pytest.raises(ValueError, match="every number"):
        agent.optimize_partition([1]*37, np.zeros((37,37)), agent.AgentConfig())
    with pytest.raises(ValueError, match="37 integer"):
        agent.optimize_partition(list(range(1,37)), np.zeros((37,37)), agent.AgentConfig())
    bad = np.zeros((37,37))
    bad[0,1] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        agent.optimize_partition(list(range(1,38)), bad, agent.AgentConfig())
    bad = np.zeros((37,37))
    bad[0,1] = 1
    with pytest.raises(ValueError, match="symmetric"):
        agent.optimize_partition(list(range(1,38)), bad, agent.AgentConfig())


def test_replay_performs_strict_prefix_pairing_and_fails_closed_on_source(tmp_path):
    csv_path = tmp_path / "draws.csv"
    champ = tmp_path / "champion.json"
    example_csv(csv_path)
    champion_file(champ)
    protected = tmp_path / "loto7_agent_output" / "predictions.csv"
    protected.parent.mkdir()
    protected.write_bytes(b"immutable ticket ledger\n")
    source = tmp_path / "source.json"
    obj = {
        "status": "ok", "verification": "verified_two_result_sources",
        "latest": {
            "round": 104,
            "date": (date(2013,4,5)+timedelta(days=7*103)).isoformat(),
        },
        "verification_provenance": {"draw_csv_sha256": fingerprint_file(csv_path)},
    }
    source.write_text(json.dumps(obj), encoding="utf-8")
    out = tmp_path / "research"
    result = agent.run(csv_path=csv_path, champion_file=champ,
                       source_report=source, out_dir=out)
    assert result["evaluated_rounds"] == 4
    assert result["first_evaluated_round"] == 101
    assert result["last_evaluated_round"] == 104
    assert result["source_trust"] == "verified_two_result_sources"
    assert result["champion_version"] == v2.DEFAULT_CHAMPION.version()
    assert result["production_ledger_modified"] is False
    assert result["prospective_registry_modified"] is False
    assert result["promotion_authorized"] is False
    assert protected.read_bytes() == b"immutable ticket ledger\n"

    with (out / "paired_rounds_101_to_latest.csv").open(encoding="utf-8-sig") as f:
        rounds = list(csv.DictReader(f))
    with (out / "paired_tickets_101_to_latest.csv").open(encoding="utf-8-sig") as f:
        tickets = list(csv.DictReader(f))
    assert [int(r["round"]) for r in rounds] == [101,102,103,104]
    assert len(tickets) == 40
    for row in rounds:
        baseline = [set(map(int, ticket.split())) for ticket in row["baseline_tickets"].split("|")]
        candidate = [set(map(int, ticket.split())) for ticket in row["agent_tickets"].split("|")]
        b = [v for ticket in baseline for v in ticket]
        c = [v for ticket in candidate for v in ticket]
        assert len(b) == len(set(b)) == 35
        assert len(c) == len(set(c)) == 35
        assert sorted(c) == sorted(b)
        assert sorted(c) == sorted(map(int,row["rank_top35"].split()))
        assert not (set(c) & set(map(int,row["excluded_two"].split())))
        assert float(row["agent_objective_gain"]) >= -1e-9
    assert result["research_next_round_preview"]["target_round"] == 105
    assert len(result["research_next_round_preview"]["agent_tickets"]) == 5
    assert result["exact_fair_disjoint_null"]["score"] == pytest.approx(
        fair.exact_disjoint_null()["score"]
    )
    wrong = {**obj, "verification_provenance": {"draw_csv_sha256": "wrong"}}
    source.write_text(json.dumps(wrong), encoding="utf-8")
    with pytest.raises(RuntimeError, match="mismatch"):
        agent.run(csv_path=csv_path, champion_file=champ,
                  source_report=source, out_dir=tmp_path / "should_not_exist")


def test_extending_or_modifying_future_draw_does_not_change_prior_combo_predictions(tmp_path):
    champ = tmp_path / "champion.json"
    champion_file(champ)
    p1,p2 = tmp_path / "104.csv",tmp_path / "105.csv"
    example_csv(p1, 104)
    example_csv(p2, 105, change_last=True)
    a,b = tmp_path / "out104",tmp_path / "out105"
    agent.run(csv_path=p1, champion_file=champ, out_dir=a)
    agent.run(csv_path=p2, champion_file=champ, out_dir=b)
    def read(path):
        with path.open(encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    rows1=read(a/"paired_rounds_101_to_latest.csv")
    rows2=read(b/"paired_rounds_101_to_latest.csv")
    assert rows1==rows2[:-1]
    tickets1=read(a/"paired_tickets_101_to_latest.csv")
    tickets2=read(b/"paired_tickets_101_to_latest.csv")
    assert tickets1==tickets2[:-10]


def test_no_future_signal_even_when_pair_optimizer_is_called_repeatedly():
    x = example_history(140)
    ranking = list(range(1,38))
    cfg = agent.AgentConfig()
    t1,m1 = agent.candidate_from_history(x[:130], ranking, cfg)
    x[139] = 0
    x[139, :7] = 1
    t2,m2 = agent.candidate_from_history(x[:130], ranking, cfg)
    assert t1 == t2
    assert m1 == m2


def test_fair_lottery_null_invariant_under_any_partition():
    exact = fair.exact_disjoint_null()
    assert exact["any_first_prize_probability"] == pytest.approx(
        5 / math.comb(37,7)
    )
    assert exact["covered_distinct_numbers"] == 35
