#!/usr/bin/env python3
"""Read-only fail-closed preflight for the registered v2 prospective signal protocol.

Runs *before* the existing, SHA-locked protocol. No model/selection code is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Mapping

import numpy as np

import joint_set_v2_signal_oos as shadow
import loto7_v4_runner as v4
from loto7_evolving_agent import make_history, read_csv_flexible

def _numbers(obj: object, count: int, field: str) -> List[int]:
    if isinstance(obj, str):
        raw = obj.replace(",", " ").split()
    elif isinstance(obj, (list, tuple)):
        raw = list(obj)
    else:
        raise ValueError(f"{field}: numbers missing")
    nums = [int(v) for v in raw]
    if len(nums) != count or len(set(nums)) != count or any(n < 1 or n > 37 for n in nums):
        raise ValueError(f"{field}: expected {count} distinct numbers from 1 to 37")
    return sorted(nums)

def validate_trusted_source(csv_path: Path, source_report: Path) -> Dict[str, object]:
    x, clean = make_history(read_csv_flexible(csv_path))
    if len(clean) == 0:
        raise ValueError("empty draw history")
    latest = clean.iloc[-1]
    round_no = v4.parse_round(latest["回別"]) or len(clean)
    verification, trusted = v4.source_info(source_report, round_no)
    if not trusted:
        # The locked protocol itself must wait for trusted source verification.
        return {"round": round_no, "trusted": False, "status": "untrusted_wait"}
    report = json.loads(source_report.read_text(encoding="utf-8"))
    published = report.get("latest")
    if not isinstance(published, dict):
        raise ValueError("trusted report has no latest result")
    date = latest["抽せん日"].date().isoformat()
    actual_main = [int(i) + 1 for i in np.flatnonzero(x[-1])]
    csv_main = _numbers(actual_main, 7, "csv.main")
    csv_bonus = _numbers(latest["ボーナス数字"], 2, "csv.bonus")
    published_main = _numbers(published.get("main"), 7, "report.latest.main")
    published_bonus = _numbers(published.get("bonus"), 2, "report.latest.bonus")
    if (int(published.get("round", -1)) != round_no
            or str(published.get("date")) != date
            or csv_main != published_main
            or csv_bonus != published_bonus):
        raise ValueError("trusted source report conflicts with latest CSV draw/date/bonus")
    sources = report.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("trusted report has no independently recorded source details")
    agreeing = []
    for name, rec in sources.items():
        if not isinstance(rec, dict) or not all(k in rec for k in ("round", "date", "main", "bonus")):
            continue
        try:
            if (int(rec["round"]) == round_no
                    and str(rec["date"]) == date
                    and _numbers(rec["main"], 7, f"{name}.main") == csv_main
                    and _numbers(rec["bonus"], 2, f"{name}.bonus") == csv_bonus):
                agreeing.append(name)
        except (ValueError, TypeError):
            continue
    if not agreeing:
        raise ValueError("trusted report has no matching secondary result-source record")
    return {"round": round_no, "trusted": True, "status": "verified_csv_matches_report_and_secondary", "secondary": agreeing}

def validate_existing_shadow(out_dir: Path) -> Dict[str, object]:
    registration = shadow.load_json(out_dir / shadow.REGISTRATION_NAME)
    if not registration:
        raise ValueError("prospective registration must exist on main before grade/freeze")
    # Strictly retain the existing model/protocol SHA lock.
    manifest = shadow.algorithm_manifest(
        Path(shadow.__file__).resolve(), Path("joint_set_v2_model.py"),
        Path("joint_set_v2_research.py"), shadow.MIN_TRAIN, shadow.SELECTION_WINDOW)
    shadow.validate_manifest(registration, manifest)
    state = shadow.load_json(out_dir / shadow.STATE_NAME)
    registry = shadow.load_json(out_dir / shadow.REGISTRY_NAME)
    history = shadow.read_freeze_history(out_dir / shadow.FREEZE_HISTORY_NAME)
    rows = shadow.read_result_rows(out_dir / shadow.RESULTS_NAME)
    graded = [int(n) for n in state.get("graded_rounds", [])]
    result_rounds = [int(row["round"]) for row in rows]
    if len(set(result_rounds)) != len(result_rounds) or graded != result_rounds:
        raise ValueError("state graded_rounds and immutable result rows differ")
    if int(state.get("trusted_draws", 0)) != len(rows):
        raise ValueError("trusted_draws count and result rows differ")
    if len(rows) > shadow.HORIZON_TRUSTED_DRAWS:
        raise ValueError("prospective horizon exceeded")
    if any(r < shadow.START_TARGET_ROUND for r in result_rounds):
        raise ValueError("an excluded/pre-registration draw was graded")
    if result_rounds and result_rounds != list(range(shadow.START_TARGET_ROUND, shadow.START_TARGET_ROUND + len(result_rounds))):
        raise ValueError("trusted result sequence has a gap")
    if history:
        hrounds = sorted(history)
        if hrounds != list(range(shadow.START_TARGET_ROUND, shadow.START_TARGET_ROUND + len(hrounds))):
            raise ValueError("freeze history has missing or retrospective targets")
        for ref in history.values():
            shadow.validate_registry(ref, registration)
            if ref.get("source_verification_at_freeze") != "verified_two_result_sources":
                raise ValueError("a freeze was created from untrusted source")
    if registry:
        shadow.validate_registry(registry, registration)
        target = int(registry["target_round"])
        if target not in history or history[target] != registry:
            raise ValueError("current registry differs from immutable freeze history")
        if state.get("current_target_round") != target:
            raise ValueError("state and registry current target differ")
    elif history or rows or int(state.get("trusted_draws", 0)):
        raise ValueError("started prospective shadow has a missing current registry")
    elif state.get("current_target_round") is not None:
        raise ValueError("current target exists without a frozen vector")
    return {"registration_locked": True, "trusted_draws": len(rows), "current_target": registry.get("target_round")}

def preflight(csv_path: Path, source_report: Path, out_dir: Path) -> Dict[str, object]:
    return {
        "source": validate_trusted_source(csv_path, source_report),
        "shadow": validate_existing_shadow(out_dir),
        "role": "read_only_guard_no_model_changes",
    }

def main() -> None:
    ap = argparse.ArgumentParser(description="Fail-closed preflight before Joint Set v2 prospective freeze/grade")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = ap.parse_args()
    print(json.dumps(preflight(args.csv, args.source_report, args.out_dir), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
