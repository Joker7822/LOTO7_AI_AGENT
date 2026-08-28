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
CORRECTION_FIELDS = [
    "prediction_id","corrected_at_jst","action","reason","observed_data_sha256","expected_data_sha256"
]
LEGACY_HISTORY_FIELDS = [
    "prediction_created_at_jst","base_round","base_draw_date","target_round","target_draw_date_estimate",
    "ticket","predicted_numbers","status","actual_draw_date","actual_main_numbers","actual_bonus_numbers",
    "main_hits","bonus_hits","grade","prize_amount","checked_at_jst"
]


def now_jst() -> str:
    return dt.datetime.now(JST).isoformat(timespec="seconds")


def read_csv(path: Path) -> List[Dict[str,str]]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig","utf-8","cp932","shift_jis"):
        try:
            with path.open(encoding=enc,newline="") as f:
                return [{str(k):str(v or "").strip() for k,v in r.items()} for r in csv.DictReader(f)]
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"cannot decode {path}")


def append_csv(path: Path, rows: Iterable[Dict[str,str]], fields: List[str]) -> None:
    rows=list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    exists=path.exists() and path.stat().st_size>0
    with path.open("a",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k,"") for k in fields})


def write_csv(path: Path, rows: Iterable[Dict[str,str]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k,"") for k in fields})


def rno(v:str)->Optional[int]:
    m=re.search(r"\d+",str(v or ""))
    return int(m.group()) if m else None


def nums(v:str)->Tuple[int,...]:
    return tuple(int(x) for x in re.findall(r"\d+",str(v or "")))


def fmt(ns:Iterable[int])->str:
    return " ".join(f"{x:02d}" for x in sorted(ns))


def sha_text(s:str)->str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def money(v:str)->Optional[int]:
    m=re.search(r"([0-9,]+)\s*円",str(v or ""))
    return int(m.group(1).replace(",","")) if m else None


def grade_ticket(pred:Tuple[int,...], main:Tuple[int,...], bonus:Tuple[int,...])->Tuple[int,int,str]:
    mh=len(set(pred)&set(main))
    bh=len(set(pred)&set(bonus))
    if mh==7:g="1等"
    elif mh==6 and bh>=1:g="2等"
    elif mh==6:g="3等"
    elif mh==5:g="4等"
    elif mh==4:g="5等"
    elif mh==3 and bh>=1:g="6等"
    else:g="はずれ"
    return mh,bh,g


def invalidated_prediction_ids(corrections: Optional[Path]) -> set[str]:
    if corrections is None:
        return set()
    return {
        r.get("prediction_id","")
        for r in read_csv(corrections)
        if r.get("action")=="invalidate" and r.get("prediction_id")
    }


def active_prediction_rows(preds: Path, corrections: Optional[Path]=None) -> List[Dict[str,str]]:
    invalid=invalidated_prediction_ids(corrections)
    return [r for r in read_csv(preds) if r.get("prediction_id","") not in invalid]


def migrate_legacy(legacy:Path,preds:Path,state:Dict[str,object])->int:
    if preds.exists() or not legacy.exists():
        return 0
    out=[]
    for r in read_csv(legacy):
        target=r.get("target_round","")
        ticket=r.get("ticket","")
        pn=r.get("predicted_numbers","")
        pid=sha_text(f"{target}|{ticket}|{pn}|legacy")[:20]
        out.append({
            "prediction_id":pid,"prediction_created_at_jst":r.get("prediction_created_at_jst",""),"base_round":r.get("base_round",""),
            "base_draw_date":r.get("base_draw_date",""),"target_round":target,"target_draw_date_estimate":r.get("target_draw_date_estimate",""),
            "ticket":ticket,"predicted_numbers":pn,"model_version":"legacy-unknown",
            "git_sha":"","data_sha256":"","strategy_weights_json":"{}"
        })
    append_csv(preds,out,PRED_FIELDS)
    return len(out)


def append_prediction_invalidations(
    loto_rows: List[Dict[str,str]], preds: Path, corrections: Path, current_data_sha: str
) -> int:
    """Invalidate only provably stale non-legacy predictions; never delete frozen audit rows."""
    if not loto_rows:
        return 0
    latest=max(loto_rows,key=lambda r:rno(r.get("回別","")) or -1)
    latest_round=rno(latest.get("回別",""))
    if latest_round is None:
        return 0
    already=invalidated_prediction_ids(corrections)
    add=[]
    for p in read_csv(preds):
        pid=p.get("prediction_id","")
        if not pid or pid in already or p.get("model_version")=="legacy-unknown":
            continue
        if rno(p.get("base_round","")) != latest_round or rno(p.get("target_round","")) != latest_round+1:
            continue
        observed=p.get("data_sha256","")
        if observed and current_data_sha and observed != current_data_sha:
            add.append({
                "prediction_id":pid,
                "corrected_at_jst":now_jst(),
                "action":"invalidate",
                "reason":"base_round_current_but_data_sha_mismatch",
                "observed_data_sha256":observed,
                "expected_data_sha256":current_data_sha,
            })
    append_csv(corrections,add,CORRECTION_FIELDS)
    return len(add)


def _validated_ticket_rows(ticket_rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
    if len(ticket_rows)!=5:
        raise RuntimeError(f"expected exactly 5 Production tickets, got {len(ticket_rows)}")
    out=[]
    seen=set()
    for i,tr in enumerate(ticket_rows,1):
        ns=tuple(sorted(nums(tr.get("numbers",""))))
        if len(ns)!=7 or len(set(ns))!=7 or any(n<1 or n>37 for n in ns):
            raise RuntimeError(f"invalid Production ticket {i}: {tr.get('numbers','')}")
        ticket=str(tr.get("ticket") or i)
        if ticket in seen:
            raise RuntimeError(f"duplicate ticket id: {ticket}")
        seen.add(ticket)
        out.append({"ticket":ticket,"numbers":fmt(ns)})
    return out


def append_current_predictions(
    loto_rows, ticket_rows, preds:Path, state:Dict[str,object],
    current_data_sha: Optional[str]=None, corrections: Optional[Path]=None,
    created_at: Optional[str]=None
)->int:
    """Freeze a Production prediction. This is publisher-only; audit checkpoints must not call it."""
    if not loto_rows:
        raise RuntimeError("cannot freeze Production without LOTO7 history")
    latest=max(loto_rows,key=lambda r:rno(r.get("回別","")) or -1)
    base=rno(latest.get("回別",""))
    if base is None:
        raise RuntimeError("latest round is missing")
    target=base+1

    existing=[
        r for r in active_prediction_rows(preds,corrections)
        if rno(r.get("target_round",""))==target
    ]
    if existing:
        if len(existing)!=5:
            raise RuntimeError(f"frozen target 第{target}回 has {len(existing)} active tickets, expected 5")
        return 0

    if current_data_sha is not None and str(state.get("data_sha256","")) != current_data_sha:
        raise RuntimeError("refusing Production freeze: agent_state data SHA does not match loto7.csv")
    if rno(state.get("latest_round","")) != base:
        raise RuntimeError("refusing Production freeze: agent_state latest_round does not match loto7.csv")
    if rno(state.get("target_round","")) != target:
        raise RuntimeError("refusing Production freeze: agent_state target_round is not next draw")

    tickets=_validated_ticket_rows(list(ticket_rows))
    created=created_at or now_jst()
    est=""
    try:
        est=(dt.date.fromisoformat(latest.get("抽せん日",""))+dt.timedelta(days=7)).isoformat()
    except ValueError:
        pass
    weights=json.dumps(state.get("expert_weights",{}),ensure_ascii=False,sort_keys=True)
    rows=[]
    for tr in tickets:
        pn=tr["numbers"]
        ticket=tr["ticket"]
        pid=sha_text(f"{target}|{ticket}|{pn}|{created}")[:20]
        rows.append({
            "prediction_id":pid,"prediction_created_at_jst":created,
            "base_round":latest.get("回別",f"第{base}回"),"base_draw_date":latest.get("抽せん日",""),
            "target_round":f"第{target}回","target_draw_date_estimate":est,
            "ticket":ticket,"predicted_numbers":pn,
            "model_version":str(state.get("model_version","")),"git_sha":str(state.get("git_sha","")),
            "data_sha256":str(state.get("data_sha256","")),"strategy_weights_json":weights
        })
    append_csv(preds,rows,PRED_FIELDS)
    return len(rows)


def append_actual_snapshots(
    loto_rows,preds:Path,actuals:Path,source_report:Path,corrections:Optional[Path]=None
)->int:
    targets={rno(r.get("target_round","")) for r in active_prediction_rows(preds,corrections)}-{None}
    existing=read_csv(actuals)
    latest_by={}
    for r in existing:
        n=rno(r.get("round",""))
        latest_by[n]=r
    src={}
    if source_report.exists():
        try:
            src=json.loads(source_report.read_text(encoding="utf-8"))
        except Exception:
            src={}
    sr_sha=hashlib.sha256(source_report.read_bytes()).hexdigest() if source_report.exists() else ""
    add=[]
    for row in loto_rows:
        n=rno(row.get("回別",""))
        if n not in targets:
            continue
        main=fmt(nums(row.get("本数字","")))
        bonus=fmt(nums(row.get("ボーナス数字","")))
        if len(nums(main))!=7 or len(nums(bonus))!=2:
            continue
        payload={
            "round":f"第{n}回","draw_date":row.get("抽せん日",""),
            "main_numbers":main,"bonus_numbers":bonus,
            **{f"{i}等当選金額":row.get(f"{i}等当選金額","") for i in range(1,7)},
            "carryover":row.get("キャリーオーバー","")
        }
        signature=sha_text(json.dumps(payload,ensure_ascii=False,sort_keys=True))[:20]
        if latest_by.get(n,{}).get("result_id")==signature:
            continue
        try:
            source_round=int((src.get("latest") or {}).get("round"))
        except (TypeError,ValueError,AttributeError):
            source_round=None
        if n==source_round:
            provenance={
                "source_verification":str(src.get("verification","unknown")),
                "source_status":str(src.get("status","unknown")),
                "source_report_sha256":sr_sha
            }
        else:
            provenance={
                "source_verification":"historical_csv_not_cross_validated_this_run",
                "source_status":"historical","source_report_sha256":""
            }
        payload.update({"result_id":signature,"recorded_at_jst":now_jst(),**provenance})
        add.append(payload)
        latest_by[n]=payload
    append_csv(actuals,add,ACTUAL_FIELDS)
    return len(add)


def reconcile(
    preds:Path,actuals:Path,recon:Path,corrections:Optional[Path]=None
)->List[Dict[str,str]]:
    ps=active_prediction_rows(preds,corrections)
    aa=read_csv(actuals)
    latest={}
    for a in aa:
        n=rno(a.get("round",""))
        latest[n]=a
    rows=[]
    for p in ps:
        n=rno(p.get("target_round",""))
        a=latest.get(n)
        if not a:
            continue
        pred=nums(p.get("predicted_numbers",""))
        main=nums(a.get("main_numbers",""))
        bonus=nums(a.get("bonus_numbers",""))
        if len(pred)!=7 or len(main)!=7 or len(bonus)!=2:
            continue
        mh,bh,g=grade_ticket(pred,main,bonus)
        amount="0円" if g=="はずれ" else a.get(f"{g}当選金額","") or "確認できません"
        val=money(amount)
        cost=300
        rows.append({
            "target_round":p.get("target_round",""),"ticket":p.get("ticket",""),
            "predicted_numbers":p.get("predicted_numbers",""),"actual_draw_date":a.get("draw_date",""),
            "actual_main_numbers":a.get("main_numbers",""),"actual_bonus_numbers":a.get("bonus_numbers",""),
            "main_hits":str(mh),"bonus_hits":str(bh),"grade":g,"prize_amount":amount,
            "purchase_cost":f"{cost}円",
            "net_result":f"{val-cost}円" if val is not None else "確認できません",
            "model_version":p.get("model_version",""),"prediction_id":p.get("prediction_id",""),
            "result_id":a.get("result_id","")
        })
    write_csv(recon,rows,RECON_FIELDS)
    return rows


def render_latest(
    preds:Path,corrections:Optional[Path]=None,latest_actual_round:Optional[int]=None
)->str:
    ps=active_prediction_rows(preds,corrections)
    if latest_actual_round is not None:
        ps=[p for p in ps if (rno(p.get("target_round","")) or -1)>latest_actual_round]
    if not ps:
        next_round=(latest_actual_round+1) if latest_actual_round is not None else None
        lines=["LOTO7 最新予測","="*56]
        if next_round is not None:
            lines.append(f"対象回: 第{next_round}回")
        lines += ["Production: 未発行","発行予定: 金曜15:00 JST",""]
        return "\n".join(lines)
    target=max(rno(p.get("target_round","")) or -1 for p in ps)
    rr=sorted(
        [p for p in ps if rno(p.get("target_round",""))==target],
        key=lambda r:int(r.get("ticket") or 999)
    )
    f=rr[0]
    lines=[
        "LOTO7 最新予測","="*56,f"対象回: 第{target}回",
        f"予測基準: {f.get('base_round','')} / {f.get('base_draw_date','')}",
        f"予測作成(JST): {f.get('prediction_created_at_jst','')}",
        f"モデル: {f.get('model_version','')}",""
    ]
    lines += [f"{r.get('ticket','')}. {r.get('predicted_numbers','')}" for r in rr]
    return "\n".join(lines)+"\n"


def render_results(
    preds:Path,actuals:Path,recon_rows:List[Dict[str,str]],corrections:Optional[Path]=None
)->str:
    ps=active_prediction_rows(preds,corrections)
    by_t={}
    rec_by={}
    for p in ps:
        by_t.setdefault(rno(p.get("target_round","")),[]).append(p)
    for r in recon_rows:
        rec_by[(rno(r.get("target_round","")),r.get("ticket",""))]=r
    total_cost=0
    total_win=0
    unknown=False
    wins=0
    lines=["LOTO7 予測・当選照合 累積レポート",f"更新日時(JST): {now_jst()}","="*80,""]
    for t in sorted([x for x in by_t if x is not None],reverse=True):
        rr=sorted(by_t[t],key=lambda r:int(r.get("ticket") or 999))
        lines += [f"[第{t}回]",f"予測基準: {rr[0].get('base_round','')} / {rr[0].get('base_draw_date','')}","-"*80]
        for p in rr:
            r=rec_by.get((t,p.get("ticket","")))
            if not r:
                lines.append(f"予測{p.get('ticket')}: {p.get('predicted_numbers')} | 判定待ち")
                continue
            total_cost+=300
            val=money(r.get("prize_amount",""))
            if val is None:
                unknown=True
            else:
                total_win+=val
            if r.get("grade")!="はずれ":
                wins+=1
            lines.append(
                f"予測{p.get('ticket')}: {p.get('predicted_numbers')} | "
                f"本{r.get('main_hits')} B{r.get('bonus_hits')} | {r.get('grade')} | {r.get('prize_amount')}"
            )
        lines.append("")
    roi=(total_win/total_cost*100) if total_cost else 0.0
    lines += [
        "="*80,f"照合済み購入額: {total_cost:,}円",f"確認済み当選額: {total_win:,}円",
        f"差引: {total_win-total_cost:,}円",
        f"回収率: {roi:.2f}%" if not unknown else f"回収率(確認済み分): {roi:.2f}%",
        f"当選口数: {wins}","",
        "※ predictions.csv / actual_results.csv はappend-only、prediction_corrections.csvは無効化イベント台帳です。"
    ]
    return "\n".join(lines)+"\n"


def write_prediction_history_view(
    history:Path,preds:Path,recon_rows:List[Dict[str,str]],corrections:Optional[Path]=None
)->None:
    ps=active_prediction_rows(preds,corrections)
    rec_by={(r.get("prediction_id","")):r for r in recon_rows}
    generated=now_jst()
    rows=[]
    for p in ps:
        r=rec_by.get(p.get("prediction_id",""))
        checked=r is not None
        rows.append({
            "prediction_created_at_jst":p.get("prediction_created_at_jst",""),
            "base_round":p.get("base_round",""),"base_draw_date":p.get("base_draw_date",""),
            "target_round":p.get("target_round",""),"target_draw_date_estimate":p.get("target_draw_date_estimate",""),
            "ticket":p.get("ticket",""),"predicted_numbers":p.get("predicted_numbers",""),
            "status":"checked" if checked else "pending",
            "actual_draw_date":r.get("actual_draw_date","") if r else "",
            "actual_main_numbers":r.get("actual_main_numbers","") if r else "",
            "actual_bonus_numbers":r.get("actual_bonus_numbers","") if r else "",
            "main_hits":r.get("main_hits","") if r else "",
            "bonus_hits":r.get("bonus_hits","") if r else "",
            "grade":r.get("grade","") if r else "",
            "prize_amount":r.get("prize_amount","") if r else "",
            "checked_at_jst":generated if checked else "",
        })
    write_csv(history,rows,LEGACY_HISTORY_FIELDS)


def render_status(
    loto_rows,preds:Path,recon_rows,state:Dict[str,object],source:Dict[str,object],
    corrections:Optional[Path]=None
)->str:
    latest=max(loto_rows,key=lambda r:rno(r.get("回別","")) or -1)
    latest_no=rno(latest.get("回別","")) or -1
    ps=active_prediction_rows(preds,corrections)
    pending_rows=[p for p in ps if (rno(p.get("target_round","")) or -1)>latest_no]
    target=max([rno(p.get("target_round","")) or -1 for p in pending_rows],default=latest_no+1)
    checked={(r.get("prediction_id","")) for r in recon_rows}
    pending=sum(1 for p in pending_rows if p.get("prediction_id","") not in checked)
    publish_state="発行済み" if pending_rows else "未発行"
    return f"""# LOTO7 AI Agent Status

- 更新日時 (JST): **{now_jst()}**
- 最新取得回: **{latest.get('回別','')} / {latest.get('抽せん日','')}**
- 最新Production対象: **第{target}回（{publish_state}）**
- 未照合予測: **{pending}口**
- モデル: **{state.get('model_version','確認できません')}**
- データSHA256: `{state.get('data_sha256','')}`
- ソース検証: **{source.get('verification',source.get('status','確認できません'))}**
- 取得状態: **{source.get('status','確認できません')}**

> Productionの凍結は金曜15:00 JST publisherのみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。
"""


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--loto-csv",type=Path,default=Path("loto7.csv"))
    ap.add_argument("--tickets-csv",type=Path,default=Path("loto7_agent_output/candidate_tickets.csv"))
    ap.add_argument("--out-dir",type=Path,default=Path("loto7_agent_output"))
    ap.add_argument("--status-md",type=Path,default=Path("STATUS.md"))
    args=ap.parse_args()

    out=args.out_dir
    state={}
    source={}
    sp=out/"agent_state.json"
    sr=out/"source_validation.json"
    if sp.exists():
        state=json.loads(sp.read_text(encoding="utf-8"))
    if sr.exists():
        source=json.loads(sr.read_text(encoding="utf-8"))

    preds=out/"predictions.csv"
    actuals=out/"actual_results.csv"
    recon=out/"reconciliation.csv"
    corrections=out/"prediction_corrections.csv"
    history=out/"prediction_history.csv"

    migrate_legacy(history,preds,state)
    loto=read_csv(args.loto_csv)
    current_sha=sha_file(args.loto_csv)
    invalidated=append_prediction_invalidations(loto,preds,corrections,current_sha)

    if not actuals.exists():
        write_csv(actuals,[],ACTUAL_FIELDS)
    append_actual_snapshots(loto,preds,actuals,sr,corrections)
    rec=reconcile(preds,actuals,recon,corrections)
    write_prediction_history_view(history,preds,rec,corrections)

    latest_actual=max((rno(r.get("回別","")) or -1 for r in loto),default=-1)
    (out/"latest_prediction.txt").write_text(
        render_latest(preds,corrections,latest_actual),encoding="utf-8"
    )
    (out/"prediction_results.txt").write_text(
        render_results(preds,actuals,rec,corrections),encoding="utf-8"
    )
    args.status_md.write_text(
        render_status(loto,preds,rec,state,source,corrections),encoding="utf-8"
    )
    print(
        f"[AUDIT] active_predictions={len(active_prediction_rows(preds,corrections))} "
        f"invalidated_now={invalidated} actual_snapshots={len(read_csv(actuals))} reconciled={len(rec)}"
    )
    return 0


if __name__=="__main__":
    raise SystemExit(main())
