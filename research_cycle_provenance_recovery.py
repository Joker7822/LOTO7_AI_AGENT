#!/usr/bin/env python3
"""Read-only recovery preflight for the hourly bounded research cycle.

The core historical 26/60-draw experiments and 800-trial gate are NEVER
reset here. We report which existing scientific dependency is behind the
independently verified draw CSV, so the registered advanced-validation job
can repair its own report BEFORE the hourly research ledger resumes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from joint_set_v2_signal_oos_guard import validate_trusted_source

VERSION = "research-cycle-provenance-recovery-v1"
MODES = {"SEARCH", "VALIDATION_ONLY", "WAIT_FOR_NEW_DATA"}


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid research health evidence object")
    return data


def check(root: Path) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    csv = root / "loto7.csv"
    report = out / "source_validation.json"
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    trust = validate_trusted_source(csv, report)
    guard = _read(out / "research_cycle_guard.json")
    science = _read(out / "advanced_validation_lab_summary.json")
    source = _read(report)
    mode = guard.get("mode")
    if mode not in MODES:
        raise ValueError("unknown research-budget mode; refuse to resume")
    rounds = source.get("latest", {}).get("round")
    if type(rounds) is not int or rounds < 1 or trust.get("round") != rounds:
        raise ValueError("latest result round mismatch in source report")
    trusted = trust.get("trusted") is True
    # The source CSV itself is NOT enough: its separately recorded SHA and
    # real two-result-source proof must agree. No unverified experiment runs.
    source_sha = source.get("verification_provenance", {}).get("draw_csv_sha256")
    if not trusted or source_sha != digest:
        state = "WAIT_FOR_INDEPENDENT_SOURCE"
    elif guard.get("data_sha256") != digest:
        state = "WAIT_FOR_RESEARCH_GUARD"
    elif science.get("historical_data_sha256") != digest:
        state = "REFRESH_REGISTERED_SCIENCE"
    elif science.get("source_code_frozen") is not True or (
            science.get("automatic_model_selection") is not False or
            science.get("production_changed") is not False or
            science.get("champion_changed") is not False or
            science.get("registered_existing_shadows_changed") is not False):
        state = "INVALID_SCIENTIFIC_REVIEW"
    else:
        state = "READY_FOR_BOUNDED_RESEARCH"
    return {
        "version": VERSION,
        "status": state,
        "latest_resolved_round": rounds,
        "source_trusted": trusted and source_sha == digest,
        "draw_csv_sha256": digest,
        "guard_data_sha256": guard.get("data_sha256"),
        "science_data_sha256": science.get("historical_data_sha256"),
        "research_mode": mode,
        "trial_budget_used": guard.get("signal_trials_this_data"),
        "trial_budget_limit": guard.get("max_signal_trials_per_data"),
        "new_optimizer_trials_authorized": False,
        "registered_26_draw_state_modified": False,
        "production_champion_modified": False,
        "hourly_ledger_can_advance": state == "READY_FOR_BOUNDED_RESEARCH",
        "needs_registered_lab_refresh": state == "REFRESH_REGISTERED_SCIENCE",
        "expected_wait": (mode == "WAIT_FOR_NEW_DATA"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = check(args.repo_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write("ready=" + ("true" if result["hourly_ledger_can_advance"] else "false") + "\n")
            stream.write("status=" + result["status"] + "\n")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write("## Research cycle science provenance\n\n")
            stream.write(f"- State: **{result['status']}**\n")
            stream.write(f"- Independently verified draw: **#{result['latest_resolved_round']}**\n")
            stream.write(f"- Mode: **{result['research_mode']}**, trials {result['trial_budget_used']}/{result['trial_budget_limit']}\n")
            stream.write(f"- Registered science summary matches draw SHA: **{result['science_data_sha256'] == result['draw_csv_sha256']}**\n")
            stream.write("- No Production, historical lottery results, Champion or prospective evidence changed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
