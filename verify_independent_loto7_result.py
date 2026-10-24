#!/usr/bin/env python3
"""Cross-check a previously recorded Rakuten LOTO7 draw with a separate publisher.

This repairs unavailable bank result endpoints without fabricating a source.
A live second-site HTTP response must be parsed and match the existing,
unmodified primary CSV for round, date, main and bonus numbers. No prior
prospective scores, frozen forecasts, model selection or draw rows are edited.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import fetch_validate as fv
from joint_set_v2_signal_oos_guard import validate_trusted_source

TSUSHIN_URL_BASE = "https://loto7.money-plan.net/round"
JST = dt.timezone(dt.timedelta(hours=9))


def url_for_round(round_no: int) -> str:
    if not 1 <= round_no < 1_000_000:
        raise ValueError("invalid LOTO7 draw number")
    return f"{TSUSHIN_URL_BASE}/{round_no}/"


def parse_tsushin(html: str, target_round: int) -> dict | None:
    """Fail closed if the exact target result cannot be isolated unambiguously.

    This parser intentionally avoids guessing from general numbered menus,
    prediction listings, past draws, or unlabeled seven-number sequences.
    """
    text = fv.strip_html(html)
    round_pat = rf"第\s*0*{target_round}\s*回"
    # The page's specific draw heading must also contain the full draw date.
    dates = re.findall(
        round_pat + r"\s*(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        text,
    )
    if not dates or len(set(dates)) != 1:
        return None
    y, m, day = dates[0]
    try:
        date = dt.date(int(y), int(m), int(day)).isoformat()
    except ValueError:
        return None
    # Only the labeled result grid, never digits from a prediction or an
    # unrelated historical draw, may qualify as secondary result evidence.
    matches = []
    grid = re.compile(
        r"当選数字\s+((?:\d{1,2}\s+){6}\d{1,2})\s+"
        r"ボーナス数字\s+\(?\s*(\d{1,2})\s*\)?\s+\(?\s*(\d{1,2})\s*\)?",
        flags=re.I,
    )
    for hit in grid.finditer(text):
        # This result section is associated with the 700/other target heading
        # and not with another round's listing.
        # Match the CLOSEST draw heading, not merely the closest heading
        # for our requested round: a subsequent round's table must never be
        # mistaken for the target just because it appears within 350 chars.
        heading = list(re.finditer(r"第\s*0*(\d{1,6})\s*回", text[:hit.start()]))
        if (not heading or int(heading[-1].group(1)) != target_round
                or hit.start() - heading[-1].start() > 350):
            continue
        main = [int(n) for n in hit.group(1).split()]
        bonus = [int(hit.group(2)), int(hit.group(3))]
        try:
            fv.validate_numbers(tuple(main), tuple(bonus))
        except ValueError:
            continue
        matches.append({"round": target_round, "date": date,
                        "main": main, "bonus": bonus})
    if not matches or any(other != matches[0] for other in matches[1:]):
        return None
    return matches[0]


def fetch_secondary(round_no: int) -> dict:
    url = url_for_round(round_no)
    html = fv.http_get(url)
    parsed = parse_tsushin(html, round_no)
    if parsed is None:
        raise ValueError("independent publisher response lacks an unambiguous draw result")
    return {
        **parsed, "url": url, "transport": "direct_independent_publisher_page",
        "publisher": "LOTO7通信 (non-official, independent web publisher)",
        "fetched_at_jst": dt.datetime.now(JST).isoformat(timespec="seconds"),
        "response_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "source_tier": "independent_non_official",
    }


def candidate_report(csv_path: Path, report_path: Path, live_secondary: dict) -> dict:
    """Verify exact original CSV/source provenance before considering promotion."""
    before = json.loads(report_path.read_text(encoding="utf-8"))
    rows = fv.read_rows(csv_path)
    if not rows:
        raise ValueError("draw history does not exist")
    actual = fv.validate_row(fv.latest_row(rows))
    if before.get("latest") != actual:
        raise ValueError("primary source record and latest CSV differ")
    if before.get("primary_source") != "Rakuten backnumber via scrapingloto7.py":
        raise ValueError("unknown original primary publisher provenance")
    if before.get("status") not in ("degraded", "ok") or before.get("verification") not in (
        "degraded_single_result_source", "verified_two_result_sources"
    ):
        raise ValueError("previous report has invalid status")
    if live_secondary.get("url") != url_for_round(actual["round"]):
        raise ValueError("secondary URL is not the independently published draw URL")
    if live_secondary.get("source_tier") != "independent_non_official":
        raise ValueError("secondary publisher provenance is not recognized")
    if not fv.result_matches(actual, live_secondary) or not live_secondary.get("date"):
        raise ValueError("independent publisher disagrees with Rakuten numbers/date")
    original_sources = before.get("sources")
    if not isinstance(original_sources, dict):
        raise ValueError("original source record missing")
    # Never override any already independently verified contradictory source.
    for name in ("mizuho", "rakuten_bank"):
        other = original_sources.get(name)
        if isinstance(other, dict) and "main" in other and not fv.result_matches(actual, other):
            raise ValueError("another published source conflicts with the result")
    proposed = dict(before)
    proposed["status"] = "ok"
    proposed["verification"] = "verified_two_result_sources"
    proposed["checked_at_jst"] = dt.datetime.now(JST).isoformat(timespec="seconds")
    proposed["secondary_policy"] = (
        "Mizuho or Rakuten Bank preferred; when bank pages are blocked, "
        "an explicitly identified independently operated non-official publisher "
        "may corroborate a previously recorded Rakuten primary, if exact "
        "round/date/main/bonus and live response provenance all match."
    )
    proposed["sources"] = {**original_sources, "loto7_tsushin": live_secondary}
    proposed["notes"] = [*before.get("notes", []),
        "LOTO7通信 independently published result confirms the stored Rakuten primary.",
        "Secondary is non-official; Mizuho and Rakuten Bank result pages may remain unavailable.",
        "No retrospective future prediction freeze, score or model is amended."]
    proposed["verification_provenance"] = {
        "primary_domain": "takarakuji.rakuten.co.jp",
        "primary_method": "recorded_published_csv_result",
        "secondary_domain": "loto7.money-plan.net",
        "secondary_fetch": "live_https_response",
        "secondary_official": False,
        "independent_domains": True,
        "draw_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    return proposed


def write_atomic(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def verify(csv_path: Path, report_path: Path) -> dict:
    rows = fv.read_rows(csv_path)
    if not rows:
        raise ValueError("latest CSV not available")
    actual = fv.validate_row(fv.latest_row(rows))
    source = fetch_secondary(int(actual["round"]))
    proposal = candidate_report(csv_path, report_path, source)
    # The production-grade guard must accept the isolated proposed report
    # before the existing trusted-source record is atomically replaced.
    with tempfile.TemporaryDirectory() as tmp:
        isolated = Path(tmp) / "candidate_source.json"
        isolated.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
        checked = validate_trusted_source(csv_path, isolated)
        if not checked["trusted"] or "loto7_tsushin" not in checked["secondary"]:
            raise ValueError("prospective source guard rejected corroboration")
    write_atomic(report_path, json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
    return {"round": actual["round"], "status": proposal["status"],
            "verification": proposal["verification"], "secondary_url": source["url"],
            "independent_source_tier": "non_official", "csv_unchanged": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Live two-publication LOTO7 draw verification")
    parser.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    parser.add_argument("--report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    args = parser.parse_args()
    print(json.dumps(verify(args.csv, args.report), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
