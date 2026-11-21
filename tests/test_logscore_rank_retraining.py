"""New rank-learning candidate: replay, prequential integrity and fail-closed tests."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

import loto7_v2_runner as v2
from research import logscore_rank_retraining as rank


def sample_history(path: Path, n: int = 104, perturb_last: bool = False):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["抽せん日", "本数字", "ボーナス数字", "回別"])
        for idx in range(n):
            nums = sorted({(idx * 7 + j * 11) % 37 + 1 for j in range(7)})
            assert len(nums) == 7
            if perturb_last and idx == n - 1:
                nums = [1, 2, 3, 4, 5, 6, 7]
            bonus = [i for i in range(1, 38) if i not in nums][:2]
            writer.writerow([
                (date(2013, 4, 5) + timedelta(days=7 * idx)).isoformat(),
                " ".join(map(str, nums)), " ".join(map(str, bonus)), f"第{idx+1}回",
            ])


def make_champion(path: Path):
    cfg = v2.DEFAULT_CHAMPION
    path.write_text(json.dumps({"model_version": cfg.version(),
                                "config": asdict(cfg)}), encoding="utf-8")


def test_log_score_expert_weighting_and_candidate_normalization():
    rng = np.random.default_rng(5)
    ex = {f"e{i}": rng.dirichlet(np.ones(37)) for i in range(4)}
    old = np.ones(37) / 37
    keys = list(ex)
    q = rank._candidate_score(ex, keys, np.zeros(4), old)
    assert q.shape == (37,)
    assert q.sum() == pytest.approx(1.0, abs=1e-12)
    assert np.all(q > 0)
    assert not np.allclose(q, old)
    update = rank._update_log_score_weights(ex, keys, np.zeros(4),
                                            np.array([0, 5, 10, 15, 20, 25, 30]))
    assert update.shape == (4,) and np.all(np.isfinite(update))
    with pytest.raises(RuntimeError, match="expert registry"):
        rank._candidate_score(ex, ["missing"], np.ones(1), old)


def test_strict_chronological_retraining_keeps_production_immutable(tmp_path):
    csv_path = tmp_path / "sample.csv"
    champ = tmp_path / "champion.json"
    sample_history(csv_path)
    make_champion(champ)
    protected = tmp_path / "loto7_agent_output" / "predictions.csv"
    protected.parent.mkdir()
    protected.write_bytes(b"frozen production history\n")
    out = tmp_path / "research"
    res = rank.run(csv_path=csv_path, champion_path=champ, out_dir=out)
    assert res["evaluated_rounds"] == 4
    assert res["evaluated_tickets_per_model"] == 20
    assert res["rank_705_research_preview"]["target_round"] == 105
    assert res["model_automatically_adopted"] is False
    assert res["prospective_candidate_registered"] is False
    assert res["production_changed"] is False
    assert protected.read_bytes() == b"frozen production history\n"
    assert res["champion_version"] == v2.DEFAULT_CHAMPION.version()
    assert res["source_verification"] == "not_requested_local_test"
    assert "candidate_log_better_than_fair_uniform" in res["checks"]
    assert "candidate_brier_better_than_fair_uniform" in res["checks"]
    assert res["periods"]["all_101_latest"]["uniform_log"] == pytest.approx(
        -np.log(37)
    )
    assert res["periods"]["all_101_latest"]["uniform_brier"] == pytest.approx(
        1/7 - 1/37
    )
    assert len(res["training"]["expert_weights"]) >= 10
    assert sum(res["training"]["expert_weights"].values()) == pytest.approx(1.0)
    with (out / "paired_rounds_101_to_latest.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with (out / "paired_tickets_101_to_latest.csv").open(encoding="utf-8-sig") as f:
        tickets = list(csv.DictReader(f))
    assert [int(row["round"]) for row in rows] == [101, 102, 103, 104]
    assert len(tickets) == 40
    for rnd in range(101, 105):
        for model in ("candidate", "champion"):
            group = [r for r in tickets if int(r["round"]) == rnd and r["model"] == model]
            assert len(group) == 5
            numbers = [int(n) for r in group for n in r["predicted_numbers"].split()]
            assert len(numbers) == 35 and len(set(numbers)) == 35
    preview = res["rank_705_research_preview"]
    assert sorted(preview["ranking_1_to_37"]) == list(range(1, 38))
    assert len(preview["ranked_tickets"]) == 5
    assert len(preview["excluded_numbers"]) == 2


def test_future_draw_cannot_change_prior_rankings(tmp_path):
    champ = tmp_path / "champion.json"
    make_champion(champ)
    p1, p2 = tmp_path / "short.csv", tmp_path / "long.csv"
    sample_history(p1, 103)
    sample_history(p2, 104, perturb_last=True)
    one = rank.run(csv_path=p1, champion_path=champ, out_dir=tmp_path / "out1")
    two = rank.run(csv_path=p2, champion_path=champ, out_dir=tmp_path / "out2")
    assert one["evaluated_rounds"] == 3 and two["evaluated_rounds"] == 4
    def read(path):
        with path.open(encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    earlier = read(tmp_path / "out1" / "paired_rounds_101_to_latest.csv")
    later = read(tmp_path / "out2" / "paired_rounds_101_to_latest.csv")
    assert earlier == later[:-1]


def test_champion_file_identity_checked(tmp_path):
    p = tmp_path / "history.csv"
    sample_history(p)
    champ = tmp_path / "champion.json"
    cfg = v2.DEFAULT_CHAMPION
    champ.write_text(json.dumps({"config": asdict(cfg), "model_version": "wrong"}),
                     encoding="utf-8")
    with pytest.raises(RuntimeError, match="approved Champion"):
        rank.run(csv_path=p, champion_path=champ, out_dir=tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_early_training_and_gapped_history_rejected(tmp_path):
    p = tmp_path / "history.csv"
    champ = tmp_path / "champion.json"
    make_champion(champ)
    sample_history(p, n=100)
    with pytest.raises(ValueError, match="more than 100"):
        rank.run(csv_path=p, champion_path=champ, out_dir=tmp_path / "out")
    sample_history(p, n=104)
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text("\n".join([lines[0], *lines[2:]]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no gaps"):
        rank.run(csv_path=p, champion_path=champ, out_dir=tmp_path / "out")


def test_only_verified_latest_source_history_can_be_used_for_production_reference(tmp_path):
    csv_path = tmp_path / "history.csv"
    champion = tmp_path / "champion.json"
    sample_history(csv_path)
    make_champion(champion)
    from loto7_evolving_agent import fingerprint_file
    verification = tmp_path / "source_validation.json"
    good = {
        "status": "ok",
        "verification": "verified_two_result_sources",
        "latest": {"round": 104, "date": "2015-03-27"},
        "verification_provenance": {"draw_csv_sha256": fingerprint_file(csv_path)},
    }
    # Synthetic dates, not a live external verification: this tests the gate only.
    from datetime import date, timedelta
    good["latest"]["date"] = (date(2013,4,5)+timedelta(days=7*103)).isoformat()
    verification.write_text(json.dumps(good), encoding="utf-8")
    result = rank.run(csv_path=csv_path, champion_path=champion,
                      out_dir=tmp_path / "result", source_report=verification)
    assert result["source_verification"].startswith("verified_two_result_sources")

    wrong = {**good, "verification_provenance": {"draw_csv_sha256": "tampered"}}
    verification.write_text(json.dumps(wrong), encoding="utf-8")
    with pytest.raises(RuntimeError, match="mismatches"):
        rank.run(csv_path=csv_path, champion_path=champion,
                 out_dir=tmp_path / "invalid", source_report=verification)
    assert not (tmp_path / "invalid").exists()
