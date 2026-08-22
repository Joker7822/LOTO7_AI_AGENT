#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import html as html_lib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import scrapingloto7

MIZUHO_URL = "https://www.mizuhobank.co.jp/takarakuji/check/loto/loto7/index.html"
RAKUTEN_BANK_URL = "https://www.rakuten-bank.co.jp/takarakuji/backnumber/"
OFFICIAL_URL = "https://www.takarakuji-official.jp/ec/loto7/?knyschm=0&kujiprdShbt=61"
JST = dt.timezone(dt.timedelta(hours=9))


def now_jst() -> dt.datetime:
    return dt.datetime.now(JST)


def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 LOTO7_AI_AGENT/4.1",
            "Accept-Language": "ja,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_html(value: str) -> str:
    value = re.sub(r"(?is)<script.*?>.*?</script>", " ", value)
    value = re.sub(r"(?is)<style.*?>.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html_lib.unescape(value).replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def parse_round(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def parse_nums(value: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(value or "")))


def validate_numbers(main: Tuple[int, ...], bonus: Tuple[int, ...]) -> None:
    if len(main) != 7 or len(set(main)) != 7:
        raise ValueError(f"invalid main numbers: {main}")
    if len(bonus) != 2 or len(set(bonus)) != 2:
        raise ValueError(f"invalid bonus numbers: {bonus}")
    if any(n < 1 or n > 37 for n in main + bonus):
        raise ValueError("numbers outside 1..37")
    if set(main) & set(bonus):
        raise ValueError("bonus overlaps main numbers")


def read_rows(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    return scrapingloto7.read_existing_csv(str(csv_path))


def latest_row(rows: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not rows:
        return None
    return max(rows, key=lambda r: (parse_round(r.get("回別", "")) or -1, r.get("抽せん日", "")))


def validate_row(row: Dict[str, str]) -> Dict[str, object]:
    round_no = parse_round(row.get("回別", ""))
    if round_no is None:
        raise ValueError("latest row has no valid round")
    try:
        date = dt.date.fromisoformat(row.get("抽せん日", ""))
    except ValueError as exc:
        raise ValueError("latest row has invalid date") from exc
    main = parse_nums(row.get("本数字", ""))
    bonus = parse_nums(row.get("ボーナス数字", ""))
    validate_numbers(main, bonus)
    return {
        "round": round_no,
        "date": date.isoformat(),
        "main": list(main),
        "bonus": list(bonus),
    }


def expected_new_round(before: Optional[Dict[str, str]], now: Optional[dt.datetime] = None) -> Optional[Tuple[int, str]]:
    """Require a new result only when the repository is exactly one weekly draw behind on Friday evening."""
    if before is None:
        return None
    now = now or now_jst()
    if now.weekday() != 4 or (now.hour, now.minute) < (20, 0):
        return None
    r = parse_round(before.get("回別", ""))
    if r is None:
        return None
    try:
        d = dt.date.fromisoformat(before.get("抽せん日", ""))
    except ValueError:
        return None
    if d + dt.timedelta(days=7) == now.date():
        return r + 1, now.date().isoformat()
    return None


def parse_result_text(text: str, target_round: Optional[int] = None) -> Optional[Dict[str, object]]:
    if target_round is not None:
        locators = [f"第{target_round}回", f"第 {target_round} 回", f"{target_round}回", f"{target_round} 回"]
        positions = [text.find(x) for x in locators if text.find(x) >= 0]
        if not positions:
            return None
        pos = min(positions)
        segment = text[max(0, pos - 200): pos + 3500]
    else:
        segment = text

    mr = re.search(r"(?:第\s*)?(\d{1,6})\s*回", segment)
    md = re.search(r"(20\d{2})\s*[年/]\s*(\d{1,2})\s*[月/]\s*(\d{1,2})\s*日?", segment)
    mm = re.search(r"本数字\s*[:：]?\s*([0-9\s()（）]+?)\s*ボーナス数字", segment)
    mb = re.search(r"ボーナス数字\s*[:：]?\s*([0-9\s()（）]+?)(?:等級|1等|販売実績額|キャリーオーバー|次回|$)", segment)
    if not (mr and mm and mb):
        return None
    main = tuple(int(x) for x in re.findall(r"\d{1,2}", mm.group(1)))[:7]
    bonus = tuple(int(x) for x in re.findall(r"\d{1,2}", mb.group(1)))[:2]
    try:
        validate_numbers(main, bonus)
    except ValueError:
        return None
    round_no = int(mr.group(1))
    if target_round is not None and round_no != int(target_round):
        return None
    date_text = ""
    if md:
        date_text = f"{int(md.group(1)):04d}-{int(md.group(2)):02d}-{int(md.group(3)):02d}"
    return {"round": round_no, "date": date_text, "main": list(main), "bonus": list(bonus)}


def parse_mizuho(html: str, target_round: Optional[int] = None) -> Optional[Dict[str, object]]:
    return parse_result_text(strip_html(html), target_round)


def parse_rakuten_bank(html: str, target_round: Optional[int] = None) -> Optional[Dict[str, object]]:
    return parse_result_text(strip_html(html), target_round)


def iframe_urls(html: str, base_url: str) -> List[str]:
    urls: List[str] = []
    seen = set()
    for src in re.findall(r"(?is)<iframe[^>]+src\s*=\s*[\"']([^\"']+)[\"']", html):
        url = urllib.parse.urljoin(base_url, html_lib.unescape(src).strip())
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def fetch_rakuten_bank_result(target_round: int) -> Dict[str, object]:
    root = http_get(RAKUTEN_BANK_URL)
    direct = parse_rakuten_bank(root, target_round)
    if direct is not None:
        return {**direct, "transport": "root_page"}

    checked: List[str] = []
    queue = iframe_urls(root, RAKUTEN_BANK_URL)
    for url in queue[:12]:
        checked.append(url)
        try:
            child = http_get(url)
        except Exception:
            continue
        got = parse_rakuten_bank(child, target_round)
        if got is not None:
            return {**got, "transport": "iframe", "url": url}
        for nested in iframe_urls(child, url):
            if nested not in queue and len(queue) < 20:
                queue.append(nested)
    return {"status": "target_not_parseable", "iframes_checked": len(checked)}


def parse_official_schedule(html: str) -> Optional[Dict[str, object]]:
    text = strip_html(html)
    m = re.search(r"ロト\s*7\s*[（(]\s*第\s*(\d+)\s*回\s*[）)]", text, re.I)
    d = re.search(r"抽せん日\s*[:：]?\s*(20\d{2})[/年]\s*(\d{1,2})[/月]\s*(\d{1,2})日?", text)
    if not m:
        return None
    return {
        "round": int(m.group(1)),
        "date": f"{int(d.group(1)):04d}-{int(d.group(2)):02d}-{int(d.group(3)):02d}" if d else "",
    }


def source_snapshot(target_round: int) -> Dict[str, object]:
    out: Dict[str, object] = {}
    try:
        out["mizuho"] = parse_mizuho(http_get(MIZUHO_URL), target_round) or {"status": "target_not_parseable"}
    except Exception as exc:
        out["mizuho"] = {"status": "unavailable", "error": str(exc)[:300]}
    try:
        out["rakuten_bank"] = fetch_rakuten_bank_result(target_round)
    except Exception as exc:
        out["rakuten_bank"] = {"status": "unavailable", "error": str(exc)[:300]}
    try:
        out["official_schedule"] = parse_official_schedule(http_get(OFFICIAL_URL)) or {"status": "not_parseable"}
    except Exception as exc:
        out["official_schedule"] = {"status": "unavailable", "error": str(exc)[:300]}
    return out


def result_matches(primary: Dict[str, object], candidate: Dict[str, object]) -> bool:
    return (
        int(candidate.get("round", -1)) == int(primary["round"])
        and list(candidate.get("main", [])) == list(primary["main"])
        and list(candidate.get("bonus", [])) == list(primary["bonus"])
        and (not candidate.get("date") or candidate.get("date") == primary["date"])
    )


def compare_sources(primary: Dict[str, object], sources: Dict[str, object]) -> Tuple[str, List[str]]:
    notes: List[str] = []
    verified: List[str] = []
    for key, label in (("mizuho", "Mizuho"), ("rakuten_bank", "Rakuten Bank")):
        candidate = sources.get(key, {})
        if not isinstance(candidate, dict) or "main" not in candidate:
            continue
        if int(candidate.get("round", -1)) != int(primary["round"]):
            continue
        if not result_matches(primary, candidate):
            return "mismatch", [f"Rakuten primary and {label} results disagree"]
        verified.append(label)
        notes.append(f"{label} result matches Rakuten primary main/bonus numbers")

    official = sources.get("official_schedule", {})
    if isinstance(official, dict) and "round" in official:
        notes.append(f"official schedule visible: round={official.get('round')} date={official.get('date','')}")

    if verified:
        notes.append("result verification succeeded using at least two published result endpoints")
        return "verified_two_result_sources", notes

    notes.append("No secondary result endpoint was parseable for this round; operating in degraded single-result-source mode")
    return "degraded_single_result_source", notes


def write_report(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch LOTO7 with freshness gate and redundant cross-source validation")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--max-attempts", type=int, default=10)
    ap.add_argument("--interval-seconds", type=int, default=600)
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--require-two-result-sources", action="store_true")
    args = ap.parse_args()

    before_rows = read_rows(args.csv)
    before = latest_row(before_rows)
    expected = expected_new_round(before)
    last_error = ""

    for attempt in range(1, max(1, args.max_attempts) + 1):
        print(f"[FETCH] attempt {attempt}/{args.max_attempts}")
        try:
            scrapingloto7.update_loto7_csv(
                str(args.csv),
                months=max(1, args.months),
                all_history=not args.csv.exists() or not before_rows,
            )
            rows = read_rows(args.csv)
            latest = latest_row(rows)
            if latest is None:
                raise RuntimeError("loto7.csv is empty after fetch")
            primary = validate_row(latest)

            if expected is not None:
                expected_round, expected_date = expected
                if int(primary["round"]) < expected_round or str(primary["date"]) != expected_date:
                    raise RuntimeError(
                        f"fresh result not available yet: expected round={expected_round} date={expected_date}; "
                        f"got round={primary['round']} date={primary['date']}"
                    )

            sources = source_snapshot(int(primary["round"]))
            verification, notes = compare_sources(primary, sources)
            if verification == "mismatch":
                raise RuntimeError("cross-source mismatch: " + "; ".join(notes))
            if args.require_two_result_sources and verification != "verified_two_result_sources":
                raise RuntimeError("second result source not yet verified")

            report = {
                "checked_at_jst": now_jst().isoformat(timespec="seconds"),
                "attempt": attempt,
                "status": "ok" if verification == "verified_two_result_sources" else "degraded",
                "verification": verification,
                "primary_source": "Rakuten backnumber via scrapingloto7.py",
                "secondary_policy": "Mizuho preferred; Rakuten Bank public winning-number page is accepted as fallback",
                "latest": primary,
                "freshness_expected": {"round": expected[0], "date": expected[1]} if expected else None,
                "sources": sources,
                "notes": notes,
            }
            write_report(args.report, report)
            print(f"[VALIDATION] {verification} round={primary['round']} date={primary['date']}")
            return 0
        except Exception as exc:
            last_error = str(exc)
            print(f"[WAIT] {last_error}", file=sys.stderr)
            if attempt < args.max_attempts and args.interval_seconds > 0:
                time.sleep(args.interval_seconds)

    write_report(args.report, {
        "checked_at_jst": now_jst().isoformat(timespec="seconds"),
        "status": "failed",
        "freshness_expected": {"round": expected[0], "date": expected[1]} if expected else None,
        "error": last_error,
    })
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
