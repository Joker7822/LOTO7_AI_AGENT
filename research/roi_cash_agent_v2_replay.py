#!/usr/bin/env python3
"""Research-only three-arm ROI cash-trained v2 ranked35 chronological replay.

Reuses the existing independently audited Champion/replay for rank snapshots
and incumbents, and trains v2 only from historical prizes *before* each target.
No current-round result is passed to candidate_from_cash_history.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict
from pathlib import Path

import numpy as np

from audit_ledger import grade_ticket
from loto7_evolving_agent import make_history, read_csv_flexible, fingerprint_file
from research.production_combination_round2_replay import (
    run as run_incumbent, _prize_payout, _numbers, _write_csv
)
from research.roi_cash_agent_v2 import CashAgentConfig, VERSION as CANDIDATE_VERSION, candidate_from_cash_history
from production_disjoint35_policy import COMBINATION_VERSION
from roi_first_governance import ROUND_COST_YEN, paired_signflip_yen

VERSION="research-roi-cash-training-v2-round2-replay-v1"
GRADES=("はずれ","6等","5等","4等","3等","2等","1等")
TICKET_FIELDS=(
    "round","draw_date","arm","ticket","predicted_numbers","actual_main",
    "actual_bonus","main_hits","bonus_hits","grade","public_payout_yen",
    "prefix_sha256","candidate_training_rows",
)
ROUND_FIELDS=(
    "round","draw_date","training_rows","phase","prefix_sha256","rank_top35",
    "excluded_two","candidate_tickets","candidate_swaps",
    "candidate_training_gain_yen_per_draw","candidate_training_status",
    "current_production_tickets","baseline_tickets",
    "candidate_payout_yen","current_production_payout_yen","baseline_payout_yen",
    "candidate_complete","current_production_complete","baseline_complete",
    "candidate_score","current_production_score","baseline_score",
    "candidate_max_hits","current_production_max_hits","baseline_max_hits",
)


def _source_tables(history:np.ndarray, clean) -> tuple[np.ndarray,np.ndarray]:
    bonus=np.zeros_like(history,dtype=np.int8)
    payout=np.full((len(history),7),-1.,dtype=float)
    payout[:,0]=0.
    for i in range(len(history)):
        row=clean.iloc[i]
        bg=[int(v) for v in re.findall(r"\d+",str(row.get("ボーナス数字","") or ""))]
        if len(bg)!=2 or len(set(bg))!=2 or any(n<1 or n>37 for n in bg):
            raise ValueError(f"invalid historical bonus numbers round {i+1}")
        if any(history[i,n-1] for n in bg):
            raise ValueError(f"bonus and main numbers overlap in round {i+1}")
        bonus[i,np.asarray(bg)-1]=1
        for j,grade in enumerate(GRADES[1:],1):
            amount=_prize_payout(row,grade)
            if amount is not None:
                payout[i,j]=float(amount)
    return bonus,payout


def _portfolio_from_string(value:str) -> list[tuple[int,...]]:
    t=[tuple(int(n) for n in s.split()) for s in value.split("|")]
    if len(t)!=5 or any(len(x)!=7 for x in t):
        raise ValueError("incomplete portfolio row")
    return t


def _period(records:list[dict], *, seed:int) -> dict:
    if not records:
        return {"valid":False,"rounds":0}
    if not all(r["candidate_complete"] and r["current_production_complete"] and r["baseline_complete"] for r in records):
        return {"valid":False,"rounds":len(records),"reason":"unavailable_published_payout"}
    n=len(records)
    cost=ROUND_COST_YEN*n
    cash=sum(r["candidate_payout_yen"] for r in records)
    incumbent=sum(r["current_production_payout_yen"] for r in records)
    baseline=sum(r["baseline_payout_yen"] for r in records)
    diffs=[r["candidate_payout_yen"]-r["current_production_payout_yen"] for r in records]
    positives=sorted((d for d in diffs if d>0),reverse=True)
    return {
        "valid":True,"rounds":n,"first_round":records[0]["round"],
        "last_round":records[-1]["round"],
        "purchase_cost_yen_per_arm":cost,
        "candidate_payout_yen":cash,
        "production_payout_yen":incumbent,
        "baseline_payout_yen":baseline,
        "candidate_roi":cash/cost,"production_roi":incumbent/cost,
        "baseline_roi":baseline/cost,
        "candidate_minus_production_yen":cash-incumbent,
        "candidate_minus_production_roi_points":(cash-incumbent)/cost*100,
        "candidate_net_yen":cash-cost,
        "candidate_better_payout_rounds":sum(d>0 for d in diffs),
        "candidate_worse_payout_rounds":sum(d<0 for d in diffs),
        "candidate_equal_payout_rounds":sum(d==0 for d in diffs),
        "candidate_delta_without_top_four_positive_wins_yen":sum(diffs)-sum(positives[:4]),
        "paired_cash_delta_signflip_exploratory":paired_signflip_yen(diffs,seed=seed),
        "candidate_mean_score":float(np.mean([r["candidate_score"] for r in records])),
        "production_mean_score":float(np.mean([r["current_production_score"] for r in records])),
    }


def run(
    *,csv_path:Path,champion_file:Path,source_report:Path|None,
    out_dir:Path,config:CashAgentConfig=CashAgentConfig(),
    matched_reps:int=32,verify_parity:bool=True,
) -> dict:
    # The base replay has its own prefix and Champion parity tests and
    # rebuilds all 2+ ranks. Every target v2 then uses its frozen ranking.
    base_dir=out_dir/"incumbent_approved_model"
    incumbent=run_incumbent(
        csv_path=csv_path,champion_file=champion_file,out_dir=base_dir,
        source_report=source_report,matched_reps=matched_reps,
        verify_parity=verify_parity,
    )
    hist,clean=make_history(read_csv_flexible(csv_path))
    if len(hist)!=incumbent["target_round_last"]:
        raise RuntimeError("historical source/replay length mismatch")
    bonus,payout=_source_tables(hist,clean)
    with (base_dir/"rounds_2_to_latest.csv").open(encoding="utf-8-sig",newline="") as f:
        frozen=list(csv.DictReader(f))
    if len(frozen)!=len(hist)-1:
        raise RuntimeError("missing incumbent chronological replay snapshots")
    output=[]
    tickets=[]
    for row in frozen:
        r=int(row["round"])
        t=r-1
        if r!=len(output)+2:
            raise AssertionError("nonconsecutive frozen rank snapshots")
        rank=[int(x) for x in row["rank_1_to_35"].split()]
        excluded=[int(x) for x in row["excluded_rank_36_37"].split()]
        if sorted(rank+excluded)!=list(range(1,38)):
            raise AssertionError("frozen rank order is not 37 labels")
        current=_portfolio_from_string(row["combo_tickets"])
        baseline=_portfolio_from_string(row["baseline_tickets"])
        if t>=100:
            # STRICT PREFIX: target t's result is not passed to training.
            proposed,details=candidate_from_cash_history(hist[:t],bonus[:t],payout[:t],
                                                         rank+excluded,config)
        else:
            proposed=baseline
            details={"swaps":0,"training_cash_objective_gain_yen_per_draw":0.0,
                     "stop_reason":"no_trained_cash_agent_before_round101"}
        if sorted(x for ticket in proposed for x in ticket)!=sorted(rank):
            raise AssertionError("cash-trained AI illegally changed Champion selected 35")
        import loto7_v2_runner as v2
        import loto7_v3_runner as v3
        actual=tuple(np.flatnonzero(hist[t])+1)
        bg=tuple(np.flatnonzero(bonus[t])+1)
        results={}
        for arm,ticket_set in (
            ("cash_v2",proposed),("production_v1",current),("rank_order",baseline)
        ):
            score=float(v3.row_score(v2._portfolio_metrics(ticket_set,set(actual))))
            metric=v2._portfolio_metrics(ticket_set,set(actual))
            total=0
            complete=True
            for i,ticket in enumerate(ticket_set,1):
                hit,bh,grade=grade_ticket(ticket,actual,bg)
                pay=_prize_payout(clean.iloc[t],grade)
                if pay is None:
                    complete=False
                else:
                    total+=pay
                tickets.append({
                    "round":r,"draw_date":row["draw_date"],
                    "arm":arm,"ticket":i,"predicted_numbers":_numbers(ticket),
                    "actual_main":_numbers(actual),"actual_bonus":_numbers(bg),
                    "main_hits":hit,"bonus_hits":bh,"grade":grade,
                    "public_payout_yen":pay if pay is not None else "unknown",
                    "prefix_sha256":row["source_prefix_sha256"],
                    "candidate_training_rows":t if arm=="cash_v2" and t>=100 else 0,
                })
            results[arm]={"payout":total,"complete":complete,
                          "score":score,"max_hits":metric["max_hits"]}
        output.append({
            "round":r,"draw_date":row["draw_date"],"training_rows":t,
            "phase":row["phase"],"prefix_sha256":row["source_prefix_sha256"],
            "rank_top35":row["rank_1_to_35"],"excluded_two":row["excluded_rank_36_37"],
            "candidate_tickets":"|".join(_numbers(p) for p in proposed),
            "candidate_swaps":details["swaps"],
            "candidate_training_gain_yen_per_draw":details["training_cash_objective_gain_yen_per_draw"],
            "candidate_training_status":details["stop_reason"],
            "current_production_tickets":row["combo_tickets"],
            "baseline_tickets":row["baseline_tickets"],
            **{
                f"{label}_{metric}":results[arm][source]
                for label,arm in (("candidate","cash_v2"),("current_production","production_v1"),("baseline","rank_order"))
                for metric,source in (("payout_yen","payout"),("complete","complete"),("score","score"),("max_hits","max_hits"))
            },
        })
        if results["production_v1"]["payout"]!=int(row["public_payout_yen"]):
            raise AssertionError(f"incumbent payout mismatch at round {r}")
        if results["rank_order"]["payout"]!=int(row["baseline_payout_yen"]):
            raise AssertionError(f"ranking payout mismatch at round {r}")

    # Refit with every known draw for *unissued* future research proposal.
    future_rank=incumbent["next_target_retrained_preview"]["top35_ranked_numbers"]
    future_excluded=incumbent["next_target_retrained_preview"]["excluded_numbers"]
    future,meta=candidate_from_cash_history(hist,bonus,payout,future_rank+future_excluded,config)
    periods={
        "all_round2_latest":_period(output,seed=80100),
        "trained_round101_latest":_period(output[99:],seed=80101),
        "locked_development_round101_450":_period([x for x in output if 101<=x["round"]<=450],seed=80102),
        "chronological_holdout_round451_latest":_period([x for x in output if x["round"]>=451],seed=80103),
        "last120":_period(output[-120:],seed=80104),
        "last60":_period(output[-60:],seed=80105),
        "last30":_period(output[-30:],seed=80106),
    }
    # Historic ROI improvement alone is not eligible for Production promotion.
    # Any future OOS must first register/freeze candidate and payout protocol.
    hold=periods["chronological_holdout_round451_latest"]
    recent=periods["last60"]
    train=periods["trained_round101_latest"]
    checks={
        "trained_roi_gt_incumbent":train.get("candidate_roi",0)>train.get("production_roi",0),
        "chronological_holdout_roi_gt_incumbent":hold.get("candidate_roi",0)>hold.get("production_roi",0),
        "recent_60_roi_gt_incumbent":recent.get("candidate_roi",0)>recent.get("production_roi",0),
        "chronological_holdout_tail_robust":hold.get("candidate_delta_without_top_four_positive_wins_yen",0)>0,
    }
    report={
        "version":VERSION,
        "candidate_version":CANDIDATE_VERSION,
        "candidate_config":asdict(config),
        "approved_production_model":COMBINATION_VERSION,
        "approved_champion":incumbent["model_version"],
        "source_sha256":fingerprint_file(csv_path),
        "source_trust":incumbent["source_validation"],
        "source_latest_draw_date":clean.iloc[-1]["抽せん日"].date().isoformat(),
        "first_round":2,"last_round":len(hist),"evaluated_rounds":len(output),
        "three_arm_ticket_rows":len(tickets),
        "periods":periods,
        "retrospective_roi_checks":checks,
        "retrospective_roi_all_checks_passed":all(checks.values()),
        "future_prospective_oos_draws_for_this_candidate":0,
        "future_roi_promotion_gate_met":False,
        "production_promotion":False,
        "promotion_reason":"no_candidate_specific_preregistered_future_roi_data",
        "next_target_retrained_unissued_preview":{
            "target_round":len(hist)+1,
            "top35":future_rank,
            "excluded_two":future_excluded,
            "candidate_tickets":[list(t) for t in future],
            "diagnostics":meta,
            "status":"research_only_not_published",
        },
        "production_ledger_modified":False,
        "champion_modified":False,
        "future_oos_modified":False,
        "limitations":[
            "The v2 algorithm and evaluation windows were developed after historical draws were available; even chronological replay is exploratory, not independent prospective evidence.",
            "All comparisons preserve Champion-selected top35, five disjoint tickets and same 1500 JPY hypothetical spend per draw.",
            "Historic payouts are retrospective hypothetical cashflows and not actual purchases.",
            "Under a fair 7-of-37 independent draw, changing the partition of fixed 35 labels does not improve ex-ante prize probabilities.",
            "Promotion requires candidate-specific locked future predictions, verified result source, same-cost positive ROI and independent review.",
        ],
    }
    out_dir.mkdir(parents=True,exist_ok=True)
    _write_csv(out_dir/"cash_v2_three_arm_rounds_2_to_latest.csv",output,ROUND_FIELDS)
    _write_csv(out_dir/"cash_v2_three_arm_tickets_2_to_latest.csv",tickets,TICKET_FIELDS)
    (out_dir/"roi_cash_v2_summary.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    lines=[
        "# ROI cash-trained v2: strict chronological replay from LOTO7 #2",
        "",
        f"- Last verified draw: **#{len(hist)} ({report['source_latest_draw_date']})**",
        f"- Champion: `{report['approved_champion']}`; source SHA-256: `{report['source_sha256']}`",
        "- Arms: new payout-trained v2; existing production pairwise v1; rank-order portfolio",
        "- Same Champion top35, same five nonoverlapping 7-number tickets, same hypothetical spend",
        "- Training uses only earlier published public draw prizes; payouts clipped to 6,000 yen for training, **not** when scoring actual cash",
        "- Round2-100 are untrained and identical between all arms",
        "",
        "| Period | Draws | Cash-v2 ROI | Production-v1 ROI | Rank-order ROI | Δ vs Production |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label,part in periods.items():
        if not part["valid"]:
            lines.append(f"| {label} | {part['rounds']} | 未評価 | 未評価 | 未評価 | 未評価 |")
            continue
        lines.append(
            f"| {label} | {part['rounds']} | {part['candidate_roi']*100:.2f}% | "
            f"{part['production_roi']*100:.2f}% | {part['baseline_roi']*100:.2f}% | "
            f"{part['candidate_minus_production_yen']:+,}円 |"
        )
    lines += ["","## Promotion audit","",
              "- All retrospective improvement checks: **"+str(all(checks.values()))+"**",
              "- Candidate-specific preregistered future verified draws: **0**",
              "- Production promotion: **BLOCKED**; historical replay is not future OOS",
              "- No issued predictions, approved Champion, or production policy changed",
              ""]
    (out_dir/"CASH_V2_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print("[ROI-CASH-V2] "+json.dumps({
        "source_rounds":len(hist),"report_version":VERSION,
        "candidate":CANDIDATE_VERSION,"periods":periods,
        "checks":checks,"promotion":False,"next_preview":report["next_target_retrained_unissued_preview"],
    },ensure_ascii=False,sort_keys=True))
    return report


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--csv",type=Path,default=Path("loto7.csv"))
    parser.add_argument("--champion",type=Path,default=Path("loto7_agent_output/model_champion.json"))
    parser.add_argument("--source-validation",type=Path,default=Path("loto7_agent_output/source_validation.json"))
    parser.add_argument("--out-dir",type=Path,default=Path("research/roi_cash_agent_v2_output"))
    parser.add_argument("--matched-reps",type=int,default=32)
    args=parser.parse_args()
    run(csv_path=args.csv,champion_file=args.champion,source_report=args.source_validation,
        out_dir=args.out_dir,matched_reps=args.matched_reps)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
