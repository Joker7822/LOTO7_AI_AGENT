"""Operator-authorized ROI-cash v2 Production integration and immutable ledger tests."""
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
from loto7_evolving_agent import fingerprint_file
from production_roi_cash35_v2 import (
    ALGORITHM_VERSION, SELECTION_AUTHORITY, CashAgentConfig,
    candidate_from_canonical_rows, layout_sha256, training_arrays_from_canonical_rows,
)
from research.roi_cash_agent_v2 import candidate_from_cash_history


def _history(path:Path, n:int=704) -> np.ndarray:
    data=np.zeros((n,37),dtype=np.int8)
    with path.open("w",encoding="utf-8",newline="") as file:
        writer=csv.writer(file)
        writer.writerow(["回別","抽せん日","本数字","ボーナス数字",
                         "1等当選金額","2等当選金額","3等当選金額",
                         "4等当選金額","5等当選金額","6等当選金額"])
        for idx in range(n):
            main=sorted((idx*11 + k*5)%37+1 for k in range(7))
            data[idx,np.asarray(main)-1]=1
            bonus=[z for z in range(1,38) if z not in main][:2]
            writer.writerow([
                f"第{idx+1}回",
                (date(2013,4,5)+timedelta(days=7*idx)).isoformat(),
                " ".join(f"{v:02d}" for v in main),
                " ".join(f"{v:02d}" for v in bonus),
                "100000000円","3000000円","85000円",
                "9000円","1800円","1000円",
            ])
    return data


def _rank_scores():
    z=np.arange(1,38,dtype=float)
    return z/z.sum()


def _configure(monkeypatch):
    monkeypatch.setattr(geometry,"verify_source",lambda *a:{"trusted":True,"round":704})
    monkeypatch.setattr(geometry,"production_window_guard",lambda *a:None)
    monkeypatch.setattr(geometry,"walk_forward_evolve",lambda *a,**k:
                        SimpleNamespace(keys=["fixture"],final_weights=np.array([1.0])))
    monkeypatch.setattr(geometry,"final_score",lambda *a,**k:_rank_scores())


def _prepared(tmp_path,monkeypatch):
    csv_path=tmp_path/"data.csv"
    main=_history(csv_path)
    _configure(monkeypatch)
    out=tmp_path/"out"
    cfg=v2.DEFAULT_CHAMPION
    state=geometry.prepare_new_production_outputs(
        csv_path=csv_path, out_dir=out, champion_version=cfg.version(),
        data_sha=fingerprint_file(csv_path), latest_round=704, target_round=705,
        latest_draw_date="2026-11-20",git_sha="tested",
        source_path=out/"source_validation.json",
        history=main, champion_config=cfg,
    )
    return csv_path,main,out,state


def _issued_tickets(out):
    return [tuple(int(x) for x in row["numbers"].split())
            for row in ledger.read_csv(out/"candidate_tickets.csv")]


def test_new_705_policy_is_v2_but_all_prior_frozen_policies_survive():
    assert policy.publication_policy_for_target(702)==policy.VERSION
    assert policy.publication_policy_for_target(704)==policy.VERSION
    assert policy.publication_policy_for_target(705)==policy.ROI_CASH_VERSION
    assert policy.ROI_CASH_MIN_TARGET_ROUND==705
    assert ALGORITHM_VERSION=="research-roi-cash-trained-ranked35-v2"
    ticket_sets=[
        {"ticket":i,"model_version":"baseline+"+version,
         "predicted_numbers":" ".join(f"{n:02d}" for n in range(7*i-6,7*i+1))}
        for i in range(1,6)
        for version in []
    ]
    for version in (policy.VERSION,policy.RANKED_VERSION,policy.COMBINATION_VERSION,policy.ROI_CASH_VERSION):
        rows=[{"ticket":i,"model_version":"baseline+"+version,
                "predicted_numbers":" ".join(f"{n:02d}" for n in range(7*i-6,7*i+1))}
              for i in range(1,6)]
        policy.validate_issued_rows(rows,705)
        assert policy.issued_policy(rows,705)==version
    with pytest.raises(ValueError,match="ineligible"):
        policy.validate_issued_rows(rows,704)


def test_v2_production_matches_exact_cash_training_and_frozen_sha(tmp_path,monkeypatch):
    data,history,out,state=_prepared(tmp_path,monkeypatch)
    assert state["production_ticket_policy_version"]==policy.ROI_CASH_VERSION
    assert state["production_roi_cash_v2_algorithm_version"]==ALGORITHM_VERSION
    assert state["production_roi_cash_v2_selection_authority"]==SELECTION_AUTHORITY
    assert state["production_roi_cash_v2_training_rows"]==704
    assert state["production_roi_cash_v2_target_outcome_used"] is False
    assert state["production_roi_prediction_skill_confirmed"] is False
    assert state["production_expected_future_roi"] is None
    assert state["production_purchase_automation"] is False
    assert state["production_promotion_method"]=="explicit_operator_policy_switch_without_proven_future_roi"
    canon=ledger.read_csv(data)
    main,bon,prizes=training_arrays_from_canonical_rows(canon)
    assert np.array_equal(main,history)
    _,ranking=geometry.ranked_portfolio_from_scores(_rank_scores())
    direct,diagnostic=candidate_from_cash_history(main,bon,prizes,ranking,CashAgentConfig())
    assert _issued_tickets(out)==direct
    assert state["production_roi_cash_v2_swaps"]==diagnostic["swaps"]
    assert state["production_roi_cash_v2_layout_sha256"]==layout_sha256(
        target_round=705,data_sha=fingerprint_file(data),
        champion_version=v2.DEFAULT_CHAMPION.version(),
        ranking=ranking,tickets=direct
    )
    assert len(set(v for t in direct for v in t))==35
    frozen=ledger.append_current_predictions(
        canon,ledger.read_csv(out/"candidate_tickets.csv"),
        out/"predictions.csv",state,current_data_sha=fingerprint_file(data)
    )
    assert frozen==5
    assert all(row["model_version"].endswith("+"+policy.ROI_CASH_VERSION)
               for row in ledger.read_csv(out/"predictions.csv"))
    before=(out/"predictions.csv").read_bytes()
    assert ledger.append_current_predictions(
        canon,ledger.read_csv(out/"candidate_tickets.csv"),
        out/"predictions.csv",state,current_data_sha=fingerprint_file(data)
    )==0
    assert (out/"predictions.csv").read_bytes()==before


@pytest.mark.parametrize("key,value",[
    ("production_roi_cash_v2_algorithm_version","fake-model"),
    ("production_roi_cash_v2_config",{"lookback":52}),
    ("production_roi_cash_v2_training_rows",703),
    ("production_roi_cash_v2_training_data_sha256","forged"),
    ("production_roi_cash_v2_layout_sha256","0"*64),
    ("production_roi_cash_v2_swaps",-1),
    ("production_roi_cash_v2_training_cash_objective_gain_yen_per_draw",float("nan")),
    ("production_roi_cash_v2_selection_authority","forged"),
    ("production_roi_cash_v2_target_outcome_used",True),
    ("production_promotion_method","future_oos_only"),
    ("production_roi_prediction_skill_confirmed",True),
    ("production_expected_future_roi",2.0),
    ("production_purchase_automation",True),
])
def test_v2_auditor_fails_closed_on_fake_model_or_cashflow(tmp_path,monkeypatch,key,value):
    data,_,out,state=_prepared(tmp_path,monkeypatch)
    changed={**state,key:value}
    with pytest.raises(RuntimeError,match="refusing ROI-cash v2"):
        ledger.append_current_predictions(
            ledger.read_csv(data),ledger.read_csv(out/"candidate_tickets.csv"),
            out/"predictions.csv",changed,current_data_sha=fingerprint_file(data)
        )
    assert not (out/"predictions.csv").exists()


def test_v2_auditor_fails_before_freeze_on_forged_ticket_and_missing_draw(tmp_path,monkeypatch):
    data,_,out,state=_prepared(tmp_path,monkeypatch)
    rows=ledger.read_csv(out/"candidate_tickets.csv")
    bad=[dict(r) for r in rows]
    bad[0]["numbers"]=bad[1]["numbers"]
    with pytest.raises(RuntimeError,match="tickets disagree|ranking"):
        ledger.append_current_predictions(
            ledger.read_csv(data),bad,out/"predictions.csv",
            state,current_data_sha=fingerprint_file(data)
        )
    with pytest.raises(RuntimeError,match="complete preceding draw history"):
        ledger.append_current_predictions(
            ledger.read_csv(data)[:-1],rows,out/"predictions.csv",
            state,current_data_sha=fingerprint_file(data)
        )
    assert not (out/"predictions.csv").exists()


def test_missing_public_payouts_are_not_silently_inferred(tmp_path):
    data=tmp_path/"source.csv"
    _history(data,n=104)
    rows=ledger.read_csv(data)
    for row in rows:
        for grade in range(1,7):
            row[f"{grade}等当選金額"]="該当なし"
    _,ranking=geometry.ranked_portfolio_from_scores(_rank_scores())
    with pytest.raises(ValueError,match="missing necessary public payout"):
        candidate_from_canonical_rows(rows,ranking,CashAgentConfig())


def test_weekly_operator_v2_freeze_and_exact_republication(tmp_path,monkeypatch):
    data=tmp_path/"history.csv"
    _history(data,n=704)
    _configure(monkeypatch)
    out=tmp_path/"out"
    cfg=v2.DEFAULT_CHAMPION
    champion=tmp_path/"model.json"
    champion.write_text(json.dumps({"model_version":cfg.version(),"config":asdict(cfg)}))
    first=weekly.publish(csv_path=data,out_dir=out,champion_file=champion,
                         research_state=tmp_path/"missing_research.json")
    assert first["reason"]=="frozen_to_canonical_prediction_ledger"
    assert first["ticket_policy"]==policy.ROI_CASH_VERSION
    assert first["production_promotion_method"]=="explicit_operator_policy_switch_without_proven_future_roi"
    assert geometry.verify_canonical_publication(out)["status"]=="disjoint35_pass"
    payload=(out/"predictions.csv").read_bytes()
    monkeypatch.setattr(geometry,"prepare_new_production_outputs",
                        lambda **kw:(_ for _ in ()).throw(AssertionError("retrained frozen target")))
    second=weekly.publish(csv_path=data,out_dir=out,champion_file=champion,
                          research_state=tmp_path/"missing_research.json")
    assert second["ticket_policy"]==policy.ROI_CASH_VERSION
    assert second["production_promotion_method"]=="explicit_operator_policy_switch_without_proven_future_roi"
    assert second["reason"]=="republished_frozen_ledger_prediction"
    assert (out/"predictions.csv").read_bytes()==payload
