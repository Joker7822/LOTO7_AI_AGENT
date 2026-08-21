#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

JST = dt.timezone(dt.timedelta(hours=9))
PRED_FIELDS = [
    "prediction_id","prediction_created_at_jst","base_round","base_draw_date","target_round","target_draw_date_estimate",
    "ticket","predicted_numbers","model_version","git_sha","data_sha256","strategy_weights_json"
]
ACTUAL_FIELDS = [
    "result_id","recorded_at_jst","round","draw_date","main_numbers","bonus_numbers",
    "1等当選金額","2等当選金額","3等当選金額","4等当選金額","5等当選金額","6等当選金額",
    "carryover","source_verification","source_status","source_report_sha256"
]
RECON_FIELDS = [
    "target_round","ticket","predicted_numbers","actual_draw_date","actual_main_numbers","actual_bonus_numbers",
    "main_hits","bonus_hits","grade","prize_amount","purchase_cost","net_result","model_version","prediction_id","result_id"
]


def now_jst() -> str:
    return dt.datetime.now(JST).isoformat(timespec="seconds")


def read_csv(path: Path) -> List[Dict[str,str]]:
    if not path.exists(): return []
    for enc in ("utf-8-sig","utf-8","cp932","shift_jis"):
        try:
            with path.open(encoding=enc,newline="") as f:
                return [{str(k):str(v or "").strip() for k,v in r.items()} for r in csv.DictReader(f)]
        except UnicodeDecodeError: pass
    raise RuntimeError(f"cannot decode {path}")


def append_csv(path: Path, rows: Iterable[Dict[str,str]], fields: List[str]) -> None:
    rows=list(rows)
    if not rows: return
    path.parent.mkdir(parents=True,exist_ok=True)
    exists=path.exists() and path.stat().st_size>0
    with path.open("a",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        if not exists: w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})


def write_csv(path: Path, rows: Iterable[Dict[str,str]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})


def rno(v:str)->Optional[int]:
    m=re.search(r"\d+",str(v or "")); return int(m.group()) if m else None


def nums(v:str)->Tuple[int,...]: return tuple(int(x) for x in re.findall(r"\d+",str(v or "")))
def fmt(ns:Iterable[int])->str: return " ".join(f"{x:02d}" for x in sorted(ns))
def sha_text(s:str)->str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def money(v:str)->Optional[int]:
    m=re.search(r"([0-9,]+)\s*円",str(v or "")); return int(m.group(1).replace(",","")) if m else None


def grade_ticket(pred:Tuple[int,...], main:Tuple[int,...], bonus:Tuple[int,...])->Tuple[int,int,str]:
    mh=len(set(pred)&set(main)); bh=len(set(pred)&set(bonus))
    if mh==7:g="1等"
    elif mh==6 and bh>=1:g="2等"
    elif mh==6:g="3等"
    elif mh==5:g="4等"
    elif mh==4:g="5等"
    elif mh==3 and bh>=1:g="6等"
    else:g="はずれ"
    return mh,bh,g


def migrate_legacy(legacy:Path,preds:Path,state:Dict[str,object])->int:
    if preds.exists() or not legacy.exists(): return 0
    out=[]
    for r in read_csv(legacy):
        target=r.get("target_round",""); ticket=r.get("ticket",""); pn=r.get("predicted_numbers","")
        pid=sha_text(f"{target}|{ticket}|{pn}|legacy")[:20]
        out.append({
            "prediction_id":pid,"prediction_created_at_jst":r.get("prediction_created_at_jst",""),"base_round":r.get("base_round",""),
            "base_draw_date":r.get("base_draw_date",""),"target_round":target,"target_draw_date_estimate":r.get("target_draw_date_estimate",""),
            "ticket":ticket,"predicted_numbers":pn,"model_version":"legacy-unknown",
            "git_sha":"","data_sha256":"","strategy_weights_json":"{}"
        })
    append_csv(preds,out,PRED_FIELDS); return len(out)


def append_current_predictions(loto_rows,ticket_rows,preds:Path,state:Dict[str,object])->int:
    latest=max(loto_rows,key=lambda r:rno(r.get("回別","")) or -1)
    base=rno(latest.get("回別","")); target=(base or 0)+1
    existing=read_csv(preds)
    if any(rno(r.get("target_round",""))==target for r in existing): return 0
    created=now_jst(); est=""
    try: est=(dt.date.fromisoformat(latest.get("抽せん日",""))+dt.timedelta(days=7)).isoformat()
    except ValueError: pass
    weights=json.dumps(state.get("expert_weights",{}),ensure_ascii=False,sort_keys=True)
    rows=[]
    for tr in ticket_rows:
        pn=fmt(nums(tr.get("numbers",""))); ticket=tr.get("ticket",str(len(rows)+1))
        pid=sha_text(f"{target}|{ticket}|{pn}|{created}")[:20]
        rows.append({"prediction_id":pid,"prediction_created_at_jst":created,"base_round":latest.get("回別",f"第{base}回"),
            "base_draw_date":latest.get("抽せん日",""),"target_round":f"第{target}回","target_draw_date_estimate":est,"ticket":ticket,
            "predicted_numbers":pn,"model_version":str(state.get("model_version","")),"git_sha":str(state.get("git_sha","")),
            "data_sha256":str(state.get("data_sha256","")),"strategy_weights_json":weights})
    append_csv(preds,rows,PRED_FIELDS); return len(rows)


def append_actual_snapshots(loto_rows,preds:Path,actuals:Path,source_report:Path)->int:
    targets={rno(r.get("target_round","")) for r in read_csv(preds)}-{None}
    existing=read_csv(actuals); latest_by={}
    for r in existing:
        n=rno(r.get("round","")); latest_by[n]=r
    src={}
    if source_report.exists():
        try: src=json.loads(source_report.read_text(encoding="utf-8"))
        except Exception: src={}
    sr_sha=hashlib.sha256(source_report.read_bytes()).hexdigest() if source_report.exists() else ""
    add=[]
    for row in loto_rows:
        n=rno(row.get("回別",""))
        if n not in targets: continue
        main=fmt(nums(row.get("本数字",""))); bonus=fmt(nums(row.get("ボーナス数字","")))
        if len(nums(main))!=7 or len(nums(bonus))!=2: continue
        payload={"round":f"第{n}回","draw_date":row.get("抽せん日",""),"main_numbers":main,"bonus_numbers":bonus,
            **{f"{i}等当選金額":row.get(f"{i}等当選金額","") for i in range(1,7)},"carryover":row.get("キャリーオーバー","")}
        signature=sha_text(json.dumps(payload,ensure_ascii=False,sort_keys=True))[:20]
        if latest_by.get(n,{}).get("result_id")==signature: continue
        try:
            source_round = int((src.get("latest") or {}).get("round"))
        except (TypeError, ValueError, AttributeError):
            source_round = None
        if n == source_round:
            provenance = {"source_verification":str(src.get("verification","unknown")),
                "source_status":str(src.get("status","unknown")),"source_report_sha256":sr_sha}
        else:
            provenance = {"source_verification":"historical_csv_not_cross_validated_this_run",
                "source_status":"historical","source_report_sha256":""}
        payload.update({"result_id":signature,"recorded_at_jst":now_jst(),**provenance})
        add.append(payload); latest_by[n]=payload
    append_csv(actuals,add,ACTUAL_FIELDS); return len(add)


def reconcile(preds:Path,actuals:Path,recon:Path)->List[Dict[str,str]]:
    ps=read_csv(preds); aa=read_csv(actuals); latest={}
    for a in aa:
        n=rno(a.get("round","")); latest[n]=a
    rows=[]
    for p in ps:
        n=rno(p.get("target_round","")); a=latest.get(n)
        if not a: continue
        pred=nums(p.get("predicted_numbers","")); main=nums(a.get("main_numbers","")); bonus=nums(a.get("bonus_numbers",""))
        if len(pred)!=7 or len(main)!=7 or len(bonus)!=2: continue
        mh,bh,g=grade_ticket(pred,main,bonus)
        amount="0円" if g=="はずれ" else a.get(f"{g}当選金額","") or "確認できません"
        val=money(amount); cost=300
        rows.append({"target_round":p.get("target_round",""),"ticket":p.get("ticket",""),"predicted_numbers":p.get("predicted_numbers",""),
            "actual_draw_date":a.get("draw_date",""),"actual_main_numbers":a.get("main_numbers",""),"actual_bonus_numbers":a.get("bonus_numbers",""),
            "main_hits":str(mh),"bonus_hits":str(bh),"grade":g,"prize_amount":amount,"purchase_cost":f"{cost}円",
            "net_result":f"{val-cost}円" if val is not None else "確認できません","model_version":p.get("model_version",""),
            "prediction_id":p.get("prediction_id",""),"result_id":a.get("result_id","")})
    write_csv(recon,rows,RECON_FIELDS); return rows


def render_latest(preds:Path)->str:
    ps=read_csv(preds)
    if not ps:return "LOTO7 最新予測\n予測履歴がありません。\n"
    target=max(rno(p.get("target_round","")) or -1 for p in ps); rr=sorted([p for p in ps if rno(p.get("target_round",""))==target],key=lambda r:int(r.get("ticket") or 999))
    f=rr[0]; lines=["LOTO7 最新予測","="*56,f"対象回: 第{target}回",f"予測基準: {f.get('base_round','')} / {f.get('base_draw_date','')}",f"予測作成(JST): {f.get('prediction_created_at_jst','')}",f"モデル: {f.get('model_version','')}",""]
    lines += [f"{r.get('ticket','')}. {r.get('predicted_numbers','')}" for r in rr]
    return "\n".join(lines)+"\n"


def render_results(preds:Path,actuals:Path,recon_rows:List[Dict[str,str]])->str:
    ps=read_csv(preds); by_t={}; rec_by={}
    for p in ps: by_t.setdefault(rno(p.get("target_round","")),[]).append(p)
    for r in recon_rows: rec_by[(rno(r.get("target_round","")),r.get("ticket",""))]=r
    total_cost=0; total_win=0; unknown=False; wins=0
    lines=["LOTO7 予測・当選照合 累積レポート",f"更新日時(JST): {now_jst()}","="*80,""]
    for t in sorted([x for x in by_t if x is not None],reverse=True):
        rr=sorted(by_t[t],key=lambda r:int(r.get("ticket") or 999)); lines += [f"[第{t}回]",f"予測基準: {rr[0].get('base_round','')} / {rr[0].get('base_draw_date','')}","-"*80]
        for p in rr:
            r=rec_by.get((t,p.get("ticket","")))
            if not r: lines.append(f"予測{p.get('ticket')}: {p.get('predicted_numbers')} | 判定待ち"); continue
            total_cost+=300; val=money(r.get("prize_amount",""));
            if val is None: unknown=True
            else: total_win+=val
            if r.get("grade")!="はずれ": wins+=1
            lines.append(f"予測{p.get('ticket')}: {p.get('predicted_numbers')} | 本{r.get('main_hits')} B{r.get('bonus_hits')} | {r.get('grade')} | {r.get('prize_amount')}")
        lines.append("")
    roi=(total_win/total_cost*100) if total_cost else 0.0
    lines += ["="*80,f"照合済み購入額: {total_cost:,}円",f"確認済み当選額: {total_win:,}円",f"差引: {total_win-total_cost:,}円",f"回収率: {roi:.2f}%" if not unknown else f"回収率(確認済み分): {roi:.2f}%",f"当選口数: {wins}","", "※ 予測と実績は別のappend-only台帳に保存し、このファイルは毎回再生成します。"]
    return "\n".join(lines)+"\n"


def render_status(loto_rows,preds:Path,recon_rows,state:Dict[str,object],source:Dict[str,object])->str:
    latest=max(loto_rows,key=lambda r:rno(r.get("回別","")) or -1); ps=read_csv(preds)
    target=max([rno(p.get("target_round","")) or -1 for p in ps],default=-1)
    checked={ (rno(r.get("target_round","")),r.get("ticket","")) for r in recon_rows }
    pending=sum(1 for p in ps if (rno(p.get("target_round","")),p.get("ticket","")) not in checked)
    return f"""# LOTO7 AI Agent Status

- 更新日時 (JST): **{now_jst()}**
- 最新取得回: **{latest.get('回別','')} / {latest.get('抽せん日','')}**
- 最新予測対象: **第{target}回**
- 未照合予測: **{pending}口**
- モデル: **{state.get('model_version','確認できません')}**
- データSHA256: `{state.get('data_sha256','')}`
- ソース検証: **{source.get('verification',source.get('status','確認できません'))}**
- 取得状態: **{source.get('status','確認できません')}**

> `degraded_single_result_source` の場合、楽天の結果は取得済みですが、みずほ銀行側の同一回結果を機械解析できていません。不一致が検出された場合は処理を停止します。
"""


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--loto-csv",type=Path,default=Path("loto7.csv")); ap.add_argument("--tickets-csv",type=Path,default=Path("loto7_agent_output/candidate_tickets.csv")); ap.add_argument("--out-dir",type=Path,default=Path("loto7_agent_output")); ap.add_argument("--status-md",type=Path,default=Path("STATUS.md")); args=ap.parse_args()
    out=args.out_dir; state={}; source={}
    sp=out/"agent_state.json"; sr=out/"source_validation.json"
    if sp.exists(): state=json.loads(sp.read_text(encoding="utf-8"))
    if sr.exists(): source=json.loads(sr.read_text(encoding="utf-8"))
    preds=out/"predictions.csv"; actuals=out/"actual_results.csv"; recon=out/"reconciliation.csv"
    migrate_legacy(out/"prediction_history.csv",preds,state)
    loto=read_csv(args.loto_csv); tickets=read_csv(args.tickets_csv)
    append_current_predictions(loto,tickets,preds,state)
    if not actuals.exists():
        write_csv(actuals, [], ACTUAL_FIELDS)
    append_actual_snapshots(loto,preds,actuals,sr)
    rec=reconcile(preds,actuals,recon)
    (out/"latest_prediction.txt").write_text(render_latest(preds),encoding="utf-8")
    (out/"prediction_results.txt").write_text(render_results(preds,actuals,rec),encoding="utf-8")
    args.status_md.write_text(render_status(loto,preds,rec,state,source),encoding="utf-8")
    print(f"[AUDIT] predictions={len(read_csv(preds))} actual_snapshots={len(read_csv(actuals))} reconciled={len(rec)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
