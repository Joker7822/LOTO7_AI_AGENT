"""Read-only chronological comparison using the existing v2 rank replay.

No future preview or research numbers are published by this extension.
Historical results are exploratory, not a prospective promotion gate.
"""
from __future__ import annotations
import argparse
import csv
import json
import hashlib
import random
from pathlib import Path
import numpy as np
from audit_ledger import grade_ticket
from balanced_uniform_portfolio import validate_portfolio
from first_prize_research import checked_source
from loto7_evolving_agent import make_history, read_csv_flexible
from research.roi_cash_agent_v2_replay import _source_tables, _portfolio_from_string
from research.roi_cash_robust_v3 import refine, VERSION, MIN_HISTORY
from research.production_combination_round2_replay import _prize_payout

def grade(tickets, actual, bonus, row):
    hits = []
    prizes = []
    for ticket in tickets:
        h, _, g = grade_ticket(ticket, actual, bonus)
        hits.append(h)
        prizes.append(_prize_payout(row, g))
    return {"cash":sum(prizes) if all(p is not None for p in prizes) else None,
            "max_hits":max(hits), "three_plus":int(max(hits)>=3),
            "four_plus":int(max(hits)>=4)}

def matched(ranking, target, count=32):
    for i in range(count):
        seed = int(hashlib.sha256(f"{VERSION}|{target}|{i}".encode()).hexdigest(), 16)
        arr = list(ranking[:35])
        random.Random(seed).shuffle(arr)
        yield [tuple(sorted(arr[j:j+7])) for j in range(0,35,7)]

def summarize(records):
    n=len(records)
    if not n:
        return {"rounds":0}
    names=("v3","v2","rank","matched32")
    complete=all(r[k]["cash"] is not None for r in records for k in names)
    metrics={}
    for k in names:
        sums=[r[k]["cash"] for r in records]
        total=sum(sums) if complete else None
        metrics[k]={"payout_yen":total,"roi":total/(1500*n) if complete else None,
                    "max_hits_mean":sum(r[k]["max_hits"] for r in records)/n,
                    "three_plus_rate":sum(r[k]["three_plus"] for r in records)/n,
                    "four_plus_rate":sum(r[k]["four_plus"] for r in records)/n}
    comparisons={}
    for k in names[1:]:
        delta=[r["v3"]["cash"]-r[k]["cash"] for r in records] if complete else []
        comparisons[k]={"delta_yen":sum(delta) if complete else None,
                       "delta_excluding_top_four_positive_yen":sum(delta)-sum(sorted((x for x in delta if x>0),reverse=True)[:4]) if complete else None,
                       "win_rate":sum(x>0 for x in delta)/n if complete else None}
    return {"rounds":n,"first_round":records[0]["round"],"last_round":records[-1]["round"],
            "complete_public_cash":complete,"arms":metrics,"comparisons":comparisons,
            "refined_rounds":sum(r["swaps"]>0 for r in records)}

def run(csv_path, source, base_dir):
    canonical, _, digest=checked_source(csv_path,source)
    h,clean=make_history(read_csv_flexible(csv_path))
    if len(h)!=len(canonical):
        raise ValueError("source length differs")
    b,p=_source_tables(h,clean)
    summary=json.loads((base_dir/"roi_cash_v2_summary.json").read_text())
    if summary["source_sha256"]!=digest or summary["last_round"]!=len(h):
        raise ValueError("v2 replay source mismatch")
    with (base_dir/"cash_v2_three_arm_rounds_2_to_latest.csv").open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=len(h)-1:
        raise ValueError("incomplete v2 rank snapshots")
    records=[]
    for i,row in enumerate(rows,2):
        if int(row["round"])!=i or int(row["training_rows"])!=i-1:
            raise ValueError("rank snapshot is not chronological")
        t=i-1
        if t<MIN_HISTORY:
            continue
        rank=[int(x) for x in (row["rank_top35"]+" "+row["excluded_two"]).split()]
        if sorted(rank)!=list(range(1,38)):
            raise ValueError("invalid ranking")
        v2=_portfolio_from_string(row["candidate_tickets"])
        baseline=_portfolio_from_string(row["baseline_tickets"])
        proposed,meta=refine(h[:t],b[:t],p[:t],rank)
        for portfolio in (v2,baseline,proposed):
            validate_portfolio(portfolio)
            if sorted(n for ticket in portfolio for n in ticket)!=sorted(rank[:35]):
                raise ValueError("unequal selected numbers")
        actual=tuple(np.flatnonzero(h[t])+1)
        bonus=tuple(np.flatnonzero(b[t])+1)
        results={k:grade(tickets,actual,bonus,clean.iloc[t])
                 for k,tickets in (("v3",proposed),("v2",v2),("rank",baseline))}
        controls=[grade(tickets,actual,bonus,clean.iloc[t]) for tickets in matched(rank,i)]
        results["matched32"]={k:sum(x[k] for x in controls)/len(controls)
                              if all(x[k] is not None for x in controls) else None
                              for k in ("cash","max_hits","three_plus","four_plus")}
        if results["v2"]["cash"] is not None and results["v2"]["cash"]!=int(row["candidate_payout_yen"]):
            raise ValueError("v2 grade mismatch")
        records.append({"round":i,"swaps":meta["swaps"],**results})
    return {"version":VERSION,"source_sha256":digest,"last_round":len(h),
            "periods":{"all_trained":summarize(records),
                       "round451_latest":summarize([r for r in records if r["round"]>=451]),
                       "last120":summarize(records[-120:]),"last60":summarize(records[-60:])},
            "records":records,"prospective_verified_rounds":0,"production_promotion":False,
            "limitations":"Exploratory historical replay. Equal 35 labels, five distinct tickets, no fair-draw advantage implied."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",type=Path,default=Path("loto7.csv"))
    ap.add_argument("--source",type=Path,default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--base-dir",type=Path,required=True)
    a=ap.parse_args()
    report=run(a.csv,a.source,a.base_dir)
    (a.base_dir/"robust_combination_v3_report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2,allow_nan=False))

if __name__=="__main__":
    main()
