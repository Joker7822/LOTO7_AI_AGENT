#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from audit_ledger import grade_ticket

REPORT_VERSION = "historical-reconciliation-v1"
PURCHASE_COST_YEN = 300
FIELDS = [
    "base_round", "base_draw_date", "target_round", "target_draw_date", "training_rows",
    "ticket", "predicted_numbers", "actual_main_numbers", "actual_bonus_numbers",
    "main_hits", "bonus_hits", "grade", "published_prize_amount",
    "published_prize_yen", "purchase_cost_yen", "reference_net_yen",
    "settlement_status", "source_consistency",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return [{str(k): str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"cannot decode {path}")


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_round(value: object) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def parse_nums(value: object) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(value or "")))


def fmt_nums(values: Iterable[int]) -> str:
    return " ".join(f"{int(v):02d}" for v in sorted(values))


def parse_money_yen(value: object) -> Optional[int]:
    text = str(value or "").replace(",", "")
    m = re.search(r"(\d+)\s*円", text)
    return int(m.group(1)) if m else None


def published_prize(row: Dict[str, str], grade: str) -> str:
    if grade == "はずれ":
        return "0円"
    value = str(row.get(f"{grade}当選金額", "") or "").strip()
    return value or "確認できません"


def index_actuals(loto_rows: Sequence[Dict[str, str]]) -> Tuple[Dict[int, Dict[str, str]], Dict[int, Dict[str, str]]]:
    by_round: Dict[int, Dict[str, str]] = {}
    previous: Dict[int, Dict[str, str]] = {}
    ordered = []
    for row in loto_rows:
        n = parse_round(row.get("回別", ""))
        if n is not None:
            ordered.append((n, row))
    ordered.sort(key=lambda x: x[0])
    prev: Optional[Dict[str, str]] = None
    for n, row in ordered:
        by_round[n] = row
        if prev is not None:
            previous[n] = prev
        prev = row
    return by_round, previous


def consistency_check(pred_row: Dict[str, str], main: Tuple[int, ...], bonus: Tuple[int, ...]) -> str:
    embedded_main = parse_nums(pred_row.get("actual_main_numbers", ""))
    embedded_bonus = parse_nums(pred_row.get("actual_bonus_numbers", ""))
    if embedded_main and tuple(sorted(embedded_main)) != tuple(sorted(main)):
        return "mismatch_actual_main"
    if embedded_bonus and tuple(sorted(embedded_bonus)) != tuple(sorted(bonus)):
        return "mismatch_actual_bonus"
    return "verified_against_loto_csv"


def build_reconciliation(pred_rows: Sequence[Dict[str, str]], loto_rows: Sequence[Dict[str, str]]) -> List[Dict[str, object]]:
    by_round, previous = index_actuals(loto_rows)
    out: List[Dict[str, object]] = []
    for pred in pred_rows:
        target_round = parse_round(pred.get("round", pred.get("target_round", "")))
        if target_round is None:
            continue
        actual = by_round.get(target_round)
        if actual is None:
            continue
        predicted = parse_nums(pred.get("predicted_numbers", ""))
        main = parse_nums(actual.get("本数字", ""))
        bonus = parse_nums(actual.get("ボーナス数字", ""))
        if len(predicted) != 7 or len(main) != 7 or len(bonus) != 2:
            continue
        mh, bh, grade = grade_ticket(tuple(predicted), tuple(main), tuple(bonus))
        prize_text = published_prize(actual, grade)
        prize_yen = parse_money_yen(prize_text)
        if grade == "はずれ":
            prize_yen = 0
        if prize_yen is None:
            settlement = "published_payout_unavailable"
            ref_net: object = ""
        else:
            settlement = "published_payout_reference"
            ref_net = prize_yen - PURCHASE_COST_YEN
        prev = previous.get(target_round, {})
        consistency = consistency_check(pred, tuple(main), tuple(bonus))
        if consistency != "verified_against_loto_csv":
            raise RuntimeError(f"historical prediction/result mismatch at round {target_round}: {consistency}")
        out.append({
            "base_round": parse_round(prev.get("回別", "")) or target_round - 1,
            "base_draw_date": prev.get("抽せん日", ""),
            "target_round": target_round,
            "target_draw_date": actual.get("抽せん日", ""),
            "training_rows": pred.get("training_rows", ""),
            "ticket": pred.get("ticket", ""),
            "predicted_numbers": fmt_nums(predicted),
            "actual_main_numbers": fmt_nums(main),
            "actual_bonus_numbers": fmt_nums(bonus),
            "main_hits": mh,
            "bonus_hits": bh,
            "grade": grade,
            "published_prize_amount": prize_text,
            "published_prize_yen": "" if prize_yen is None else prize_yen,
            "purchase_cost_yen": PURCHASE_COST_YEN,
            "reference_net_yen": ref_net,
            "settlement_status": settlement,
            "source_consistency": consistency,
        })
    return out


def summarize(rows: Sequence[Dict[str, object]], pred_sha: str, loto_sha: str) -> Dict[str, object]:
    grade_counts: Dict[str, int] = {}
    rounds = set()
    known_payout = 0
    known_rows = 0
    unknown_rows = 0
    wins = 0
    for row in rows:
        rounds.add(int(row["target_round"]))
        grade = str(row["grade"])
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
        if grade != "はずれ":
            wins += 1
        value = row.get("published_prize_yen", "")
        if value == "":
            unknown_rows += 1
        else:
            known_payout += int(value)
            known_rows += 1
    total_cost = len(rows) * PURCHASE_COST_YEN
    return {
        "report_version": REPORT_VERSION,
        "prediction_sha256": pred_sha,
        "loto_csv_sha256": loto_sha,
        "evaluated_rounds": len(rounds),
        "evaluated_tickets": len(rows),
        "first_round": min(rounds) if rounds else None,
        "last_round": max(rounds) if rounds else None,
        "grade_counts": grade_counts,
        "winning_tickets": wins,
        "winning_ticket_rate": wins / max(1, len(rows)),
        "purchase_cost_yen": total_cost,
        "published_reference_payout_yen": known_payout,
        "published_reference_net_yen": known_payout - total_cost if unknown_rows == 0 else None,
        "published_reference_roi": (known_payout / total_cost) if total_cost and unknown_rows == 0 else None,
        "known_payout_rows": known_rows,
        "unknown_payout_rows": unknown_rows,
        "integrity": {
            "prediction_actual_fields_reverified": True,
            "mismatches": 0,
        },
        "note": "Published prize amounts are reference values from historical results. These predictions were not necessarily purchased, so this is not an actual realized P/L and a hypothetical winning ticket could alter pari-mutuel payouts.",
    }


def render_report(summary: Dict[str, object]) -> str:
    grades = summary.get("grade_counts", {}) or {}
    grade_text = " / ".join(f"{k}: {v}" for k, v in sorted(grades.items()))
    roi = summary.get("published_reference_roi")
    net = summary.get("published_reference_net_yen")
    lines = [
        "# LOTO7 Historical Prediction Reconciliation",
        "",
        f"- 照合回数: **{summary['evaluated_rounds']}回** ({summary['first_round']}〜{summary['last_round']})",
        f"- 照合口数: **{summary['evaluated_tickets']}口**",
        f"- 当選口数: **{summary['winning_tickets']}口** ({summary['winning_ticket_rate']*100:.3f}%)",
        f"- 等級内訳: {grade_text or 'なし'}",
        f"- 参考購入額: **{summary['purchase_cost_yen']:,}円**",
        f"- 公表当選額ベース参考払戻: **{summary['published_reference_payout_yen']:,}円**",
    ]
    if net is not None and roi is not None:
        lines += [
            f"- 公表当選額ベース参考差引: **{int(net):+,}円**",
            f"- 公表当選額ベース参考回収率: **{float(roi)*100:.2f}%**",
        ]
    else:
        lines.append(f"- 当選額未確定行: **{summary['unknown_payout_rows']}口**（差引・回収率は確定せず）")
    lines += [
        "- 実績整合性: **loto7.csvを別読込して再照合 / mismatch 0**",
        "",
        "> 金額は各回で公表された1口あたり当選金額を参照した比較値です。過去予測が実際に購入されたとは限らず、仮に高額当選券を追加購入していた場合は当選口数や配当が変わり得るため、実現損益ではありません。",
        "",
    ]
    return "\n".join(lines)


def is_fresh(summary_path: Path, pred_sha: str, loto_sha: str) -> bool:
    if not summary_path.exists():
        return False
    try:
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        obj.get("report_version") == REPORT_VERSION
        and obj.get("prediction_sha256") == pred_sha
        and obj.get("loto_csv_sha256") == loto_sha
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile historical replay predictions against independently loaded LOTO7 actual results")
    ap.add_argument("--predictions", type=Path, default=Path("loto7_agent_output/historical_round_predictions.csv"))
    ap.add_argument("--loto-csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()

    pred_sha = sha256(args.predictions)
    loto_sha = sha256(args.loto_csv)
    summary_path = args.out_dir / "historical_reconciliation_summary.json"
    if args.if_stale and is_fresh(summary_path, pred_sha, loto_sha):
        print("[HISTORICAL-RECON] report is fresh; skipped")
        return 0

    pred_rows = read_csv(args.predictions)
    loto_rows = read_csv(args.loto_csv)
    rows = build_reconciliation(pred_rows, loto_rows)
    summary = summarize(rows, pred_sha, loto_sha)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "historical_reconciliation.csv", rows)
    write_json(summary_path, summary)
    (args.out_dir / "historical_reconciliation_report.md").write_text(render_report(summary), encoding="utf-8")
    print(f"[HISTORICAL-RECON] rounds={summary['evaluated_rounds']} tickets={summary['evaluated_tickets']} wins={summary['winning_tickets']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
