#!/usr/bin/env python3
"""Read-only deterministic role council for the LOTO7 AI agent.

Five independently scoped governance reviews, prioritized action handoffs, and a
machine-readable report. No code here publishes, grades, freezes or promotes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

from joint_set_v2_signal_oos import (
    algorithm_manifest, read_freeze_history, read_result_rows,
    validate_manifest, validate_registry,
)
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import make_history, read_csv_flexible
import loto7_v4_runner as v4

VERSION = "loto7-agent-role-council-v1"
JST = timezone(timedelta(hours=9))
LEVEL = {"ok": 0, "watch": 1, "block": 2}
ROLES = (
    "data_steward", "prospective_signal_custodian", "oos_risk_officer",
    "research_skeptic", "release_operations",
)
PERMISSIONS = {
    "read_repository_inputs": True,
    "write_own_diagnostic_report": True,
    "freeze_or_backfill": False,
    "grade_prospective_outcomes": False,
    "update_model_or_signal": False,
    "publish_production_tickets": False,
    "promote_champion": False,
}


def obj(path: Path, *, required: bool = True) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise ValueError("required file missing: " + str(path))
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("not a JSON object: " + str(path))
    return value


def finding(level: str, code: str, evidence: str, action: str = "Continue predeclared workflow.") -> dict:
    return {"level": level, "code": code, "evidence": evidence, "next_action": action}


def done(items: list) -> dict:
    return {"status": max((x["level"] for x in items), key=lambda x: LEVEL[x]), "findings": items}


def round_id(value: object) -> int:
    return int(v4.parse_round(value) or 0)


def pair_context_overflow_count(history: np.ndarray) -> int:
    """Audit legacy co-occurrence arithmetic without changing locked forecasts.

    The legacy expert multiplies an int8 history by its transpose, causing
    counts above 127 to wrap. Compare with exact int64 arithmetic.
    """
    h = np.asarray(history)
    if h.ndim != 2 or h.shape[1] != 37 or not np.issubdtype(h.dtype, np.integer):
        raise ValueError("expected 37-column integer draw history")
    if not np.all((h == 0) | (h == 1)):
        raise ValueError("draw history must contain binary indicators")
    legacy = h.T @ h
    wide = h.astype(np.int64, copy=False)
    exact = wide.T @ wide
    return int(np.count_nonzero(legacy.astype(np.int64) != exact))


def data_steward(root: Path, out: Path, now: datetime) -> dict:
    try:
        csv_file = root / "loto7.csv"
        x, clean = make_history(read_csv_flexible(csv_file))
        if len(x) == 0:
            raise ValueError("history is empty")
        latest = round_id(clean["回別"].iloc[-1])
        if latest < 1:
            raise ValueError("last draw has no valid identity")
        source = obj(out / "source_validation.json")
        status, trusted = v4.source_info(out / "source_validation.json", latest)
        findings = []
        if trusted:
            check = validate_trusted_source(csv_file, out / "source_validation.json")
            findings.append(finding(
                "ok", "TRUSTED_RESULT_EXACT_MATCH",
                "round=" + str(latest) + "; secondary=" + ",".join(check["secondary"]),
            ))
        else:
            findings.append(finding(
                "watch", "RESULT_NOT_TWO_SOURCE_VERIFIED",
                "round=" + str(latest) + "; status=" + status,
                "Use the existing source recovery workflow; no trusted OOS grading.",
            ))
        overflow_pairs = pair_context_overflow_count(x)
        if overflow_pairs:
            findings.append(finding(
                "watch", "PAIR_CONTEXT_INT8_OVERFLOW",
                f"corrupted_cooccurrence_cells={overflow_pairs}; history_draws={len(x)}",
                "Use a separately versioned, revalidated model before changing "
                "pair_context arithmetic. Do not rewrite frozen predictions.",
            ))
        checked_at = source.get("checked_at_jst")
        if checked_at:
            stamp = datetime.fromisoformat(str(checked_at))
            if stamp.tzinfo is None:
                raise ValueError("source timestamp missing timezone")
            hours = (now - stamp.astimezone(JST)).total_seconds() / 3600
            if hours < -1:
                raise ValueError("source validation timestamp is in the future")
            if hours > 48:
                findings.append(finding(
                    "watch", "SOURCE_REFRESH_OVERDUE", "last checked " + str(round(hours, 1)) + " hours ago",
                    "Run the existing validation workflow and check upstream result providers.",
                ))
        return done(findings)
    except Exception as exc:
        return done([finding(
            "block", "DATA_INTEGRITY_BLOCK", str(exc),
            "Investigate draw CSV and source verification; never grade a conflicting draw.",
        )])


def prospective_signal_custodian(root: Path, out: Path, latest: int, trusted: bool) -> dict:
    try:
        reg = obj(out / "joint_set_v2_signal_oos_registration.json")
        state = obj(out / "joint_set_v2_signal_oos_state.json")
        manifest = algorithm_manifest(
            root / "joint_set_v2_signal_oos.py", root / "joint_set_v2_model.py",
            root / "joint_set_v2_research.py",
        )
        validate_manifest(reg, manifest)
        if (reg.get("promotion_role") != "diagnostic_only"
                or int(reg["start_target_round"]) != 701
                or int(reg["horizon_trusted_draws"]) != 26
                or int(reg["excluded_already_frozen_target_round"]) != 700):
            raise ValueError("registered prospective policy changed")
        start = 701
        rows = read_result_rows(out / "joint_set_v2_signal_oos_results.csv")
        grades = [int(v) for v in state["graded_rounds"]]
        rounds = [int(r["round"]) for r in rows]
        if (rounds != grades or rounds != list(range(start, start + len(rounds)))
                or len(rows) != int(state["trusted_draws"]) or len(rows) > 26):
            raise ValueError("trusted results differ from contiguous 26-draw state")
        history = read_freeze_history(out / "joint_set_v2_signal_oos_freeze_history.jsonl")
        if sorted(history) != list(range(start, start + len(history))):
            raise ValueError("freeze history has a gap or unregistered draw")
        for rec in history.values():
            validate_registry(rec, reg)
            if rec.get("source_verification_at_freeze") != "verified_two_result_sources":
                raise ValueError("untrusted prefix used to freeze future draw")
        live = obj(out / "joint_set_v2_signal_oos_registry.json", required=False)
        if str(state.get("status", "")).startswith("invalid_"):
            raise ValueError("shadow is terminal fail-closed: " + str(state["status"]))
        if live:
            validate_registry(live, reg)
            target = int(live["target_round"])
            if history.get(target) != live or state.get("current_target_round") != target:
                raise ValueError("live registry changed or differs from freeze ledger")
            if target != start + len(rows) and len(rows) < 26:
                raise ValueError("freeze target is not the next unobserved draw")
            if latest > target:
                raise ValueError("missed prefrozen draw " + str(target))
        elif history or rows or state.get("current_target_round") is not None or latest >= start:
            raise ValueError("missing mandatory prospective frozen reference")
        findings = [finding(
            "ok", "V2_LOCK_AND_IMMUTABLE_HISTORY",
            "locked_manifest=" + str(manifest["manifest_sha256"])[:16]
            + "; trusted=" + str(len(rows)) + "/26; target=" + str(live.get("target_round")),
        )]
        if latest == 700 and trusted and not live:
            findings.append(finding(
                "watch", "FREEZE_701_NOW", "verified round 700 available, target 701 not frozen",
                "Dispatch the existing v2 signal freeze workflow before draw 701.",
            ))
        elif latest < 700 and not live:
            findings.append(finding("ok", "WAIT_FOR_700", "round 700 not resolved; do not freeze 701 yet"))
        if len(rows) == 26:
            findings.append(finding("ok", "FIXED_HORIZON_COMPLETE", "26/26; no automatic promotion"))
        return done(findings)
    except Exception as exc:
        return done([finding(
            "block", "PROSPECTIVE_LOCK_BLOCK", str(exc),
            "Do not backfill or retune; inspect SHA manifest and append-only prospective ledger.",
        )])


def oos_risk_officer(out: Path, latest: int) -> dict:
    try:
        champion = obj(out / "model_champion.json")
        holdout = obj(out / "future_holdout_state.json")
        frozen = obj(out / "future_holdout_registry.json")
        shadow = obj(out / "shadow_registry.json")
        formal = obj(out / "formal_challenger_state.json")
        version = champion["model_version"]
        if (shadow.get("champion_version") != version
                or frozen.get("champion_version") != version
                or formal.get("champion_version") != version):
            raise ValueError("official Champion and prefrozen references disagree")
        if holdout.get("protocol_lock_status") != "verified":
            raise ValueError("26-draw protocol SHA lock not verified")
        n, h = int(holdout["trusted_draws"]), int(holdout["horizon_trusted_draws"])
        graded = [int(v) for v in holdout["graded_rounds"]]
        if n < 0 or n > h or graded != list(range(int(holdout["start_target_round"]), int(holdout["start_target_round"]) + n)):
            raise ValueError("26-draw holdout graded rounds are noncontiguous or inconsistent")
        target = int(frozen["target_round"])
        if target != int(shadow["target_round"]) or target < latest + 1:
            raise ValueError("Production OOS registries have inconsistent or missed freeze target")
        if frozen.get("locked_candidate_version") != holdout.get("locked_candidate_version"):
            raise ValueError("holdout candidate was changed")
        findings = [finding(
            "ok", "OOS_REFERENCE_CONSISTENCY", "champion=" + str(version) + "; frozen="
            + str(target) + "; trusted=" + str(n) + "/" + str(h),
        )]
        if n < h:
            findings.append(finding(
                "watch", "NO_EARLY_PORTFOLIO_CLAIM", "holdout=" + str(n) + "/" + str(h),
                "Keep all comparator evidence and wait until 26/26 for independent confirmation.",
            ))
        else:
            findings.append(finding(
                "watch", "HOLDOUT_CLAIM_REVIEW_REQUIRED", "26/26 observed",
                "Use the existing fixed-horizon evidence policy; this role cannot promote.",
            ))
        return done(findings)
    except Exception as exc:
        return done([finding(
            "block", "OOS_GOVERNANCE_BLOCK", str(exc),
            "Investigate Champion, frozen references, and prospective holdout before operational use.",
        )])


def research_skeptic(out: Path) -> dict:
    try:
        guard = obj(out / "research_cycle_guard.json")
        audit = obj(out / "joint_set_v2_conversion_audit_summary.json")
        if (audit.get("research_only") is not True or audit.get("independent_evidence") is not False
                or audit.get("promotion_eligible") is not False):
            raise ValueError("reused historical research mislabeled as prospective or promotable")
        used, budget = int(guard["signal_trials_this_data"]), int(guard["max_signal_trials_per_data"])
        mode = str(guard["mode"])
        if budget <= 0 or used < 0 or used > budget or mode not in (
            "SEARCH", "VALIDATION_ONLY", "WAIT_FOR_NEW_DATA"
        ):
            raise ValueError("research budget or trial phase invalid")
        findings = [finding(
            "ok", "DIAGNOSTIC_RESEARCH_ISOLATION",
            "history reused; mode=" + mode + "; trials=" + str(used) + "/" + str(budget),
        )]
        if mode == "SEARCH" and used >= 0.80 * budget:
            findings.append(finding(
                "watch", "RESEARCH_TRIAL_LIMIT_APPROACHING",
                "draw-specific exploration consumed " + str(used) + "/" + str(budget),
                "Honor existing plateau guard, then validate or wait for genuinely new data.",
            ))
        return done(findings)
    except Exception as exc:
        return done([finding(
            "block", "RESEARCH_EVIDENCE_BOUNDARY_BLOCK", str(exc),
            "Keep historical studies diagnostic and verify predeclared search budget.",
        )])


def release_operations(out: Path, latest: int, now: datetime) -> dict:
    try:
        publisher = obj(out / "weekly_production_prediction_state.json")
        source = obj(out / "source_validation.json")
        schedule = source.get("sources", {}).get("official_schedule", {})
        target = latest + 1
        if int(schedule.get("round", -1)) != target or not schedule.get("date"):
            return done([finding(
                "watch", "DRAW_SCHEDULE_NOT_VERIFIED", "expected target=" + str(target),
                "Verify the official next draw date; do not infer publishing deadlines.",
            )])
        deadline = datetime.fromisoformat(str(schedule["date"]) + "T20:00:00+09:00")
        already_published = bool(publisher.get("published")) and round_id(publisher.get("target_round")) == target
        if now >= deadline and not already_published:
            return done([finding(
                "block", "PRODUCTION_DEADLINE_PASSED", "missing verified pre-draw publication for " + str(target),
                "Investigate existing publisher; never retroactively publish a lottery ticket.",
            )])
        return done([finding(
            "ok", "RELEASE_SCHEDULE_GUARD", "next=" + str(target) + " on "
            + str(schedule["date"]) + "; already_published=" + str(already_published),
        )])
    except Exception as exc:
        return done([finding(
            "block", "RELEASE_GOVERNANCE_BLOCK", str(exc),
            "Inspect existing weekly Production publisher and official source schedule.",
        )])


def evaluate(root: Path, now: Optional[datetime] = None) -> dict:
    root = root.resolve()
    now = (now or datetime.now(JST)).astimezone(JST)
    out = root / "loto7_agent_output"
    try:
        _, clean = make_history(read_csv_flexible(root / "loto7.csv"))
        latest = round_id(clean["回別"].iloc[-1])
    except Exception:
        latest = -1
    source = obj(out / "source_validation.json", required=False)
    trusted = (
        source.get("status") == "ok"
        and source.get("verification") == "verified_two_result_sources"
        and int((source.get("latest") or {}).get("round", -2)) == latest
    )
    roles = {
        "data_steward": data_steward(root, out, now),
        "prospective_signal_custodian": prospective_signal_custodian(root, out, latest, trusted),
        "oos_risk_officer": oos_risk_officer(out, latest),
        "research_skeptic": research_skeptic(out),
        "release_operations": release_operations(out, latest, now),
    }
    assert tuple(roles) == ROLES
    handoffs = [{
        "priority": priority, "owner": owner,
        "issue_code": item["code"], "evidence": item["evidence"],
        "next_action": item["next_action"],
        "existing_workflow_or_human_required": True,
        "autonomous_production_write_allowed": False,
    } for priority in ("block", "watch") for owner in ROLES
        for item in roles[owner]["findings"] if item["level"] == priority]
    tracked = [
        root / "loto7.csv", root / "joint_set_v2_signal_oos.py",
        root / "joint_set_v2_model.py", root / "joint_set_v2_research.py",
        *(out / s for s in (
            "source_validation.json", "model_champion.json", "shadow_registry.json",
            "future_holdout_state.json", "future_holdout_registry.json",
            "joint_set_v2_signal_oos_registration.json", "joint_set_v2_signal_oos_state.json",
            "joint_set_v2_signal_oos_registry.json", "research_cycle_guard.json",
            "joint_set_v2_conversion_audit_summary.json", "weekly_production_prediction_state.json",
        )),
    ]
    snapshot = [
        [str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"]
        for path in sorted(tracked)
    ]
    sha = hashlib.sha256(json.dumps(snapshot, separators=(",", ":")).encode()).hexdigest()
    return {
        "version": VERSION, "checked_at_jst": now.isoformat(timespec="seconds"),
        "latest_resolved_round": latest,
        "overall": max((r["status"] for r in roles.values()), key=lambda s: LEVEL[s]),
        "input_snapshot_sha256": sha,
        "governance": {
            "authority": "read_only_advisory", "permissions": PERMISSIONS,
            "auto_actions_taken": [], "production_promotion_eligible": False,
        },
        "roles": roles, "handoff_tasks": handoffs,
    }


def render_report(report: Mapping[str, Any]) -> str:
    lines = [
        "# LOTO7 AI Agent — Role Council",
        "",
        "- checked JST: **" + str(report["checked_at_jst"]) + "**",
        "- latest round: **" + str(report["latest_resolved_round"]) + "**",
        "- overall: **" + str(report["overall"]).upper() + "**",
        "- input snapshot SHA256: " + str(report["input_snapshot_sha256"]),
        "- **Read-only advice; never promote, publish, freeze or backfill.**",
        "",
        "## Role checks",
        "| Role | Verdict | Checks |",
        "|---|---|---|",
    ]
    for key in ROLES:
        entry = report["roles"][key]
        lines.append("| " + key + " | " + entry["status"].upper() + " | "
                     + ", ".join(f["code"] for f in entry["findings"]) + " |")
    lines.extend(["", "## Prioritized handoffs"])
    for t in report["handoff_tasks"]:
        lines.extend([
            "### " + t["priority"].upper() + " — " + t["owner"] + ": " + t["issue_code"],
            "- evidence: " + t["evidence"],
            "- next action: " + t["next_action"],
            "- executor: **existing workflow / human review only**", "",
        ])
    if not report["handoff_tasks"]:
        lines.append("No handoffs; existing registered workflows continue.")
    lines.extend([
        "", "This is a deterministic role-based auditor, not five independent trained AIs.",
        "It has no authority to update the registered model or interpret reused historical data as new evidence.",
        "",
    ])
    return "\n".join(lines)


def run(root: Path, output_dir: Path, now: Optional[datetime] = None) -> dict:
    result = evaluate(root, now)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "agent_role_council_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "agent_role_council_report.md").write_text(
        render_report(result), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only role council for LOTO7 AI_AGENT")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    parser.add_argument("--fail-on-blocker", action="store_true")
    args = parser.parse_args()
    result = run(args.repo_root, args.out_dir)
    print(json.dumps({"overall": result["overall"], "handoffs": len(result["handoff_tasks"]),
                      "role_statuses": {k: v["status"] for k, v in result["roles"].items()}},
                     ensure_ascii=False))
    return 2 if args.fail_on_blocker and result["overall"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
