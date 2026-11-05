#!/usr/bin/env python3
"""Prospectively registered v2 online learning (research only).

The existing v1 registration and frozen forecasts NEVER change. This new
track uses multi-rate exponentially weighted experts, an online meta-learner,
and a predeclared uniform-risk fallback. Every result is graded ONLY against
a vector frozen before the target's scheduled JST calendar date.

No post-hoc backfill, Production promotion, or unregistered p-values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round
import predictive_expert_agent as expert

VERSION = "online-learning-boost-v2-prospective-1"
START_TARGET = 702
JST = timezone(timedelta(hours=9))
DESTINATION = "research/online_learning_v2/state.json"
RATES = (2.0, 8.0, 20.0)
EXPERT_PRIOR = (0.55, 0.15, 0.15, 0.15)
TRACK_PRIOR = (1.0 / 3, 1.0 / 3, 1.0 / 3)
FORGET = 0.97
META_FORGET = 0.97
META_RATE = 8.0
WEIGHT_PRIOR_FLOOR = 0.10
NORMAL_UNIFORM_ANCHOR = 0.30
DRIFT_UNIFORM_ANCHOR = 0.60
DRIFT_WINDOW = 4
NUMBERS = 37
PICKS = 7
UNIFORM = PICKS / NUMBERS
LOCKED_CODE = (
    "online_learning_boost_v2.py",
    "predictive_expert_agent.py",
    "joint_set_v2_signal_oos_guard.py",
    "joint_set_v2_signal_oos.py",
    "joint_set_v2_model.py",
    "loto7_v4_runner.py",
    "loto7_evolving_agent.py",
)


def digest(record: object) -> str:
    return hashlib.sha256(json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def check_probability(p: np.ndarray) -> None:
    a = np.asarray(p, dtype=np.float64)
    if (a.shape != (NUMBERS,) or not np.all(np.isfinite(a))
            or np.any(a <= 0) or np.any(a >= 1)
            or not np.isclose(a.sum(), PICKS, rtol=0, atol=1e-9)):
        raise ValueError("invalid seven-of-37 inclusion probabilities")


def edge(p: np.ndarray, y: np.ndarray) -> float:
    check_probability(p)
    if y.shape != (NUMBERS,) or not np.all((y == 0) | (y == 1)) or y.sum() != PICKS:
        raise ValueError("invalid draw outcome")
    q = UNIFORM
    return float(np.mean(
        y * np.log(p / q) + (1 - y) * np.log((1 - p) / (1 - q))))


def weights(prior: tuple[float, ...], scores: np.ndarray, rate: float) -> np.ndarray:
    a = np.asarray(prior, dtype=np.float64)
    if scores.shape != a.shape or not np.all(np.isfinite(scores)):
        raise ValueError("invalid online learner state")
    logits = np.log(a) + rate * scores
    logits -= logits.max()
    w = np.exp(logits)
    w /= w.sum()
    w = (1 - WEIGHT_PRIOR_FLOOR) * w + WEIGHT_PRIOR_FLOOR * a
    if np.any(w <= 0) or not np.isclose(w.sum(), 1, atol=1e-12):
        raise ValueError("invalid online weights")
    return w


def initial_state() -> tuple[np.ndarray, np.ndarray, list[float]]:
    return (np.zeros(len(EXPERT_PRIOR), dtype=np.float64),
            np.zeros(len(TRACK_PRIOR), dtype=np.float64), [])


def prediction(prior: np.ndarray, expert_scores: np.ndarray,
               meta_scores: np.ndarray, graded_edges: list[float]) -> dict:
    expert.assert_history(prior, min_train=100)
    prefix_sum = np.vstack((
        np.zeros((1, NUMBERS), dtype=np.int64),
        np.cumsum(prior.astype(np.int64), axis=0)))
    base = expert.expert_vectors(prefix_sum, len(prior))
    if base.shape != (len(EXPERT_PRIOR), NUMBERS):
        raise ValueError("expert family does not match registered v2")
    for p in base:
        check_probability(p)
    ws = np.asarray([
        weights(EXPERT_PRIOR, expert_scores, rate) for rate in RATES])
    track_predictions = ws @ base
    for p in track_predictions:
        check_probability(p)
    mw = weights(TRACK_PRIOR, meta_scores, META_RATE)
    adaptive = mw @ track_predictions
    has_drift = (len(graded_edges) >= DRIFT_WINDOW and
                 float(np.mean(graded_edges[-DRIFT_WINDOW:])) < 0.0)
    anchor = DRIFT_UNIFORM_ANCHOR if has_drift else NORMAL_UNIFORM_ANCHOR
    result = anchor * np.full(NUMBERS, UNIFORM) + (1 - anchor) * adaptive
    check_probability(result)
    return {
        "prefix_sha256": digest(prior.astype(int).tolist()),
        "expert_vectors": base.tolist(),
        "track_predictions": track_predictions.tolist(),
        "track_expert_weights": ws.tolist(),
        "meta_weights": mw.tolist(),
        "probabilities": result.tolist(),
        "top7": sorted(int(i + 1) for i in np.argsort(
            -result, kind="mergesort")[:PICKS]),
        "uniform_anchor": float(anchor),
        "drift_guard_active": bool(has_drift),
        "expert_score_before": expert_scores.tolist(),
        "meta_score_before": meta_scores.tolist(),
        "prior_verified_grades": len(graded_edges),
    }


def assessment(freeze: dict, actual: np.ndarray) -> dict:
    pred = freeze["prediction"]
    y = np.asarray(actual, dtype=np.int8)
    p = np.asarray(pred["probabilities"], dtype=np.float64)
    exp = np.asarray(pred["expert_vectors"], dtype=np.float64)
    trk = np.asarray(pred["track_predictions"], dtype=np.float64)
    if exp.shape != (len(EXPERT_PRIOR), NUMBERS) or trk.shape != (len(RATES), NUMBERS):
        raise ValueError("stored expert vectors invalid")
    for v in (*exp, *trk):
        check_probability(v)
    model_edge = edge(p, y)
    uniform = np.full(NUMBERS, UNIFORM, dtype=float)
    return {
        "actual_numbers": (np.flatnonzero(y) + 1).tolist(),
        "frozen_event_sha256": freeze["event_sha256"],
        "model_log_edge_vs_uniform": model_edge,
        "model_brier_edge_vs_uniform": float(np.mean((uniform - y)**2 - (p - y)**2)),
        "top7_hits": int(y[np.asarray(pred["top7"], dtype=int) - 1].sum()),
        "expert_log_edges": [edge(v, y) for v in exp],
        "track_log_edges": [edge(v, y) for v in trk],
    }


def advance(expert_scores: np.ndarray, meta_scores: np.ndarray,
            graded_edges: list[float], grade: dict) -> None:
    expert_scores *= FORGET
    expert_scores += np.asarray(grade["expert_log_edges"], dtype=float)
    meta_scores *= META_FORGET
    meta_scores += np.asarray(grade["track_log_edges"], dtype=float)
    graded_edges.append(float(grade["model_log_edge_vs_uniform"]))


def manifest(root: Path) -> dict:
    files = {}
    for path in LOCKED_CODE:
        location = root / path
        if not location.is_file():
            raise ValueError("required locked file not found: " + path)
        files[path] = hashlib.sha256(location.read_bytes()).hexdigest()
    obj = {
        "version": VERSION,
        "first_future_target": START_TARGET,
        "learning_rates": list(RATES),
        "expert_prior": list(EXPERT_PRIOR),
        "track_prior": list(TRACK_PRIOR),
        "forget": FORGET, "meta_forget": META_FORGET,
        "meta_rate": META_RATE,
        "weight_prior_floor": WEIGHT_PRIOR_FLOOR,
        "normal_uniform_anchor": NORMAL_UNIFORM_ANCHOR,
        "drift_uniform_anchor": DRIFT_UNIFORM_ANCHOR,
        "drift_window": DRIFT_WINDOW,
        "expert_family": list(expert.EXPERTS),
        "source_code_sha256": files,
        "research_only": True,
    }
    obj["manifest_sha256"] = digest(obj)
    return obj


def append_event(events: list[dict], content: dict) -> dict:
    event = {
        "sequence": len(events) + 1,
        "previous_event_sha256": events[-1]["event_sha256"] if events else "GENESIS",
        **content,
    }
    event["event_sha256"] = digest(event)
    events.append(event)
    return event


def assert_ledger(ledger: dict, root: Path, x: np.ndarray, frame) -> tuple:
    if (ledger.get("version") != VERSION
            or ledger.get("registration") != manifest(root)):
        raise ValueError("registered online learner algorithm changed")
    if (ledger.get("role") != "research_only_not_production"
            or ledger.get("start_target_round") != START_TARGET):
        raise ValueError("online learner registration or research-only role changed")
    events = ledger.get("events")
    if not isinstance(events, list) or len(events) % 2 != 1:
        raise ValueError("online learner must hold exactly one ungraded freeze")
    es, ms, graded_edges = initial_state()
    previous = "GENESIS"
    for i, event in enumerate(events):
        raw = {k: v for k, v in event.items() if k != "event_sha256"}
        if (event.get("sequence") != i + 1
                or event.get("previous_event_sha256") != previous
                or event.get("event_sha256") != digest(raw)):
            raise ValueError("prospective online evidence event hash invalid")
        target = START_TARGET + i // 2
        if event.get("target_round") != target:
            raise ValueError("unexpected or nonconsecutive future target")
        if i % 2 == 0:
            if event.get("kind") != "freeze" or target > len(x) + 1:
                raise ValueError("missing or retrospective online prediction")
            issued = datetime.fromisoformat(event["issued_at_jst"])
            scheduled = datetime.fromisoformat(event["scheduled_draw_date"]).date()
            if (issued.tzinfo is None or issued.utcoffset() is None
                    or issued.astimezone(JST).date() >= scheduled):
                raise ValueError("online prediction not frozen before draw day")
            expected = prediction(x[:target - 1], es, ms, graded_edges)
            if event.get("prediction") != expected:
                raise ValueError("online frozen prediction or prefix was tampered")
        else:
            if event.get("kind") != "grade" or target > len(x):
                raise ValueError("cannot retrospectively grade an unseen target")
            frozen = events[i - 1]
            date = frame["抽せん日"].iloc[target - 1].date().isoformat()
            if date != frozen["scheduled_draw_date"]:
                raise ValueError("trusted draw date differs from original freeze")
            graded = assessment(frozen, x[target - 1])
            if event.get("grade") != graded or event.get("draw_date") != date:
                raise ValueError("online grade differs from trusted actual draw")
            advance(es, ms, graded_edges, graded)
        previous = event["event_sha256"]
    expected_target = START_TARGET + len(events) // 2
    if events[-1]["target_round"] != expected_target:
        raise ValueError("invalid online current target")
    if len(graded_edges) != len(events) // 2:
        raise ValueError("online grading count drift")
    if ledger.get("trusted_grades") != len(graded_edges):
        raise ValueError("online learning summary not consistent with evidence")
    return es, ms, graded_edges


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".online-v2-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(obj, file, ensure_ascii=False, sort_keys=True,
                      indent=2, allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def source_attestation(root: Path, source_report: Path, latest: int) -> tuple:
    result = validate_trusted_source(root / "loto7.csv", source_report)
    if result["round"] != latest:
        raise ValueError("source verification round does not match draw history")
    report = json.loads(source_report.read_text(encoding="utf-8"))
    if (report.get("verification_provenance", {}).get("draw_csv_sha256")
            != fingerprint_file(root / "loto7.csv")):
        raise ValueError("source attestation does not bind exact CSV")
    return bool(result["trusted"]), report


def official_next_schedule(report: dict, next_target: int) -> str | None:
    schedule = report.get("sources", {}).get("official_schedule")
    if not isinstance(schedule, dict) or schedule.get("round") != next_target:
        return None
    candidate = schedule.get("date")
    try:
        return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return None


def freeze(events: list[dict], x: np.ndarray,
           es: np.ndarray, ms: np.ndarray, grades: list[float],
           schedule: str, now: datetime) -> dict:
    target = len(x) + 1
    if target != START_TARGET + len(grades):
        raise ValueError("online next target must be sequential")
    if now.date() >= datetime.fromisoformat(schedule).date():
        raise ValueError("refuse to freeze forecast on/after scheduled draw date")
    return append_event(events, {
        "kind": "freeze", "target_round": target,
        "scheduled_draw_date": schedule,
        "issued_at_jst": now.isoformat(timespec="seconds"),
        "prediction": prediction(x, es, ms, grades),
    })


def run(root: Path, output: Path, source_report: Path,
        *, now: datetime | None = None) -> dict:
    root, output = root.resolve(), output.resolve()
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("online learner requires timezone-aware timestamps")
    now = (now or datetime.now(JST)).astimezone(JST)
    x, frame = make_history(read_csv_flexible(root / "loto7.csv"))
    expert.assert_history(x, min_train=100)
    if [parse_round(v) for v in frame["回別"]] != list(range(1, len(x) + 1)):
        raise ValueError("nonconsecutive source draw identities")
    latest = len(x)
    trusted, report = source_attestation(root, source_report, latest)
    schedule = official_next_schedule(report, latest + 1)
    if output.exists():
        ledger = json.loads(output.read_text(encoding="utf-8"))
        es, ms, grades = assert_ledger(ledger, root, x, frame)
        target = ledger["events"][-1]["target_round"]
        if latest > target:
            raise ValueError("missing previous freeze; retrospective repair prohibited")
        if latest == target and trusted:
            if now.date() < frame["抽せん日"].iloc[-1].date():
                raise ValueError("trusted result cannot precede actual draw date")
            if not schedule:
                return {"status": "awaiting_verified_next_schedule",
                        "trusted_grades": len(grades), "target_round": target}
            if now.date() >= datetime.fromisoformat(schedule).date():
                raise ValueError("next prefreeze date already passed")
            previous = ledger["events"][-1]
            graded = assessment(previous, x[-1])
            append_event(ledger["events"], {
                "kind": "grade", "target_round": target,
                "draw_date": frame["抽せん日"].iloc[-1].date().isoformat(),
                "grade": graded,
            })
            advance(es, ms, grades, graded)
            freeze(ledger["events"], x, es, ms, grades, schedule, now)
            ledger["trusted_grades"] = len(grades)
            atomic_json(output, ledger)
        elif latest == target and not trusted:
            return {"status": "awaiting_independent_result_verification",
                    "trusted_grades": len(grades), "target_round": target}
    else:
        if latest >= START_TARGET:
            raise ValueError("cannot backdate initial prospective v2 registration")
        if latest < START_TARGET - 1 or not trusted:
            return {"status": "awaiting_verified_701_prefix", "trusted_grades": 0}
        if not schedule:
            return {"status": "awaiting_official_next_schedule", "trusted_grades": 0}
        es, ms, grades = initial_state()
        events: list[dict] = []
        freeze(events, x, es, ms, grades, schedule, now)
        ledger = {"version": VERSION, "registration": manifest(root),
                  "events": events, "trusted_grades": 0,
                  "role": "research_only_not_production",
                  "start_target_round": START_TARGET}
        atomic_json(output, ledger)
    es, ms, grades = assert_ledger(ledger, root, x, frame)
    last = ledger["events"][-1]
    return {
        "status": "prospective_online_v2_active",
        "target_round": last["target_round"],
        "scheduled_draw_date": last["scheduled_draw_date"],
        "trusted_grades": len(grades),
        "adaptive_expert_weights": last["prediction"]["track_expert_weights"],
        "adaptive_meta_weights": last["prediction"]["meta_weights"],
        "uniform_safety_anchor": last["prediction"]["uniform_anchor"],
        "drift_guard_active": last["prediction"]["drift_guard_active"],
        "mean_future_log_edge_vs_uniform":
            float(np.mean(grades)) if grades else None,
        "production_modified": False, "model_promotion_authorized": False,
        "p_values_or_proven_skill_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-file", type=Path, default=Path(DESTINATION))
    parser.add_argument("--source-report", type=Path,
                        default=Path("loto7_agent_output/source_validation.json"))
    args = parser.parse_args()
    root = args.repo_root.resolve()
    result = run(root, root / args.state_file, root / args.source_report)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
