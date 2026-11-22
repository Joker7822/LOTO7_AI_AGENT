"""Production adoption tests for independently trained ranked35 combination agent."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import audit_ledger as ledger
import loto7_v2_runner as v2
import production_disjoint35_policy as policy
import production_ticket_geometry35 as geometry
import weekly_production_prediction as weekly
from combination_agent35_core import AgentConfig, candidate_from_history
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible


def synthetic_loto7(path: Path, n: int = 704) -> np.ndarray:
    hist = np.zeros((n, 37), dtype=np.int8)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["回別", "抽せん日", "本数字", "ボーナス数字"])
        for j in range(n):
            numbers = sorted((j*11 + k*5) % 37 + 1 for k in range(7))
            hist[j, np.array(numbers)-1] = 1
            bonus = [v for v in range(1,38) if v not in numbers][:2]
            writer.writerow([
                f"第{j+1}回",
                (date(2013,4,5)+timedelta(days=j*7)).isoformat(),
                " ".join(f"{n:02d}" for n in numbers),
                " ".join(f"{n:02d}" for n in bonus),
            ])
    return hist


def q_descending() -> np.ndarray:
    q = np.arange(1,38,dtype=float)
    return q / q.sum()


def _prepared(tmp_path, monkeypatch):
    data = tmp_path / "history.csv"
    x = synthetic_loto7(data)
    out = tmp_path / "output"
    cfg = v2.DEFAULT_CHAMPION
    monkeypatch.setattr(geometry, "publication_policy_for_target", lambda *_: policy.COMBINATION_VERSION)
    monkeypatch.setattr(geometry, "verify_source", lambda *a: {"trusted":True,"round":704})
    monkeypatch.setattr(geometry, "production_window_guard", lambda *a: None)
    monkeypatch.setattr(geometry, "walk_forward_evolve", lambda *a, **kw:
                        SimpleNamespace(keys=["synthetic"],final_weights=np.array([1.0])))
    monkeypatch.setattr(geometry, "final_score", lambda *a, **kw:q_descending())
    state = geometry.prepare_new_production_outputs(
        csv_path=data, out_dir=out, champion_version=cfg.version(),
        data_sha=fingerprint_file(data),
        latest_round=704, target_round=705,
        latest_draw_date="2026-11-20", git_sha="test", source_path=out/"source.json",
        history=x, champion_config=cfg,
    )
    return data,x,out,state


def test_policy_migrates_new_issuances_without_invalidating_old_frozen_rows():
    assert policy.publication_policy_for_target(702) == policy.VERSION
    assert policy.publication_policy_for_target(704) == policy.VERSION
    assert policy.publication_policy_for_target(705) == policy.ROI_CASH_VERSION
    old = [
        {"ticket":i,"model_version":"baseline+"+policy.RANKED_VERSION,
         "predicted_numbers":" ".join(f"{n:02d}" for n in range((i-1)*7+1,i*7+1))}
        for i in range(1,6)
    ]
    policy.validate_issued_rows(old, 705)
    assert policy.issued_policy(old,705) == policy.RANKED_VERSION
    current = [{**row,"model_version":"baseline+"+policy.COMBINATION_VERSION}
               for row in old]
    policy.validate_issued_rows(current,705)
    assert policy.issued_policy(current,705) == policy.COMBINATION_VERSION
    next_policy = [{**row,"model_version":"baseline+"+policy.ROI_CASH_VERSION} for row in old]
    policy.validate_issued_rows(next_policy,705)
    assert policy.issued_policy(next_policy,705) == policy.ROI_CASH_VERSION
    with pytest.raises(ValueError, match="ineligible"):
        policy.validate_issued_rows(current,704)


def test_production_trains_and_auditor_recomputes_identical_combo(tmp_path,monkeypatch):
    data,history,out,state = _prepared(tmp_path,monkeypatch)
    assert state["production_ticket_policy_version"] == policy.COMBINATION_VERSION
    assert state["production_combo_agent_version"] == policy.COMBINATION_VERSION
    assert state["production_combo_training_rows"] == 704
    assert state["production_combo_training_data_sha256"] == fingerprint_file(data)
    assert len(state["production_combo_layout_sha256"]) == 64
    assert state["first_prize_odds_unchanged"] is True
    baseline, ranking = geometry.ranked_portfolio_from_scores(q_descending())
    expected,diag = candidate_from_history(history,ranking,AgentConfig())
    assert state["production_combo_swaps"] == diag["swap_count"]
    rows=ledger.read_csv(out/"candidate_tickets.csv")
    actual=[tuple(int(v) for v in row["numbers"].split()) for row in rows]
    assert actual==expected
    assert sorted(n for row in actual for n in row)==sorted(ranking[:35])
    assert len(set(n for row in actual for n in row))==35
    assert sorted(n for row in actual for n in row)==sorted(n for row in baseline for n in row)

    original=ledger.read_csv(data)
    pred_path=out/"predictions.csv"
    frozen=ledger.append_current_predictions(
        original,rows,pred_path,state,current_data_sha=fingerprint_file(data))
    assert frozen == 5
    assert all(row["model_version"].endswith("+"+policy.COMBINATION_VERSION)
               for row in ledger.read_csv(pred_path))
    assert ledger.append_current_predictions(
        original,rows,pred_path,state,current_data_sha=fingerprint_file(data)) == 0
    issued_bytes=pred_path.read_bytes()
    assert pred_path.read_bytes()==issued_bytes


def test_production_fails_closed_on_tamper_before_freeze(tmp_path,monkeypatch):
    data,hist,out,state = _prepared(tmp_path,monkeypatch)
    original=ledger.read_csv(data)
    rows=ledger.read_csv(out/"candidate_tickets.csv")
    wrong=[dict(v) for v in rows]
    wrong[0]["numbers"]=wrong[1]["numbers"]
    with pytest.raises(RuntimeError,match="ranking|combination"):
        ledger.append_current_predictions(
            original,wrong,out/"predictions.csv",state,current_data_sha=fingerprint_file(data))
    assert not (out/"predictions.csv").exists()
    for name,value in (
        ("production_combo_swaps",999),
        ("production_combo_layout_sha256","forged"),
        ("production_combo_training_data_sha256","forged"),
        ("production_combo_training_rows",703),
        ("production_rank_order",list(range(1,38))),
        ("production_combo_config",{**state["production_combo_config"],"max_swaps":19}),
    ):
        changed={**state,name:value}
        with pytest.raises(RuntimeError,match="combination|ranking"):
            ledger.append_current_predictions(
                original,rows,out/"predictions.csv",changed,
                current_data_sha=fingerprint_file(data))
    assert not (out/"predictions.csv").exists()


def test_combo_fails_closed_if_input_history_was_forged(tmp_path,monkeypatch):
    data,history,out,state=_prepared(tmp_path,monkeypatch)
    csv_rows=ledger.read_csv(data)
    tampered=[dict(r) for r in csv_rows]
    tampered[700]["本数字"]="01 02 03 04 05 06 07"
    # Even if caller presents the original SHA, replaying actual supplied
    # history must produce the correct digest/combination (or fail).
    # For guaranteed fail here deliberately remove a round.
    tampered.pop(1)
    with pytest.raises(RuntimeError,match="complete preceding draw history"):
        ledger.append_current_predictions(
            tampered,ledger.read_csv(out/"candidate_tickets.csv"),
            out/"predictions.csv",state,current_data_sha=fingerprint_file(data))


def test_frozen_old_ranked_705_is_not_reissued_under_new_combo_policy(tmp_path,monkeypatch):
    data=tmp_path/"history.csv"
    synthetic_loto7(data)
    out=tmp_path/"output"
    out.mkdir()
    old=[{"prediction_id":f"old-{i}","ticket":str(i),
          "model_version":"baseline+"+policy.RANKED_VERSION,
          "target_round":"第705回",
          "predicted_numbers":" ".join(f"{n:02d}"
                for n in range((i-1)*7+1,i*7+1))}
         for i in range(1,6)]
    ledger.write_csv(out/"predictions.csv",old,ledger.PRED_FIELDS)
    before=(out/"predictions.csv").read_bytes()
    monkeypatch.setattr(geometry,"prepare_new_production_outputs",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("retrained frozen")))
    result=weekly.publish(csv_path=data,out_dir=out,
                          champion_file=tmp_path/"missing.json",
                          research_state=tmp_path/"missing.json")
    assert result["ticket_policy"]==policy.RANKED_VERSION
    assert result["reason"]=="republished_frozen_ledger_prediction"
    assert (out/"predictions.csv").read_bytes()==before


def test_weekly_can_publish_new_combo_and_republish_unchanged(tmp_path,monkeypatch):
    data=tmp_path/"history.csv"
    synthetic_loto7(data)
    out=tmp_path/"out"
    out.mkdir()
    cfg=v2.DEFAULT_CHAMPION
    champ=tmp_path/"champion.json"
    champ.write_text(json.dumps({"model_version":cfg.version(),
                                  "config":asdict(cfg)}),encoding="utf-8")
    monkeypatch.setattr(geometry,"publication_policy_for_target",lambda *_:policy.COMBINATION_VERSION)
    monkeypatch.setattr(geometry,"verify_source",lambda *a:{"trusted":True,"round":704})
    monkeypatch.setattr(geometry,"production_window_guard",lambda *a:None)
    monkeypatch.setattr(geometry,"walk_forward_evolve",lambda *a,**kw:
                        SimpleNamespace(keys=["test"],final_weights=np.array([1.0])))
    monkeypatch.setattr(geometry,"final_score",lambda *a,**kw:q_descending())
    initial=weekly.publish(csv_path=data,out_dir=out,champion_file=champ,
                            research_state=tmp_path/"missing.json")
    assert initial["ticket_policy"]==policy.COMBINATION_VERSION
    assert initial["reason"]=="frozen_to_canonical_prediction_ledger"
    frozen=(out/"predictions.csv").read_bytes()
    assert geometry.verify_canonical_publication(out)["status"]=="disjoint35_pass"
    monkeypatch.setattr(geometry,"prepare_new_production_outputs",
                        lambda **kw:(_ for _ in ()).throw(AssertionError("reissued frozen")))
    again=weekly.publish(csv_path=data,out_dir=out,champion_file=champ,
                         research_state=tmp_path/"missing.json")
    assert again["ticket_policy"]==policy.COMBINATION_VERSION
    assert again["reason"]=="republished_frozen_ledger_prediction"
    assert (out/"predictions.csv").read_bytes()==frozen
