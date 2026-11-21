"""Exact round-2-to-latest prequential replay of the production combination AI."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import pytest

import loto7_v2_runner as v2
from research import production_combination_round2_replay as replay


def write_history(path: Path, count: int = 105, tamper_last: bool = False) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "回別", "抽せん日", "本数字", "ボーナス数字",
            "4等当選金額", "5等当選金額", "6等当選金額"
        ])
        for i in range(count):
            numbers = sorted((i*13 + j*5)%37+1 for j in range(7))
            if tamper_last and i == count-1:
                numbers = list(range(1,8))
            bonus = [n for n in range(1,38) if n not in numbers][:2]
            writer.writerow([
                f"第{i+1}回", (date(2013,4,5)+timedelta(days=i*7)).isoformat(),
                " ".join(str(n) for n in numbers),
                " ".join(str(n) for n in bonus),
                "10000円", "1700円", "900円",
            ])


def champion(path: Path) -> None:
    cfg=v2.DEFAULT_CHAMPION
    path.write_text(json.dumps({
        "model_version":cfg.version(),"config":asdict(cfg)
    }),encoding="utf-8")


def records(path:Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def test_full_round2_replay_separates_cold_start_and_trained_ai(tmp_path):
    data,model=tmp_path/"history.csv",tmp_path/"champion.json"
    write_history(data,104)
    champion(model)
    out=tmp_path/"out"
    result=replay.run(csv_path=data,champion_file=model,out_dir=out,
                      matched_reps=2,verify_parity=True)
    assert result["target_round_first"] == 2
    assert result["target_round_last"] == 104
    assert result["source_rows"] == 104
    assert result["results"]["all_rounds_2_plus"]["round_count"] == 103
    assert result["results"]["uniform_cold_start_2_20"]["round_count"] == 19
    assert result["results"]["untrained_expert_21_100"]["round_count"] == 80
    assert result["results"]["approved_champion_101_plus"]["round_count"] == 4
    assert result["total_ticket_rows"]==103*10
    assert result["evaluated_combination_tickets"]==103*5
    assert result["evaluated_baseline_tickets"]==103*5
    assert result["cold_start_fallback_rounds"]==99
    assert result["champion_parity_target_rounds"]==[102,103,104]
    assert result["next_target_retrained_preview"]["target_round"]==105
    assert result["issued_predictions_changed"] is False
    assert result["future_oos_evidence_changed"] is False
    assert result["promotion_authorized_by_replay"] is False

    rounds=records(out/"rounds_2_to_latest.csv")
    tickets=records(out/"tickets_2_to_latest.csv")
    assert [int(r["round"]) for r in rounds]==list(range(2,105))
    assert len(tickets)==103*10
    assert all(int(r["combo_swaps"])==0 for r in rounds[:99])
    assert all(r["combination_phase"]=="not_trainable_fallback_rank_order" for r in rounds[:99])
    assert all(r["combination_phase"]=="trained_pairwise_combination" for r in rounds[99:])
    assert all(r["combo_tickets"]==r["baseline_tickets"] for r in rounds[:99])
    for row in rounds:
        chosen={int(n) for n in row["rank_1_to_35"].split()}
        excluded={int(n) for n in row["excluded_rank_36_37"].split()}
        assert len(chosen)==35 and len(excluded)==2 and not chosen&excluded
        for arm,key in (("combination","combo_tickets"),("rank_order","baseline_tickets")):
            parts=row[key].split("|")
            assert len(parts)==5
            numbers=[int(v) for p in parts for v in p.split()]
            assert len(numbers)==len(set(numbers))==35
            assert set(numbers)==chosen
        assert len(row["source_prefix_sha256"])==64
        assert len(row["rank_sha256"])==64


def test_cannot_see_future_draw_when_replaying_historical_tickets(tmp_path):
    data1,data2=tmp_path/"104.csv",tmp_path/"105.csv"
    model=tmp_path/"champion.json"
    write_history(data1,104)
    write_history(data2,105,tamper_last=True)
    champion(model)
    out1,out2=tmp_path/"out1",tmp_path/"out2"
    replay.run(csv_path=data1,champion_file=model,out_dir=out1,
               matched_reps=2,verify_parity=False)
    replay.run(csv_path=data2,champion_file=model,out_dir=out2,
               matched_reps=2,verify_parity=False)
    assert records(out1/"rounds_2_to_latest.csv")==records(out2/"rounds_2_to_latest.csv")[:-1]
    assert records(out1/"tickets_2_to_latest.csv")==records(out2/"tickets_2_to_latest.csv")[:-10]


def test_wrong_min_training_and_missing_champion_fail_before_output(tmp_path):
    data=tmp_path/"draws.csv"
    model=tmp_path/"champ.json"
    write_history(data,104)
    champion(model)
    with pytest.raises(ValueError,match="min_train=100"):
        replay.run(csv_path=data,champion_file=model,out_dir=tmp_path/"not_created",min_train=80)
    with pytest.raises(RuntimeError,match="approved Champion"):
        replay.run(csv_path=data,champion_file=tmp_path/"not_exists",out_dir=tmp_path/"not_created")
    assert not (tmp_path/"not_created").exists()


def test_gapped_rounds_never_generate_research_predictions(tmp_path):
    data=tmp_path/"draws.csv"
    model=tmp_path/"champion.json"
    write_history(data,104)
    champion(model)
    lines=data.read_text(encoding="utf-8").splitlines()
    data.write_text("\n".join([lines[0],*lines[2:]])+"\n",encoding="utf-8")
    with pytest.raises(RuntimeError,match="contiguous"):
        replay.run(csv_path=data,champion_file=model,out_dir=tmp_path/"out")
