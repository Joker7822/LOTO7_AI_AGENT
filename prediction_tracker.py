#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOTO7 prediction tracker.

- latest 5 candidate tickets are appended to a cumulative audit CSV once per target round.
- completed predictions are reconciled against loto7.csv.
- official prize rank conditions are applied from main/bonus matches.
- prize money is read from the matching rank's actual draw row in loto7.csv.
- human-readable cumulative and latest reports are written as UTF-8 text.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

HISTORY_FIELDS = [
    "prediction_created_at_jst",
    "base_round",
    "base_draw_date",
    "target_round",
    "target_draw_date_estimate",
    "ticket",
    "predicted_numbers",
    "status",
    "actual_draw_date",
    "actual_main_numbers",
    "actual_bonus_numbers",
    "main_hits",
    "bonus_hits",
    "grade",
    "prize_amount",
    "checked_at_jst",
]


def now_jst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def fmt_now_jst() -> str:
    return now_jst().isoformat(timespec="seconds")


def read_csv_flexible(path: Path) -> List[Dict[str, str]]:
    errors = []
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [
                    {str(k): str(v or "").strip() for k, v in row.items()}
                    for row in csv.DictReader(f)
                ]
        except UnicodeDecodeError as exc:
            errors.append(f"{enc}: {exc}")
    raise RuntimeError(f"CSV decode failed: {path}: {' / '.join(errors)}")


def write_csv(path: Path, rows: Iterable[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def parse_round(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def round_label(number: Optional[int]) -> str:
    return f"第{number}回" if number is not None else ""


def parse_numbers(value: str) -> Tuple[int, ...]:
    nums = tuple(int(x) for x in re.findall(r"\d+", str(value or "")))
    return nums


def normalize_numbers(nums: Iterable[int]) -> str:
    return " ".join(f"{n:02d}" for n in sorted(nums))


def next_week_estimate(date_text: str) -> str:
    try:
        d = dt.date.fromisoformat(date_text)
        return (d + dt.timedelta(days=7)).isoformat()
    except ValueError:
        return ""


def grade_ticket(predicted: Tuple[int, ...], main: Tuple[int, ...], bonus: Tuple[int, ...]) -> Tuple[int, int, str]:
    p, m, b = set(predicted), set(main), set(bonus)
    main_hits = len(p & m)
    bonus_hits = len(p & b)

    # Official LOTO7 conditions:
    # 1st: 7 main
    # 2nd: 6 main + >=1 bonus
    # 3rd: 6 main
    # 4th: 5 main
    # 5th: 4 main
    # 6th: 3 main + >=1 bonus
    if main_hits == 7:
        grade = "1等"
    elif main_hits == 6 and bonus_hits >= 1:
        grade = "2等"
    elif main_hits == 6:
        grade = "3等"
    elif main_hits == 5:
        grade = "4等"
    elif main_hits == 4:
        grade = "5等"
    elif main_hits == 3 and bonus_hits >= 1:
        grade = "6等"
    else:
        grade = "はずれ"
    return main_hits, bonus_hits, grade


def prize_amount_for_grade(draw: Dict[str, str], grade: str) -> str:
    if grade == "はずれ":
        return "0円"
    value = str(draw.get(f"{grade}当選金額", "")).strip()
    return value if value else "確認できません"


def draw_map(loto_rows: List[Dict[str, str]]) -> Dict[int, Dict[str, str]]:
    out: Dict[int, Dict[str, str]] = {}
    for row in loto_rows:
        r = parse_round(row.get("回別", ""))
        if r is not None:
            out[r] = row
    return out


def load_history(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv_flexible(path)
    return [{k: row.get(k, "") for k in HISTORY_FIELDS} for row in rows]


def latest_draw(loto_rows: List[Dict[str, str]]) -> Dict[str, str]:
    candidates = [(parse_round(r.get("回別", "")), r) for r in loto_rows]
    candidates = [(n, r) for n, r in candidates if n is not None]
    if not candidates:
        raise RuntimeError("loto7.csv に有効な回号がありません。")
    return max(candidates, key=lambda x: x[0])[1]


def reconcile(history: List[Dict[str, str]], draws: Dict[int, Dict[str, str]]) -> None:
    checked = fmt_now_jst()
    for row in history:
        target = parse_round(row.get("target_round", ""))
        if target is None or target not in draws:
            if row.get("status") != "checked":
                row["status"] = "pending"
            continue

        draw = draws[target]
        predicted = parse_numbers(row.get("predicted_numbers", ""))
        main = parse_numbers(draw.get("本数字", ""))
        bonus = parse_numbers(draw.get("ボーナス数字", ""))

        if len(predicted) != 7 or len(main) != 7 or len(bonus) != 2:
            row["status"] = "error"
            row["checked_at_jst"] = checked
            continue

        mh, bh, grade = grade_ticket(predicted, main, bonus)
        row.update(
            {
                "status": "checked",
                "actual_draw_date": draw.get("抽せん日", ""),
                "actual_main_numbers": normalize_numbers(main),
                "actual_bonus_numbers": normalize_numbers(bonus),
                "main_hits": str(mh),
                "bonus_hits": str(bh),
                "grade": grade,
                "prize_amount": prize_amount_for_grade(draw, grade),
                "checked_at_jst": checked,
            }
        )


def append_latest_prediction(
    history: List[Dict[str, str]],
    loto_rows: List[Dict[str, str]],
    ticket_rows: List[Dict[str, str]],
) -> int:
    base = latest_draw(loto_rows)
    base_no = parse_round(base.get("回別", ""))
    if base_no is None:
        raise RuntimeError("最新回号を解析できません。")
    target_no = base_no + 1

    # Once a round has been recorded, do not rewrite history on reruns.
    if any(parse_round(r.get("target_round", "")) == target_no for r in history):
        return 0

    created = fmt_now_jst()
    estimate = next_week_estimate(base.get("抽せん日", ""))
    added = 0
    for ticket_row in ticket_rows:
        nums = parse_numbers(ticket_row.get("numbers", ""))
        if len(nums) != 7:
            raise RuntimeError(f"候補数字が7個ではありません: {ticket_row}")
        history.append(
            {
                "prediction_created_at_jst": created,
                "base_round": base.get("回別", round_label(base_no)),
                "base_draw_date": base.get("抽せん日", ""),
                "target_round": round_label(target_no),
                "target_draw_date_estimate": estimate,
                "ticket": ticket_row.get("ticket", str(added + 1)),
                "predicted_numbers": normalize_numbers(nums),
                "status": "pending",
                "actual_draw_date": "",
                "actual_main_numbers": "",
                "actual_bonus_numbers": "",
                "main_hits": "",
                "bonus_hits": "",
                "grade": "",
                "prize_amount": "",
                "checked_at_jst": "",
            }
        )
        added += 1
    return added


def money_to_int(value: str) -> Optional[int]:
    m = re.fullmatch(r"\s*([0-9,]+)\s*円\s*", str(value or ""))
    return int(m.group(1).replace(",", "")) if m else None


def report_group_sort_key(item):
    target, rows = item
    return target if target is not None else -1


def render_cumulative(history: List[Dict[str, str]]) -> str:
    grouped: Dict[Optional[int], List[Dict[str, str]]] = {}
    for row in history:
        grouped.setdefault(parse_round(row.get("target_round", "")), []).append(row)

    lines = [
        "LOTO7 予測・当選照合 累積レポート",
        f"更新日時(JST): {fmt_now_jst()}",
        "=" * 72,
        "",
    ]

    total_checked_tickets = 0
    total_winning_tickets = 0
    total_known_prize = 0

    for target_no, rows in sorted(grouped.items(), key=report_group_sort_key, reverse=True):
        rows = sorted(rows, key=lambda r: int(r.get("ticket") or 999))
        first = rows[0]
        lines.append(f"[{round_label(target_no)}]")
        lines.append(
            f"予測基準: {first.get('base_round','')} / "
            f"{first.get('base_draw_date','')}"
        )
        lines.append(f"予測作成(JST): {first.get('prediction_created_at_jst','')}")

        checked_rows = [r for r in rows if r.get("status") == "checked"]
        if checked_rows:
            d = checked_rows[0]
            lines.append(f"抽せん日: {d.get('actual_draw_date','')}")
            lines.append(f"本数字: {d.get('actual_main_numbers','')}")
            lines.append(f"ボーナス数字: {d.get('actual_bonus_numbers','')}")
        else:
            lines.append(
                f"抽せん予定日(週次推定): "
                f"{first.get('target_draw_date_estimate','') or '確認できません'}"
            )
            lines.append("当選結果: 未取得")

        lines.append("-" * 72)
        round_known_total = 0
        round_known = True
        for r in rows:
            ticket = r.get("ticket", "")
            pred = r.get("predicted_numbers", "")
            if r.get("status") == "checked":
                total_checked_tickets += 1
                grade = r.get("grade", "")
                amount = r.get("prize_amount", "")
                if grade != "はずれ":
                    total_winning_tickets += 1
                val = money_to_int(amount)
                if val is None:
                    round_known = False
                else:
                    round_known_total += val
                    total_known_prize += val
                lines.append(
                    f"予測{ticket}: {pred} | 本数字一致 {r.get('main_hits','')} | "
                    f"ボーナス一致 {r.get('bonus_hits','')} | {grade} | {amount}"
                )
            elif r.get("status") == "error":
                lines.append(f"予測{ticket}: {pred} | 照合エラー")
            else:
                lines.append(f"予測{ticket}: {pred} | 判定待ち")

        if checked_rows:
            lines.append(
                f"この回の既知当選金額合計: "
                f"{round_known_total:,}円" if round_known else
                "この回の当選金額合計: 一部確認できません"
            )
        lines.append("")

    lines.extend(
        [
            "=" * 72,
            f"照合済み予測口数: {total_checked_tickets}",
            f"当選口数: {total_winning_tickets}",
            f"確認済み当選金額累計: {total_known_prize:,}円",
            "",
            "※ 等級はLOTO7の本数字・ボーナス数字一致条件で判定。",
            "※ 当選金額は各回の loto7.csv に保存された実績金額を使用。",
            "※ 未取得・空欄の金額は「確認できません」と表示。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_latest(history: List[Dict[str, str]]) -> str:
    if not history:
        return "LOTO7 最新予測\n予測履歴がありません。\n"

    target_nums = [parse_round(r.get("target_round", "")) for r in history]
    valid = [n for n in target_nums if n is not None]
    if not valid:
        return "LOTO7 最新予測\n対象回を確認できません。\n"

    latest_target = max(valid)
    rows = [r for r in history if parse_round(r.get("target_round", "")) == latest_target]
    rows.sort(key=lambda r: int(r.get("ticket") or 999))
    first = rows[0]
    lines = [
        "LOTO7 最新予測",
        "=" * 48,
        f"対象回: {round_label(latest_target)}",
        f"予測基準: {first.get('base_round','')} / {first.get('base_draw_date','')}",
        f"予測作成(JST): {first.get('prediction_created_at_jst','')}",
        f"抽せん予定日(週次推定): {first.get('target_draw_date_estimate','') or '確認できません'}",
        "",
    ]
    for r in rows:
        lines.append(f"{r.get('ticket','')}. {r.get('predicted_numbers','')}")
    if all(r.get("status") == "checked" for r in rows):
        lines.append("")
        lines.append("※ この対象回は照合済みです。次回予測の生成待ちです。")
    else:
        lines.append("")
        lines.append("※ 5通りの候補。将来の当せんを保証するものではありません。")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="LOTO7予測履歴の累積・当選照合・テキスト出力")
    p.add_argument("--loto-csv", type=Path, default=Path("loto7.csv"))
    p.add_argument(
        "--tickets-csv",
        type=Path,
        default=Path("loto7_agent_output/candidate_tickets.csv"),
    )
    p.add_argument(
        "--history-csv",
        type=Path,
        default=Path("loto7_agent_output/prediction_history.csv"),
    )
    p.add_argument(
        "--results-txt",
        type=Path,
        default=Path("loto7_agent_output/prediction_results.txt"),
    )
    p.add_argument(
        "--latest-txt",
        type=Path,
        default=Path("loto7_agent_output/latest_prediction.txt"),
    )
    args = p.parse_args()

    loto_rows = read_csv_flexible(args.loto_csv)
    ticket_rows = read_csv_flexible(args.tickets_csv)
    if len(ticket_rows) != 5:
        raise SystemExit(f"最新予測は5通り必須です。現在: {len(ticket_rows)}通り")

    history = load_history(args.history_csv)
    draws = draw_map(loto_rows)

    # First grade predictions whose actual result has arrived.
    reconcile(history, draws)
    # Then persist one immutable 5-ticket prediction set for the next round.
    added = append_latest_prediction(history, loto_rows, ticket_rows)
    # Reconcile once more in case historical imports include the target.
    reconcile(history, draws)

    history.sort(
        key=lambda r: (
            parse_round(r.get("target_round", "")) or -1,
            int(r.get("ticket") or 999),
        )
    )
    write_csv(args.history_csv, history, HISTORY_FIELDS)

    args.results_txt.parent.mkdir(parents=True, exist_ok=True)
    args.results_txt.write_text(render_cumulative(history), encoding="utf-8")
    args.latest_txt.write_text(render_latest(history), encoding="utf-8")

    checked = sum(r.get("status") == "checked" for r in history)
    pending = sum(r.get("status") == "pending" for r in history)
    print(
        f"[TRACKER] history={len(history)} added={added} "
        f"checked={checked} pending={pending}"
    )
    print(f"[TRACKER] {args.history_csv}")
    print(f"[TRACKER] {args.results_txt}")
    print(f"[TRACKER] {args.latest_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
