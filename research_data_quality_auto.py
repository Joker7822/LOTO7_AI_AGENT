#!/usr/bin/env python3
"""Automatic data-quality audit with narrow, existing-workflow recovery requests.

No draw result is edited or invented, and no prospective evidence, model,
budget or Production files are written. On a genuine overdue official draw
the only authorized source recovery is the existing Friday watchdog; for a
trusted draw with a stale registered scientific report, the existing lab.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source, _numbers
from loto7_evolving_agent import make_history, read_csv_flexible
import loto7_v4_runner as v4

VERSION = "autonomous-data-quality-recovery-v1"
JST = timezone(timedelta(hours=9))
OUTPUT = "research_data_quality_auto_report.json"
MARKDOWN = "research_data_quality_auto_report.md"
MIN_POST_DRAW_DELAY_MINUTES = 30
ALLOWED_RECOVERY = {
    "friday_result_check_watchdog.yml", "advanced_validation_lab.yml",
    "always_on_accuracy_research.yml"
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid independent research data-quality input")
    return value


def audit(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    files = {
        "draw": root / "loto7.csv",
        "source": out / "source_validation.json",
        "guard": out / "research_cycle_guard.json",
        "science": out / "advanced_validation_lab_summary.json",
        "queue": out / "research_autonomy_priority_queue.json",
        "bibliography": out / "research_verified_publications.json",
    }
    before = {k: sha(p) for k, p in files.items()}
    now = (now or datetime.now(JST)).astimezone(JST)
    raw = read_csv_flexible(files["draw"])
    x, clean = make_history(raw)
    if len(x) < 20 or not np.all(x.sum(axis=1) == 7):
        raise ValueError("historical main numbers invalid")
    rounds = [v4.parse_round(v) for v in clean["回別"]]
    if rounds != list(range(1, len(x) + 1)):
        raise ValueError("missing, repeated or reordered draw rounds")
    dates = [v.date() for v in clean["抽せん日"]]
    if dates != sorted(set(dates)):
        raise ValueError("duplicate or nonmonotone historical draw dates")
    for i in range(len(x)):
        bonus = _numbers(clean.iloc[i]["ボーナス数字"], 2, "historical bonus")
        main = {int(j) + 1 for j in np.flatnonzero(x[i])}
        if set(bonus) & main:
            raise ValueError("historical bonus overlaps main numbers")
    status = validate_trusted_source(files["draw"], files["source"])
    source = load(files["source"])
    guard = load(files["guard"])
    science = load(files["science"])
    queue = load(files["queue"])
    biblio = load(files["bibliography"])
    latest = len(x)
    if status.get("round") != latest:
        raise ValueError("latest independently checked round disagrees with history")
    verified = (status.get("trusted") is True
                and source.get("verification") == "verified_two_result_sources"
                and source.get("verification_provenance", {}).get("draw_csv_sha256")
                    == before["draw"])
    if guard.get("mode") not in {"WAIT_FOR_NEW_DATA", "VALIDATION_ONLY", "SEARCH"}:
        raise ValueError("invalid bound research budget")
    trials = guard.get("signal_trials_this_data")
    limit = guard.get("max_signal_trials_per_data")
    if (type(trials) is not int or type(limit) is not int or
            trials < 0 or limit < trials):
        raise ValueError("research trial budget inconsistent")

    official = source.get("sources", {}).get("official_schedule", {})
    if not isinstance(official, dict):
        raise ValueError("invalid official schedule")
    target = official.get("round")
    due_date = official.get("date")
    if type(target) is not int or target < latest or target > latest + 1:
        raise ValueError("unexpected official schedule target")
    if not isinstance(due_date, str):
        raise ValueError("missing official schedule date")
    scheduled_day = date.fromisoformat(due_date)
    if scheduled_day.weekday() != 4:
        raise ValueError("official lottery schedule does not name a Friday")
    due = datetime.combine(
        scheduled_day, time(20, 0), JST
    ) + timedelta(minutes=MIN_POST_DRAW_DELAY_MINUTES)
    overdue = (target == latest + 1 and now >= due)
    next_draw_wait = (target == latest + 1 and now < due)
    issues = []
    if not verified:
        issues.append("SOURCE_TWO_PROVIDER_CONFIRMATION_REQUIRED")
    if overdue:
        issues.append("OFFICIAL_RESULT_PAST_DUE")
    if guard.get("data_sha256") != before["draw"]:
        issues.append("RESEARCH_BUDGET_GUARD_STALE")
    if science.get("historical_data_sha256") != before["draw"]:
        issues.append("REGISTERED_SCIENCE_OUTDATED")

    queue_source_sha = queue.get("input_evidence_sha256", {}).get("source")
    queue_pub_sha = queue.get("input_evidence_sha256", {}).get("bibliography")
    if (queue.get("version") != "research-priority-orchestrator-v1"
            or queue.get("draw_history_sha256") != before["draw"]
            or queue_source_sha != before["source"]
            or queue_pub_sha != before["bibliography"]):
        issues.append("REGENERATE_PRIORITY_QUEUE_AFTER_SOURCE_UPDATE")
    tasks = queue.get("tasks")
    if not isinstance(tasks, list) or len(tasks) > 25:
        raise ValueError("invalid bounded priority queue")
    if (queue.get("authority", {}).get("production_or_champion_update") is not False
            or queue.get("authority", {}).get("workflows_dispatched") is not False
            or any(not isinstance(x, dict) or
                   x.get("forecast_or_production_change_authorized") is not False or
                   x.get("new_optimizer_trials_authorized") is not False
                   for x in tasks)):
        raise ValueError("priority queue attempts forbidden model authority")

    # Dispatch instructions are derived ONLY from hardcoded enums and locally
    # verified public draw schedules; never execute priority task text.
    recovery = None
    if overdue:
        recovery = "friday_result_check_watchdog.yml"
    elif (verified and guard.get("data_sha256") == before["draw"]
          and "REGISTERED_SCIENCE_OUTDATED" in issues):
        recovery = "advanced_validation_lab.yml"
    elif (verified and guard.get("data_sha256") == before["draw"]
          and science.get("historical_data_sha256") == before["draw"]
          and "REGENERATE_PRIORITY_QUEUE_AFTER_SOURCE_UPDATE" in issues):
        recovery = "always_on_accuracy_research.yml"
    if recovery is not None and recovery not in ALLOWED_RECOVERY:
        raise AssertionError("unallowlisted recovery workflow")
    if before != {k: sha(p) for k, p in files.items()}:
        raise ValueError("evidence changed during quality audit")
    return {
        "version": VERSION,
        "checked_at_jst": now.isoformat(timespec="seconds"),
        "latest_verified_round": latest if verified else None,
        "latest_history_round": latest,
        "historical_rows_checked": len(x),
        "main_number_invalid": 0,
        "bonus_number_invalid_or_overlapping": 0,
        "duplicate_or_missing_rounds": 0,
        "source_two_independently_verified": verified,
        "next_official_round": target,
        "next_official_draw_date": due_date,
        "result_available_after_jst": due.isoformat(timespec="seconds"),
        "before_next_draw_result_deadline": next_draw_wait,
        "quality_issues": issues,
        "research_queue_tasks": len(tasks),
        "candidate_priority_queue_stale": (
            "REGENERATE_PRIORITY_QUEUE_AFTER_SOURCE_UPDATE" in issues
        ),
        "requested_recovery_workflow": recovery,
        "recovery_request_is_recommendation_until_actions_dispatches": True,
        "source_sha256": before,
        "research_mode": guard["mode"],
        "same_data_trials_used": trials,
        "same_data_trial_limit": limit,
        "auto_corrected_lottery_numbers": False,
        "new_optimizer_trials": 0,
        "production_or_champion_modified": False,
        "registered_future_oos_modified": False,
        "quality_condition": ("attention" if issues else "checked_healthy"),
    }


def markdown(report: dict) -> str:
    body = [
        "# Autonomous research data-quality audit",
        "",
        f"- Checked: {report['checked_at_jst']}",
        f"- Draw history: 1..{report['latest_history_round']}; rows={report['historical_rows_checked']}",
        f"- Two independent published sources matched: {report['source_two_independently_verified']}",
        f"- Next official result deadline: {report['result_available_after_jst']}",
        f"- Awaiting scheduled draw without error: {report['before_next_draw_result_deadline']}",
        f"- Status: {report['quality_condition']}",
        f"- Allowed existing recovery workflow: {report['requested_recovery_workflow'] or 'none'}",
        "", "## Current issues",
    ]
    body.extend("- " + x for x in report["quality_issues"])
    if not report["quality_issues"]:
        body.append("- None; no data repairs are needed.")
    body += [
        "", "No invented draw numbers, second-source attestations or historical",
        "backfills. Dispatch is handled by GitHub Actions with a cooldown;",
        "the auditor itself cannot modify source CSV, Champion or OOS.",
    ]
    return "\n".join(body) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    p.add_argument("--github-output", type=Path)
    opts = p.parse_args()
    data = audit(opts.repo_root)
    opts.out_dir.mkdir(parents=True, exist_ok=True)
    (opts.out_dir / OUTPUT).write_text(json.dumps(
        data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    (opts.out_dir / MARKDOWN).write_text(markdown(data), encoding="utf-8")
    if opts.github_output is not None:
        with opts.github_output.open("a", encoding="utf-8") as file:
            file.write("recovery_workflow=" +
                       (data["requested_recovery_workflow"] or "") + "\n")
    print(json.dumps({
        "condition": data["quality_condition"],
        "issues": data["quality_issues"],
        "recovery": data["requested_recovery_workflow"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
