"""Strict-prefix round-2 retrospective replay and matched geometry-null tests."""
from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

import balanced_uniform_portfolio as geometry_null
import loto7_v2_runner as v2
from research import ranked35_walkforward_round2 as replay


def synthetic_draws(path: Path, count: int = 104, change_last: bool = False) -> None:
    begin = date(2013, 4, 5)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "抽せん日", "本数字", "ボーナス数字", "回別",
            *[f"{i}等当選金額" for i in range(1, 7)],
        ])
        for i in range(count):
            chosen = sorted((i * 13 + j * 5) % 37 + 1 for j in range(7))
            if change_last and i == count - 1:
                chosen = [1, 2, 3, 4, 5, 6, 7]
            bonus = [n for n in range(1, 38) if n not in chosen][:2]
            writer.writerow([
                (begin + timedelta(days=7*i)).isoformat(),
                " ".join(f"{n:02d}" for n in chosen),
                " ".join(f"{n:02d}" for n in bonus),
                f"第{i+1}回",
                "1000000円", "100000円", "10000円", "1000円", "100円", "50円",
            ])


def champion(path: Path) -> None:
    cfg = v2.DEFAULT_CHAMPION
    from dataclasses import asdict
    path.write_text(json.dumps({
        "model_version": cfg.version(), "config": asdict(cfg),
    }), encoding="utf-8")


def test_exact_disjoint_null_agrees_with_existing_analytical_geometry():
    actual = replay.exact_disjoint_score_null()
    expected = geometry_null.exact_disjoint_null()
    assert actual["universe_size"] == math.comb(37, 7)
    assert actual["score_mean"] == pytest.approx(expected["score"], abs=1e-10)
    assert actual["max_hits_mean"] == pytest.approx(expected["max_hits"], abs=1e-10)
    assert actual["ge3_probability"] == pytest.approx(expected["ge3"], abs=1e-10)
    assert actual["ge4_probability"] == pytest.approx(expected["ge4"], abs=1e-10)
    assert actual["any_first_prize_probability"] == 5 / math.comb(37, 7)
    assert actual["score_variance"] > 0


def test_replay_all_rounds_from_two_with_zero_lookahead_and_parity(tmp_path):
    csv_path = tmp_path / "history.csv"
    champion_path = tmp_path / "champion.json"
    synthetic_draws(csv_path)
    champion(champion_path)
    canonical = tmp_path / "production" / "predictions.csv"
    canonical.parent.mkdir()
    canonical.write_bytes(b"immutable ledger\n")
    output = tmp_path / "research"
    summary = replay.run(csv_path=csv_path, champion_file=champion_path,
                         out_dir=output, verify_parity=True, matched_reps=3)
    assert summary["target_round_first"] == 2
    assert summary["target_round_last"] == 104
    assert summary["results"]["all_rounds_2_plus"]["round_count"] == 103
    assert summary["results"]["uniform_cold_start_2_20"]["round_count"] == 19
    assert summary["results"]["untrained_expert_21_100"]["round_count"] == 80
    assert summary["results"]["approved_champion_101_plus"]["round_count"] == 4
    assert summary["champion_parity_target_rounds"] == [102, 103, 104]
    assert canonical.read_bytes() == b"immutable ledger\n"
    assert summary["research_only"] and not summary["issued_predictions_changed"]

    with (output / "rounds_2_to_latest.csv").open(encoding="utf-8-sig") as stream:
        rounds = list(csv.DictReader(stream))
    with (output / "tickets_2_to_latest.csv").open(encoding="utf-8-sig") as stream:
        tickets = list(csv.DictReader(stream))
    assert [int(r["round"]) for r in rounds] == list(range(2, 105))
    assert len(tickets) == 515
    for i in range(0, len(tickets), 5):
        group = tickets[i:i + 5]
        all_numbers = [int(n) for r in group for n in r["predicted_numbers"].split()]
        assert len(all_numbers) == 35
        assert len(set(all_numbers)) == 35
    first = rounds[0]
    assert first["phase"] == "uniform_cold_start"
    assert first["rank_1_to_7"] == "01 02 03 04 05 06 07"
    assert first["excluded_rank_36_37"] == "36 37"
    assert rounds[99]["round"] == "101"
    assert rounds[99]["phase"] == "approved_champion_online"
    assert len(first["source_prefix_sha256"]) == 64
    assert len(first["rank_sha256"]) == 64


def test_future_changes_never_affect_older_predictions_or_fingerprints(tmp_path):
    champion_path = tmp_path / "champion.json"
    champion(champion_path)
    p1, p2 = tmp_path / "104.csv", tmp_path / "105.csv"
    synthetic_draws(p1, count=104)
    synthetic_draws(p2, count=105, change_last=True)
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    replay.run(csv_path=p1, champion_file=champion_path,
               out_dir=out1, verify_parity=False, matched_reps=2)
    replay.run(csv_path=p2, champion_file=champion_path,
               out_dir=out2, verify_parity=False, matched_reps=2)
    with (out1 / "rounds_2_to_latest.csv").open(encoding="utf-8-sig") as f:
        old = list(csv.DictReader(f))
    with (out2 / "rounds_2_to_latest.csv").open(encoding="utf-8-sig") as f:
        new = list(csv.DictReader(f))
    assert old == new[:-1]
    assert len(new) == 104


def test_replay_rejects_missing_and_incorrect_champion_identity(tmp_path):
    csv_path = tmp_path / "history.csv"
    synthetic_draws(csv_path)
    invalid = tmp_path / "tampered.json"
    cfg = v2.DEFAULT_CHAMPION
    from dataclasses import asdict
    invalid.write_text(json.dumps({"model_version": "forged",
                                   "config": asdict(cfg)}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="approved Champion"):
        replay.run(csv_path=csv_path, champion_file=invalid,
                   out_dir=tmp_path / "result")
    assert not (tmp_path / "result").exists()
    with pytest.raises(RuntimeError, match="approved Champion"):
        replay.run(csv_path=csv_path, champion_file=tmp_path / "missing.json",
                   out_dir=tmp_path / "result")


def test_non_contiguous_history_is_rejected_instead_of_guessing_rounds(tmp_path):
    source = tmp_path / "source.csv"
    synthetic_draws(source)
    lines = source.read_text(encoding="utf-8").splitlines()
    source.write_text("\n".join([lines[0], *lines[2:]])+"\n", encoding="utf-8")
    champion_path = tmp_path / "champion.json"
    champion(champion_path)
    with pytest.raises(RuntimeError, match="contiguous"):
        replay.run(csv_path=source, champion_file=champion_path,
                   out_dir=tmp_path / "out")


def test_wrong_training_cutoff_never_masquerades_as_champion(tmp_path):
    source = tmp_path / "source.csv"
    synthetic_draws(source)
    champ = tmp_path / "champion.json"
    champion(champ)
    with pytest.raises(ValueError, match="min_train=100"):
        replay.run(csv_path=source, champion_file=champ,
                   out_dir=tmp_path / "out", min_train=25)
