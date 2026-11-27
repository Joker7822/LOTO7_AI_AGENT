"""Fail-closed deadline for new Production publication on the official draw day."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

def check(source, now, *, before_push=False):
    if now.tzinfo is None:
        raise RuntimeError("timezone-aware clock required")
    local = now.astimezone(JST)
    if local.weekday() != 4 or not time(13) <= local.time() < time(17):
        raise RuntimeError("new Production allowed only Friday 13:00 to before 17:00 JST")
    if before_push and local.time() >= time(16,59):
        raise RuntimeError("insufficient time for safe push before 17:00 JST")
    if source.get("status") != "ok" or source.get("verification") != "verified_two_result_sources":
        raise RuntimeError("independent source verification required")
    latest = source.get("latest") or {}
    upcoming = (source.get("sources") or {}).get("official_schedule") or {}
    if (type(latest.get("round")) is not int or
            upcoming.get("round") != latest["round"] + 1 or
            upcoming.get("date") != local.date().isoformat()):
        raise RuntimeError("today's next unobserved draw schedule not verified")
    return upcoming["round"]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=Path("loto7_agent_output/source_validation.json"))
    parser.add_argument("--before-push",action="store_true")
    args=parser.parse_args()
    target=check(json.loads(args.source.read_text(encoding="utf-8")),datetime.now(JST),before_push=args.before_push)
    print(f"Pre-draw deadline passed verification for round {target}")

if __name__ == "__main__":
    main()
