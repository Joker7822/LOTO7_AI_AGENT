#!/usr/bin/env python3
"""Select a strictly same-history v2 research comparator, or no comparator.

Never mix a cached historical result (e.g. last verified draw 699) with
newer source history (e.g. round 700). Absence is explicitly reported as an
unavailable comparator by predictive_expert_agent; no synthetic substitution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def fingerprint_file(path: Path) -> str:
    # Standalone scripts/ entrypoints cannot import repository-root modules
    # before adjusting sys.path. Read the exact committed CSV bytes instead.
    return hashlib.sha256(path.read_bytes()).hexdigest()

KIND = "strict_prior_only_prequential_inclusion_probability_joint_set_v2"


def choose(csv_path: Path, summary: Path, last_n: int = 60) -> Path:
    try:
        report = json.loads(summary.read_text(encoding="utf-8"))
        if (report.get("data_sha256") == fingerprint_file(csv_path)
                and report.get("evaluation_type") == KIND
                and report.get("evaluated_rounds") == last_n
                and report.get("last_n", last_n) == last_n):
            return summary
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    # This sentinel is not a real report: predictive_expert_agent explicitly
    # returns {"available":false} when the path does not exist.
    return Path("/tmp/loto7_v2_comparator_not_valid_for_current_csv.json")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    p.add_argument("--summary", type=Path, default=Path("loto7_agent_output/joint_set_v2_true_nested_summary.json"))
    p.add_argument("--last-n", type=int, default=60)
    opts = p.parse_args()
    selected = choose(opts.csv, opts.summary, opts.last_n)
    if selected != opts.summary:
        print("::warning::V2 historical comparator is unavailable/stale for the current draw-history SHA; "
              "run exploratory research WITHOUT claiming a comparable v2 result.", file=sys.stderr)
    print(selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
