"""Historical v4 audit on the same chronological rank and v3 replay snapshots."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from first_prize_research import checked_source
from loto7_evolving_agent import make_history,read_csv_flexible
from research.roi_cash_agent_v2_replay import _source_tables,_portfolio_from_string
from research.roi_cash_robust_v3 import refine,MIN_HISTORY
from research.roi_cash_robust_v3_replay import grade
from research.roi_cash_cooccurrence_v4 import refine_cooccurrence,VERSION

ARMS=("v4","v3","v2","rank","matched32")


def summarize(records):
    if not records:
        return {"rounds":0}
    n=len(records)
    complete=all(r[k]["cash"] is not None for r in records for k in ARMS)
    arms={}
    for k in ARMS:
        cash=sum(r[k]["cash"] for r in records) if complete else None
        arms[k]={"payout_yen":cash,"roi":cash/(1500*n) if complete else None,
                 "three_plus_rate":sum(r[k]["three_plus"] for r in records)/n,
                 "four_plus_rate":sum(r[k]["four_plus"] for r in records)/n,
                 "max_hits_mean":sum(r[k]["max_hits"] for r in records)/n}
    paired={}
    for k in ARMS[1:]:
        d=[r["v4"]["cash"]-r[k]["cash"] for r in records] if complete else []
        paired[k]={"delta_yen":sum(d) if complete else None,
                   "without_top_four_positive_yen":sum(d)-sum(sorted((x for x in d if x>0),reverse=True)[:4]) if complete else None,
                   "win_rate":sum(x>0 for x in d)/n if complete else None}
    return {"rounds":n,"first_round":records[0]["round"],"last_round":records[-1]["round"],
            "complete_cash":complete,"arms":arms,"paired":paired,
            "modified_rounds":sum(r["v4_swaps"]>0 for r in records)}


def run(csv_path,source,base_dir):
    canonical,_,digest=checked_source(csv_path,source)
    h,clean=make_history(read_csv_flexible(csv_path))
    b,p=_source_tables(h,clean)
    report=json.loads((base_dir/"robust_combination_v3_report.json").read_text())
    if len(h)!=len(canonical) or report["source_sha256"]!=digest or report["last_round"]!=len(h):
        raise ValueError("v3 source mismatch")
    prior=report["records"]
    if len(prior)!=len(h)-MIN_HISTORY:
        raise ValueError("incomplete v3 records")
    with (base_dir/"cash_v2_three_arm_rounds_2_to_latest.csv").open(encoding="utf-8-sig",newline="") as f:
        ranks=list(csv.DictReader(f))
    if len(ranks)!=len(h)-1:
        raise ValueError("incomplete ranked prefix snapshots")
    records=[]
    for row,old in zip(ranks[MIN_HISTORY-1:],prior,strict=True):
        i=int(row["round"])
        t=i-1
        if i!=MIN_HISTORY+1+len(records) or i!=old["round"] or t!=int(row["training_rows"]):
            raise ValueError("nonchronological replay")
        rank=[int(x) for x in (row["rank_top35"]+" "+row["excluded_two"]).split()]
        if sorted(rank)!=list(range(1,38)):
            raise ValueError("invalid ranking")
        start,_=refine(h[:t],b[:t],p[:t],rank)
        proposed,meta=refine_cooccurrence(h[:t],b[:t],p[:t],rank,start=start)
        actual=tuple(np.flatnonzero(h[t])+1)
        bonus=tuple(np.flatnonzero(b[t])+1)
        if grade(start,actual,bonus,clean.iloc[t])!=old["v3"]:
            raise ValueError("v3 refit disagrees with previous replay")
        result=grade(proposed,actual,bonus,clean.iloc[t])
        records.append({"round":i,"v4_swaps":meta["swaps"],"v4":result,
                        **{k:old[k] for k in ARMS[1:]}})
    return {"version":VERSION,"source_sha256":digest,"last_round":len(h),
            "periods":{"all_trained":summarize(records),
                       "round451_latest":summarize([r for r in records if r["round"]>=451]),
                       "last120":summarize(records[-120:]),"last60":summarize(records[-60:])},
            "records":records,"prospective_verified_rounds":0,"production_promotion":False,
            "limitations":"Exploratory retrospective comparison; no proven predictive edge."}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",type=Path,default=Path("loto7.csv"))
    ap.add_argument("--source",type=Path,default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--base-dir",type=Path,required=True)
    a=ap.parse_args()
    report=run(a.csv,a.source,a.base_dir)
    (a.base_dir/"cooccurrence_v4_report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2,allow_nan=False))


if __name__=="__main__":
    main()
