#!/usr/bin/env python3
"""Read-only LOTO7 data quality audit with bounded derived-report regeneration.

Never repairs lottery observations, source attestations, registered evidence or
Production. Only its own two reports are regenerated from the checked inputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

VERSION = "research-data-quality-v1"
JSON_REPORT = "research_data_quality.json"
MD_REPORT = "research_data_quality_report.md"
JST = timezone(timedelta(hours=9))
REQUIRED = {"回別", "抽せん日", "本数字", "ボーナス数字"}
ROUND = re.compile(r"第?(\d+)回\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def issue(code: str, severity: str, detail: str) -> dict:
    return {"code": code, "severity": severity, "detail": detail,
            "action": "review_source_or_existing_validator"}


def parse_numbers(value: str, count: int) -> tuple[int, ...]:
    if not isinstance(value, str):
        raise ValueError("missing number column")
    values = tuple(int(x) for x in re.findall(r"\d+", value))
    if len(values) != count or len(set(values)) != count or any(
            n < 1 or n > 37 for n in values):
        raise ValueError("numbers must be unique, complete and within 1..37")
    return values


def next_result_deadline(last_draw: date, source: dict) -> datetime:
    """Official schedule may move the next result; otherwise use Friday + 7d."""
    next_day = last_draw + timedelta(days=7)
    official = source.get("sources", {}).get("official_schedule", {})
    latest = source.get("latest", {})
    if isinstance(official, dict) and isinstance(latest, dict):
        try:
            scheduled = date.fromisoformat(official.get("date", ""))
            if (official.get("round") == latest.get("round", 0) + 1
                    and last_draw < scheduled <= last_draw + timedelta(days=14)):
                next_day = scheduled
        except (TypeError, ValueError):
            pass
    return datetime.combine(next_day, time(20, 0), JST)


def audit(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    now = (now or datetime.now(JST)).astimezone(JST)
    csv_path = root / "loto7.csv"
    source_path = root / "loto7_agent_output" / "source_validation.json"
    problems = []
    draw_bytes = csv_path.read_bytes() if csv_path.is_file() else b""
    source_bytes = source_path.read_bytes() if source_path.is_file() else b""
    if not draw_bytes:
        problems.append(issue("DRAW_DATA_MISSING", "block", "historical CSV unavailable"))
    if not source_bytes:
        problems.append(issue("SOURCE_ATTESTATION_MISSING", "block", "source receipt unavailable"))
    try:
        source = json.loads(source_bytes) if source_bytes else {}
        if not isinstance(source, dict):
            raise ValueError("invalid source receipt")
    except (ValueError, UnicodeError):
        source = {}
        problems.append(issue("SOURCE_ATTESTATION_INVALID", "block", "source receipt is not valid JSON"))
    rows = []
    try:
        if not draw_bytes:
            raise ValueError("empty history")
        reader = csv.DictReader(io.StringIO(draw_bytes.decode("utf-8-sig"), newline=""))
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("missing required history columns")
        seen = set()
        previous_round, previous_date = 0, None
        for row in reader:
            match = ROUND.fullmatch((row.get("回別") or "").strip())
            if match is None:
                raise ValueError("invalid round label")
            n = int(match.group(1))
            draw_date = date.fromisoformat(row["抽せん日"])
            main = parse_numbers(row["本数字"], 7)
            bonus = parse_numbers(row["ボーナス数字"], 2)
            if set(main) & set(bonus):
                raise ValueError("main and bonus numbers overlap")
            if n in seen or n <= previous_round or (previous_date and draw_date <= previous_date):
                raise ValueError("duplicate or unsorted round/date")
            if n != previous_round + 1:
                problems.append(issue("HISTORICAL_ROUND_GAP", "watch",
                                      "gap before round " + str(n)))
            if draw_date > now.date():
                raise ValueError("historical CSV contains a future draw")
            seen.add(n)
            rows.append({"round": n, "date": draw_date.isoformat(),
                         "main": list(main), "bonus": list(bonus)})
            previous_round, previous_date = n, draw_date
        if not rows:
            raise ValueError("no rows")
    except (ValueError, TypeError, UnicodeError, csv.Error) as exc:
        problems.append(issue("DRAW_DATA_INVALID", "block", str(exc)[:160]))
        rows = []
    provenance = source.get("verification_provenance", {})
    receipt_sha = provenance.get("draw_csv_sha256") if isinstance(provenance, dict) else None
    if receipt_sha != sha(draw_bytes):
        problems.append(issue("DRAW_SHA_MISMATCH", "block",
                              "source receipt does not match exact CSV bytes"))
    if (source.get("status") != "ok"
            or source.get("verification") != "verified_two_result_sources"):
        problems.append(issue("INDEPENDENT_SOURCE_NOT_VERIFIED", "block",
                              "two published result sources not independently verified"))
    if rows:
        latest = source.get("latest", {})
        if not isinstance(latest, dict) or any(latest.get(k) != rows[-1][k]
                                               for k in ("round", "date", "main", "bonus")):
            problems.append(issue("LATEST_DRAW_CONFLICT", "block",
                                  "last CSV row differs from source receipt"))
        else:
            deadline = next_result_deadline(date.fromisoformat(rows[-1]["date"]), source)
            if now >= deadline:
                problems.append(issue("DRAW_UPDATE_OVERDUE", "watch",
                                      "next scheduled draw has passed its 20:00 JST result threshold"))
    status = ("block" if any(p["severity"] == "block" for p in problems)
              else "watch" if problems else "pass")
    return {
        "version": VERSION,
        "checked_at_jst": now.isoformat(timespec="seconds"),
        "draw_csv_sha256": sha(draw_bytes),
        "source_sha256": sha(source_bytes),
        "latest_round": rows[-1]["round"] if rows else None,
        "rows_checked": len(rows),
        "status": status,
        "issues": problems,
        "auto_repair_scope": "derived_quality_reports_only",
        "source_csv_modified": False,
        "source_attestation_modified": False,
        "production_or_oos_modified": False,
    }


def atomic_update(path: Path, content: str) -> bool:
    data = content.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".quality-",
                                         delete=False) as handle:
            temp_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return True


def run(root: Path, *, now: datetime | None = None) -> dict:
    result = audit(root, now=now)
    out = root / "loto7_agent_output"
    json_text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    lines = ["# Research Data Quality", "",
             "- Checked: " + result["checked_at_jst"],
             "- Status: **" + result["status"] + "**",
             "- CSV rows: " + str(result["rows_checked"]),
             "- Exact CSV SHA256: " + result["draw_csv_sha256"], ""]
    for item in result["issues"]:
        lines.append("- **" + item["severity"] + " / " + item["code"] +
                     "**: " + item["detail"])
    if not result["issues"]:
        lines.append("- All configured data-integrity checks passed.")
    lines.extend(["", "Only these derived reports may be regenerated automatically.",
                  "Unverified results must not be promoted or used for prospective scoring.",
                  "No change to CSV, registered OOS, research budget or Production.", ""])
    changed = [name for name, body in ((JSON_REPORT, json_text),
                                        (MD_REPORT, "\n".join(lines)))
               if atomic_update(out / name, body)]
    return {**result, "derived_reports_regenerated": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit data; regenerate only derived audit reports")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.repo_root)
    print(json.dumps({"status": result["status"], "issues": len(result["issues"]),
                      "reports_regenerated": result["derived_reports_regenerated"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
