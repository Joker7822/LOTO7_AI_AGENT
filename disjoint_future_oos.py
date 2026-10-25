#!/usr/bin/env python3
"""Separate, fail-closed prospective OOS for uniform 35-number coverage.

Never publishes purchased tickets, alters Production, or changes existing
registered 26-draw OOS. Files in research/disjoint_future_oos are append-only;
old freeze and grading records are verified and never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

import balanced_uniform_portfolio as geometry
import signal_portfolio_factorial as metrics
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import make_history, read_csv_flexible

VERSION = "disjoint-geometry-prospective-oos-v1"
START = 701
HORIZON = 26
ROOT = Path("research/disjoint_future_oos")
REGISTRATION = "registration.json"
JST = ZoneInfo("Asia/Tokyo")
DRAW_CUTOFF = time(18, 0)  # Friday pre-draw; fail closed when late.
FINGERPRINT_KEYS = ("algorithm_blob_sha1", "protocol_blob_sha1")


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"{path}: object expected")
    return result


def register_guard(reg: dict, protocol_path: Path, algorithm_path: Path) -> None:
    if (reg.get("protocol_version") != VERSION or reg.get("first_target") != START
            or reg.get("horizon_trusted_draws") != HORIZON
            or reg.get("registered_latest_verified_round") != START - 1
            or reg.get("candidate_version") != geometry.VERSION
            or reg.get("promotion_role") != "research_only_not_eligible"
            or reg.get("first_target_draw_date") != "2026-10-30"
            or reg.get("primary_endpoint") != "fixed_26_mean_paired_composite_score_delta_vs_uniform_random"
            or reg.get("no_interim_tuning") is not True
            or reg.get("auto_promotion") is not False):
        raise ValueError("prospective registration altered or incomplete")
    if type(reg.get("base_seed")) is not int:
        raise ValueError("fixed integer seed required")
    for key, path in (("protocol_blob_sha1", protocol_path),
                      ("algorithm_blob_sha1", algorithm_path)):
        if reg.get(key) != git_blob_sha1(path):
            raise RuntimeError(f"{key}: immutable implementation changed")
    data_hash = reg.get("registered_draw_csv_sha256")
    if not isinstance(data_hash, str) or len(data_hash) != 64:
        raise ValueError("registration missing original draw data fingerprint")


def random_control(seed: int) -> list[tuple[int, ...]]:
    """Five distinct, independently uniform 7-number sets; fixed seed."""
    rng = np.random.default_rng(seed)
    tickets = []
    seen = set()
    while len(tickets) < 5:
        ticket = tuple(sorted(int(n + 1) for n in rng.choice(
            np.arange(37), size=7, replace=False
        )))
        if ticket not in seen:
            tickets.append(ticket)
            seen.add(ticket)
    return tickets


def ticket_seed(reg: dict, target: int) -> int:
    return int(reg["base_seed"]) + int(target) * 1009 + 1_000_000


def proposed_freeze(reg: dict, target: int, prior_sha: str,
                    draw_date: str) -> dict:
    if not START <= target < START + HORIZON:
        raise ValueError("target exceeds separately registered horizon")
    seed = ticket_seed(reg, target)
    disjoint = geometry.disjoint_portfolio(seed)
    uniform = random_control(seed + 44_3322)
    return {
        "protocol_version": VERSION,
        "candidate_model": reg["candidate_version"],
        "target_round": target,
        "draw_date": draw_date,
        "verified_parent_round": target - 1,
        "parent_draw_csv_sha256": prior_sha,
        "registration_sha256": digest(reg),
        "candidate_seed": seed,
        "candidate_tickets": [list(t) for t in disjoint],
        "random_reference_seed": seed + 44_3322,
        "random_reference_tickets": [list(t) for t in uniform],
        "role": "shadow_research_only_not_for_purchase",
        "pre_outcome_freeze": True,
        "promotion_authorized": False,
    }


def freeze_path(root: Path, target: int) -> Path:
    return root / f"freeze_{target:04d}.json"


def grade_path(root: Path, target: int) -> Path:
    return root / f"grade_{target:04d}.json"


def metrics_for(freeze: dict, actual: list[int]) -> dict:
    actual_set = set(actual)
    return {
        "candidate": metrics.ticket_metrics(
            [tuple(t) for t in freeze["candidate_tickets"]], actual_set
        ),
        "random_reference": metrics.ticket_metrics(
            [tuple(t) for t in freeze["random_reference_tickets"]], actual_set
        ),
    }


def grade_record(reg: dict, freeze: dict, actual: list[int],
                 source_sha: str, source_report_sha: str) -> dict:
    scores = metrics_for(freeze, actual)
    return {
        "protocol_version": VERSION,
        "target_round": freeze["target_round"],
        "freeze_sha256": digest(freeze),
        "actual_main_numbers": list(actual),
        "result_source": "verified_two_result_sources",
        "graded_draw_csv_sha256": source_sha,
        "source_validation_sha256": source_report_sha,
        "candidate": scores["candidate"],
        "random_reference": scores["random_reference"],
        "paired_composite_delta": (
            scores["candidate"]["score"] - scores["random_reference"]["score"]
        ),
        "promotion_authorized": False,
        "independent_evidence_of_predictive_skill": False,
    }


def validate_freeze(reg: dict, freeze: dict) -> None:
    target = freeze.get("target_round")
    if type(target) is not int or not START <= target < START + HORIZON:
        raise ValueError("invalid prefrozen target")
    actual = proposed_freeze(reg, target, freeze.get("parent_draw_csv_sha256"),
                             freeze.get("draw_date"))
    if actual != freeze:
        raise ValueError(f"freeze {target} differs from deterministic protocol")
    geometry.validate_portfolio([tuple(t) for t in freeze["candidate_tickets"]])
    if len(set(tuple(t) for t in freeze["random_reference_tickets"])) != 5:
        raise ValueError("random reference is not five distinct tickets")


def archive_guard(root: Path, reg: dict) -> tuple[dict, dict]:
    freezes = {}
    grades = {}
    for path in sorted(root.glob("freeze_*.json")):
        obj = load(path)
        target = obj.get("target_round")
        if path != freeze_path(root, target):
            raise ValueError("inconsistent freeze filename")
        validate_freeze(reg, obj)
        freezes[target] = obj
    for path in sorted(root.glob("grade_*.json")):
        obj = load(path)
        target = obj.get("target_round")
        if path != grade_path(root, target):
            raise ValueError("inconsistent grade filename")
        grades[target] = obj
    fids = sorted(freezes)
    gids = sorted(grades)
    if fids != list(range(START, START + len(fids))):
        raise ValueError("missing or retroactive freeze")
    if gids != list(range(START, START + len(gids))):
        raise ValueError("missing or retroactive grade")
    if not fids or len(gids) > len(fids):
        raise ValueError("no valid future prefrozen chain")
    for target, grade in grades.items():
        if target not in freezes:
            raise ValueError("graded a never-frozen draw")
        freeze = freezes[target]
        main = grade.get("actual_main_numbers")
        if (not isinstance(main, list) or len(main) != 7
                or len(set(main)) != 7 or any(type(n) is not int or n < 1 or n > 37
                                              for n in main)):
            raise ValueError("invalid graded numbers")
        expected = grade_record(
            reg, freeze, main, grade.get("graded_draw_csv_sha256"),
            grade.get("source_validation_sha256")
        )
        if expected != grade:
            raise ValueError(f"grade {target} is not reproducible")
    for target, freeze in freezes.items():
        if target == START:
            if (freeze["parent_draw_csv_sha256"] != reg["registered_draw_csv_sha256"]
                    or freeze["draw_date"] != reg["first_target_draw_date"]):
                raise ValueError("initial registration data or schedule altered")
        elif target - 1 not in grades:
            raise ValueError("freeze made before predecessor was trusted/graded")
        elif freeze["parent_draw_csv_sha256"] != grades[target - 1]["graded_draw_csv_sha256"]:
            raise ValueError("freeze chain does not match preceding trusted draw")
    if len(fids) > len(gids) + 1:
        raise ValueError("more than one pending frozen draw")
    return freezes, grades


def verified_latest(csv_path: Path, source_path: Path) -> tuple[int, list[int], str, dict]:
    info = validate_trusted_source(csv_path, source_path)
    if not info["trusted"]:
        raise RuntimeError("wait: result has not passed independent source verification")
    source = load(source_path)
    latest = source["latest"]
    x, df = make_history(read_csv_flexible(csv_path))
    row = df.iloc[-1]
    target = int("".join(ch for ch in str(row["回別"]) if ch.isdigit()))
    if len(x) != target or info["round"] != target:
        raise ValueError("history draw numbers must be strictly contiguous from 1")
    csv_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    provenance = source.get("verification_provenance") or {}
    if provenance.get("draw_csv_sha256") != csv_sha:
        raise RuntimeError("source-verification CSV fingerprint mismatch")
    actual = (np.flatnonzero(x[-1]) + 1).astype(int).tolist()
    if actual != sorted(latest.get("main", [])):
        raise RuntimeError("trusted source and CSV main values differ")
    return target, actual, csv_sha, source


def ensure_cutoff(schedule_date: str, now: datetime) -> None:
    draw_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
    cutoff = datetime.combine(draw_date, DRAW_CUTOFF, tzinfo=JST)
    if now.astimezone(JST) >= cutoff:
        raise RuntimeError("refuse to freeze on/after the 18:00 JST draw-day cutoff")


def write_new(path: Path, obj: dict) -> None:
    if path.exists():
        raise RuntimeError(f"immutable file already exists: {path}")
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")


def advance(root: Path, reg: dict, csv_path: Path, source_path: Path,
            *, now: datetime | None = None) -> dict:
    """Append at most one *trusted* grade and one subsequent freeze.

    Missing/old source verification is a non-mutating wait. Any inconsistency
    or missing required frozen prediction fails closed (no backfilling).
    """
    now = now or datetime.now(JST)
    freezes, grades = archive_guard(root, reg)
    pending = START + len(grades)
    if pending >= START + HORIZON:
        return {"status": "completed", "graded": len(grades)}
    info, main, sha, source = verified_latest(csv_path, source_path)
    if info == pending - 1 and pending not in freezes:
        # A previously graded round may not have had a verified next-draw
        # schedule yet. Recovery may ONLY freeze the next unobserved round,
        # never reconstruct the already observed result.
        if pending == START or pending - 1 not in grades:
            raise RuntimeError("cannot create an unfounded freeze")
        schedule = (source.get("sources") or {}).get("official_schedule") or {}
        if int(schedule.get("round", -1)) != pending:
            return {"status": "awaiting_official_schedule", "target": pending,
                    "graded": len(grades)}
        date_value = schedule.get("date")
        if not isinstance(date_value, str):
            return {"status": "awaiting_official_schedule", "target": pending,
                    "graded": len(grades)}
        try:
            ensure_cutoff(date_value, now)
        except (ValueError, RuntimeError):
            return {"status": "freeze_cutoff_passed_no_backfill", "target": pending,
                    "graded": len(grades)}
        write_new(freeze_path(root, pending),
                  proposed_freeze(reg, pending, sha, date_value))
        return {"status": "new_future_target_prefrozen", "target": pending,
                "graded": len(grades)}
    if info < pending:
        return {"status": "waiting_for_future_result", "target": pending,
                "graded": len(grades)}
    if info > pending:
        raise RuntimeError("latest draw is ahead of frozen target: no backfill")
    if pending not in freezes:
        raise RuntimeError("target was not prefrozen: refuse retrospective grade")
    if grade_path(root, pending).exists():
        raise RuntimeError("attempted overwrite of immutable grade")
    graded = grade_record(
        reg, freezes[pending], main, sha,
        hashlib.sha256(source_path.read_bytes()).hexdigest()
    )
    write_new(grade_path(root, pending), graded)
    following = pending + 1
    outcome = {"status": "trusted_graded", "target": pending,
               "graded": len(grades) + 1}
    if following >= START + HORIZON:
        outcome["status"] = "horizon_complete_ready_for_fixed_analysis"
        return outcome
    schedule = (source.get("sources") or {}).get("official_schedule") or {}
    if int(schedule.get("round", -1)) != following:
        outcome["next_freeze_status"] = "awaiting_verified_official_next_schedule"
        return outcome
    scheduled_date = schedule.get("date")
    if not isinstance(scheduled_date, str):
        outcome["next_freeze_status"] = "awaiting_verified_official_next_schedule"
        return outcome
    try:
        ensure_cutoff(scheduled_date, now)
    except (RuntimeError, ValueError):
        outcome["next_freeze_status"] = "not_prefrozen_before_safe_cutoff"
        return outcome
    if freeze_path(root, following).exists():
        raise RuntimeError("attempted overwrite of immutable forecast")
    write_new(freeze_path(root, following),
              proposed_freeze(reg, following, sha, scheduled_date))
    outcome["next_freeze_status"] = "prefrozen_for_future_result"
    outcome["next_target"] = following
    return outcome


def summary(root: Path, reg: dict) -> dict:
    freezes, grades = archive_guard(root, reg)
    rows = [grades[t] for t in sorted(grades)]
    return {
        "protocol_version": VERSION,
        "status": "completed" if len(rows) == HORIZON else "active",
        "start_target_round": START,
        "horizon_trusted_draws": HORIZON,
        "trusted_draws": len(rows),
        "frozen_targets": sorted(freezes),
        "primary_endpoint": reg["primary_endpoint"],
        "interim_descriptive_only": True,
        "promotion_authorized": False,
        "first_prize_probability_improvement_claimed": False,
        "mean_paired_delta_interim": (
            float(np.mean([r["paired_composite_delta"] for r in rows]))
            if rows else None
        ),
        "fixed_horizon_primary_mean_delta": (
            float(np.mean([r["paired_composite_delta"] for r in rows]))
            if len(rows) == HORIZON else None
        ),
        "explicit_note": "Geometry advantage is NOT lottery-number predictive skill",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    p.add_argument("--source", type=Path,
                   default=Path("loto7_agent_output/source_validation.json"))
    p.add_argument("--mode", choices=("verify", "advance"), default="verify")
    args = p.parse_args()
    reg = load(args.root / REGISTRATION)
    register_guard(reg, Path(__file__).resolve(), Path(geometry.__file__).resolve())
    status = None
    if args.mode == "advance":
        status = advance(args.root, reg, args.csv, args.source)
    print(json.dumps({"mode": args.mode, "action": status,
                      "summary": summary(args.root, reg)},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
