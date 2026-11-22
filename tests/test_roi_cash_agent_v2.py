"""Deterministic cash-trained ROI candidate: budget invariants, no target peek, no false promotion."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date,timedelta
from pathlib import Path

import numpy as np
import pytest

import loto7_v2_runner as v2
from research.roi_cash_agent_v2 import (
    CashAgentConfig, VERSION, candidate_from_cash_history, _public_cash
)
from research.roi_cash_agent_v2_replay import run as replay


def sample(n=104):
    h=np.zeros((n,37),dtype=np.int8)
    b=np.zeros_like(h)
    p=np.zeros((n,7),dtype=float)
    p[:]=[0,1000,1800,9000,85000,3000000,100000000]
    for t in range(n):
        picks=np.asarray([(t*7+k*5)%37 for k in range(7)])
        h[t,picks]=1
        missing=[x for x in range(37) if not h[t,x]]
        b[t,missing[:2]]=1
    return h,b,p


def ranking():
    return list(range(1,38))


def synthetic_csv(path:Path,n=104,flip_last=False):
    h,b,p=sample(n)
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream)
        writer.writerow(["回別","抽せん日","本数字","ボーナス数字",
                         "1等当選金額","2等当選金額","3等当選金額",
                         "4等当選金額","5等当選金額","6等当選金額"])
        for i in range(n):
            main=(np.flatnonzero(h[i])+1).tolist()
            if flip_last and i==n-1:
                main=list(range(1,8))
                bonus=[x for x in range(1,38) if x not in main][:2]
            else:
                bonus=(np.flatnonzero(b[i])+1).tolist()
            writer.writerow([
                f"第{i+1}回",
                (date(2013,4,5)+timedelta(days=7*i)).isoformat(),
                " ".join(str(x) for x in main),
                " ".join(str(x) for x in bonus),
                "100000000円","3000000円","85000円","9000円","1800円","1000円",
            ])


def test_cash_optimizer_preserves_disjoint_set_and_tie_is_deterministic():
    h,b,p=sample()
    a,x=candidate_from_cash_history(h,b,p,ranking())
    c,y=candidate_from_cash_history(h,b,p,ranking())
    assert a==c and x==y
    assert VERSION==x["candidate_version"]
    assert x["history_rows"]==104
    assert 0<=x["swaps"]<=8
    assert len(a)==5
    assert all(len(t)==7 for t in a)
    assert sorted(v for t in a for v in t)==list(range(1,36))
    assert x["production_modified"] is False


def test_optimizer_declines_cash_swaps_on_zero_gain():
    h,b,p=sample()
    p[:]=0
    chosen,meta=candidate_from_cash_history(h,b,p,ranking())
    assert chosen==[tuple(range(i*7+1,(i+1)*7+1)) for i in range(5)]
    assert meta["swaps"]==0
    assert meta["training_cash_objective_gain_yen_per_draw"]==0


def test_unknown_public_payout_is_not_treated_as_zero_or_earned():
    h,b,p=sample()
    p[:]=0
    p[:,-1]=-1
    proposed,diagnostics=candidate_from_cash_history(h,b,p,ranking())
    assert len(proposed)==5
    assert all(v>=0 for v in diagnostics["training_cash_swaps_gain"])
    # Missing grade-1 payouts cannot become fictitious positive cash amounts.
    v=_public_cash(np.array([[7]]),np.array([[0]]),p[:1],6000)
    assert np.isnan(v[0,0])


@pytest.mark.parametrize("bad",[
    CashAgentConfig(lookback=60),
    CashAgentConfig(max_swaps=-1),
    CashAgentConfig(half_life=0),
    CashAgentConfig(payout_cap_yen=0),
])
def test_reject_invalid_cash_training_configuration(bad):
    h,b,p=sample()
    with pytest.raises(ValueError,match="invalid training config"):
        candidate_from_cash_history(h,b,p,ranking(),bad)


def test_reject_corrupted_cash_train_data():
    h,b,p=sample()
    h[0,:]=0
    with pytest.raises(ValueError,match="invalid or overlapping"):
        candidate_from_cash_history(h,b,p,ranking())
    h,b,p=sample()
    b[0,:]=0
    with pytest.raises(ValueError,match="invalid or overlapping"):
        candidate_from_cash_history(h,b,p,ranking())
    h,b,p=sample()
    p[0,3]=-999
    with pytest.raises(ValueError,match="nonnegative public amounts"):
        candidate_from_cash_history(h,b,p,ranking())


def test_cash_replay_round2_has_past_only_ranking_and_three_arms(tmp_path):
    data=tmp_path/"draws.csv"
    model=tmp_path/"champion.json"
    synthetic_csv(data,n=104)
    cfg=v2.DEFAULT_CHAMPION
    model.write_text(json.dumps({"model_version":cfg.version(),"config":asdict(cfg)}))
    out=tmp_path/"result"
    summary=replay(csv_path=data,champion_file=model,source_report=None,
                   out_dir=out,matched_reps=1,verify_parity=False)
    assert summary["first_round"]==2
    assert summary["last_round"]==104
    assert summary["evaluated_rounds"]==103
    assert summary["three_arm_ticket_rows"]==103*15
    assert summary["future_prospective_oos_draws_for_this_candidate"]==0
    assert summary["future_roi_promotion_gate_met"] is False
    assert summary["production_promotion"] is False
    assert summary["next_target_retrained_unissued_preview"]["target_round"]==105
    assert summary["periods"]["trained_round101_latest"]["rounds"]==4
    assert (out/"CASH_V2_REPORT.md").is_file()
    with (out/"cash_v2_three_arm_rounds_2_to_latest.csv").open(encoding="utf-8-sig") as f:
        records=list(csv.DictReader(f))
    assert len(records)==103
    assert all(r["candidate_tickets"]==r["baseline_tickets"]
               for r in records[:99])
    assert all(int(r["candidate_swaps"])==0 for r in records[:99])
    assert all(r["prefix_sha256"]==records[i]["prefix_sha256"] for i,r in enumerate(records))


def test_candidate_does_not_retrain_using_target_outcome(tmp_path):
    cfg=v2.DEFAULT_CHAMPION
    model=tmp_path/"champion.json"
    model.write_text(json.dumps({"model_version":cfg.version(),"config":asdict(cfg)}))
    a=tmp_path/"a.csv"
    b=tmp_path/"b.csv"
    synthetic_csv(a,n=104)
    synthetic_csv(b,n=105,flip_last=True)
    x=replay(csv_path=a,champion_file=model,source_report=None,
             out_dir=tmp_path/"result_a",matched_reps=1,verify_parity=False)
    y=replay(csv_path=b,champion_file=model,source_report=None,
             out_dir=tmp_path/"result_b",matched_reps=1,verify_parity=False)
    assert x["last_round"]==104 and y["last_round"]==105
    def freeze(path):
        with path.open(encoding="utf-8-sig") as f:
            return [(row["round"],row["candidate_tickets"],row["prefix_sha256"])
                    for row in csv.DictReader(f)]
    pa=freeze(tmp_path/"result_a/cash_v2_three_arm_rounds_2_to_latest.csv")
    pb=freeze(tmp_path/"result_b/cash_v2_three_arm_rounds_2_to_latest.csv")
    assert pa==pb[:-1]
