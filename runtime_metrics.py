#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path

JST = dt.timezone(dt.timedelta(hours=9))
FIELDS = [
    "completed_at_jst", "runner_iteration", "generation", "duration_seconds",
    "data_sha256", "champion_version", "research_winner",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=Path, default=Path("loto7_agent_output/execution_metrics.csv"))
    ap.add_argument("--state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--iteration", required=True)
    ap.add_argument("--duration-seconds", required=True, type=int)
    args = ap.parse_args()

    state = {}
    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    exists = args.metrics.exists() and args.metrics.stat().st_size > 0
    row = {
        "completed_at_jst": dt.datetime.now(JST).isoformat(timespec="seconds"),
        "runner_iteration": args.iteration,
        "generation": state.get("generation", ""),
        "duration_seconds": args.duration_seconds,
        "data_sha256": state.get("current_data_sha", ""),
        "champion_version": state.get("champion_version", ""),
        "research_winner": state.get("research_winner", ""),
    }
    with args.metrics.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
