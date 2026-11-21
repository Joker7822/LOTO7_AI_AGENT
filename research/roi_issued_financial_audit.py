#!/usr/bin/env python3
"""Read-only cashflow audit for ACTUALLY ISSUED Production forecasts.

Issued tickets are not purchase receipts. Cash figures are hypothetical unless
the user provides separately verified purchase evidence (not handled here).
Do not mix historical counterfactual replay with frozen issued predictions.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import audit_ledger as ledger
from production_disjoint35_policy import MIN_TARGET_ROUND, validate_issued_rows

VERSION="roi-issued-prediction-financial-audit-v1"


def _future_frozen(row: dict, actual: dict) -> bool:
    try:
        created=datetime.fromisoformat(row["prediction_created_at_jst"])
        draw=datetime.fromisoformat(str(actual["draw_date"])+"T00:00:00+09:00")
        if created.tzinfo is None:
            return False
        return created < draw
    except (ValueError, KeyError, TypeError):
        return False


def audit_issued(
    predictions: Path,
    corrections: Path,
    actual_results: Path,
) -> dict:
    issued=ledger.active_prediction_rows(predictions,corrections)
    actual=ledger.read_csv(actual_results)
    by_target=defaultdict(list)
    for row in issued:
        n=ledger.rno(row.get("target_round"))
        if n is None:
            raise ValueError("issued record missing target round")
        by_target[n].append(row)
    latest={}
    for row in actual:
        n=ledger.rno(row.get("round"))
        if n is None:
            raise ValueError("actual record missing round")
        latest[n]=row
    settled=[]
    future=[]
    unknown=[]
    summary=Counter()
    for target in sorted(by_target):
        group=sorted(by_target[target],key=lambda r:int(r.get("ticket") or 0))
        if len(group)!=5 or [int(r["ticket"]) for r in group]!=[1,2,3,4,5]:
            raise ValueError(f"incomplete active frozen Production five-ticket set at {target}")
        if target>=MIN_TARGET_ROUND:
            validate_issued_rows(group,target)
        if target not in latest:
            future.append(target)
            continue
        outcome=latest[target]
        main=ledger.nums(outcome.get("main_numbers"))
        bonus=ledger.nums(outcome.get("bonus_numbers"))
        if (len(main)!=7 or len(set(main))!=7 or len(bonus)!=2
                or set(main)&set(bonus)):
            raise ValueError(f"invalid settled draw outcome at {target}")
        amount=0
        grades=Counter()
        verified_before_draw=all(_future_frozen(r,outcome) for r in group)
        for forecast in group:
            ns=ledger.nums(forecast.get("predicted_numbers"))
            if len(ns)!=7 or len(set(ns))!=7:
                raise ValueError(f"invalid issued ticket at {target}")
            hits,bh,grade=ledger.grade_ticket(ns,main,bonus)
            prize=0 if grade=="はずれ" else ledger.money(outcome.get(f"{grade}当選金額",""))
            if prize is None:
                unknown.append({"round":target,"grade":grade,
                                "reason":"missing_public_prize_amount"})
            else:
                amount+=prize
            grades[grade]+=1
        summary.update(grades)
        settled.append({
            "round":target,
            "draw_date":outcome.get("draw_date"),
            "model_version":group[0].get("model_version",""),
            "source_verification":outcome.get("source_verification",""),
            "frozen_before_draw_verified":verified_before_draw,
            "ticket_count":5, "reference_cost_yen":1500,
            "reference_payout_yen":amount if not any(u["round"]==target for u in unknown) else None,
            "reference_net_yen":amount-1500 if not any(u["round"]==target for u in unknown) else None,
            "grades":dict(grades),
        })
    if unknown:
        status="incomplete_published_payouts"
    elif not settled:
        status="no_settled_issued_tickets"
    else:
        status="settled_issued_replay_only"
    complete = status=="settled_issued_replay_only"
    reference_cost=1500*len(settled)
    reference_payout=sum(r["reference_payout_yen"] for r in settled) if complete else None
    no_pre_draw_evidence=[r["round"] for r in settled if not r["frozen_before_draw_verified"]]
    return {
        "version":VERSION,"status":status,
        "scope":"frozen_issued_predictions_only_not_research_replay",
        "settled_rounds":len(settled),"unsettled_round_numbers":future,
        "unknown_public_prize_data":unknown,
        "reference_ticket_count":5*len(settled),
        "reference_cost_yen":reference_cost,
        "reference_payout_yen":reference_payout,
        "reference_profit_yen":reference_payout-reference_cost if complete else None,
        "reference_roi":reference_payout/reference_cost if complete and reference_cost else None,
        "historical_grade_counts":dict(summary),
        "no_verified_pre_draw_freeze_rounds":no_pre_draw_evidence,
        "strictly_prospective_rounds":[r["round"] for r in settled if r["frozen_before_draw_verified"]],
        "rounds":settled,
        "actual_purchase_receipts_verified":False,
        "realized_personal_cash_return":None,
        "production_ledger_modified":False,
        "future_oos_modified":False,
    }


def render(report:dict) -> str:
    roi=report["reference_roi"]
    lines=[
        "# 発行済み本番予測のみの回収率監査",
        "",
        f"- 判定：**{report['status']}**",
        f"- 照合済み抽せん回：**{report['settled_rounds']}回**",
        f"- 未抽せんの発行済み回：**{report['unsettled_round_numbers']}**",
        f"- 仮想購入額：**{report['reference_cost_yen']:,}円**",
        f"- 公表払戻の仮想合計：**{report['reference_payout_yen']:,}円**" if roi is not None else "- 公表払戻の仮想合計：**確認できません**",
        f"- 仮想回収率：**{100*roi:.2f}%**" if roi is not None else "- 仮想回収率：**確認できません**",
        "- これらは発行済み予測の事後照合であり、実際の購入や個人利益を示すものではありません。",
        f"- 抽せん前の凍結日時を確認できない回：**{len(report['no_verified_pre_draw_freeze_rounds'])}回**",
        "",
    ]
    return "\n".join(lines)


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",type=Path,default=Path("loto7_agent_output"))
    parser.add_argument("--report-dir",type=Path,default=Path("research/roi_issued_output"))
    args=parser.parse_args()
    result=audit_issued(
        args.out_dir/"predictions.csv",
        args.out_dir/"prediction_corrections.csv",
        args.out_dir/"actual_results.csv",
    )
    args.report_dir.mkdir(parents=True,exist_ok=True)
    (args.report_dir/"issued_roi_audit.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.report_dir/"issued_roi_audit.md").write_text(render(result),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="rounds"},ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
