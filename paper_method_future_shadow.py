#!/usr/bin/env python3
"""Prospective-only shadow study for paper-derived constrained research methods.

For each next unobserved LOTO7 draw: freeze method and full probability vector,
grade only once a verified result arrives, then update an anytime e-process.
A 26-draw completed study may automatically adopt *research shadow* only.
Never modifies existing historical or prospective registries / Production.
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
from recursive_self_evolution_agent import NUMBERS, PICKS, predict_inclusion_probability, parse_expression
from paper_method_autonomy import REGISTRY as PAPER_REGISTRY
from paper_method_autonomy import reproducibility
from research_cycle_round2_replay import sha as digest

VERSION = "paper-autonomous-future-shadow-v1"
REGISTRY = "research/autonomous_paper_methods/future_state.json"
HORIZON = 26
ALPHA = 0.025      # First preregistered candidate. No second candidate in this version.
REQUIRED_E = 1 / ALPHA
UNIFORM = PICKS / NUMBERS
JST = timezone(timedelta(hours=9))


def atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".future-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def next_probabilities(prior: np.ndarray, expression: str) -> list[float]:
    p = np.asarray(predict_inclusion_probability(prior, expression), dtype=float)
    if (p.shape != (NUMBERS,) or not np.all(np.isfinite(p))
            or np.any(p <= 0) or np.any(p >= 1)
            or not np.isclose(p.sum(), PICKS, rtol=0, atol=1e-8)):
        raise ValueError("paper-derived model did not return valid probabilities")
    return [float(q) for q in p]


def brier_edge(p: list[float], y: np.ndarray) -> float:
    base = np.full(NUMBERS, UNIFORM)
    return float(np.mean((base - y)**2 - (np.asarray(p) - y)**2))


def forecast_payload(prior: np.ndarray, target: int, expression: str, schedule: str) -> dict:
    if target != len(prior) + 1 or len(prior) < 100:
        raise ValueError("cannot issue a retrospective or undertrained forecast")
    date = datetime.strptime(schedule, "%Y-%m-%d").date()
    return {
        "target_round": target,
        "scheduled_draw_date": date.isoformat(),
        "prefix_history_sha256": digest([[int(y) for y in row] for row in prior]),
        "model_probabilities": next_probabilities(prior, expression),
        "uniform_probabilities": [float(UNIFORM)] * NUMBERS,
    }


def event(payload: dict, previous: str, number: int) -> dict:
    value = {"sequence": number, "previous_sha256": previous, **payload}
    value["event_sha256"] = digest(value)
    return value


def assert_chain(state: dict, x: np.ndarray, draw_dates: list[str]) -> None:
    if state.get("version") != VERSION or state.get("horizon") != HORIZON:
        raise ValueError("invalid prospective study protocol")
    reg = state.get("registration")
    if not isinstance(reg, dict) or reg.get("alpha") != ALPHA:
        raise ValueError("invalid preregistered familywise budget")
    expression = reg.get("expression")
    parse_expression(expression)
    if hashlib.sha256(expression.encode()).hexdigest() != reg.get("expression_sha256"):
        raise ValueError("registered method was changed")
    start = reg["first_target_round"]
    if start < 101 or start > len(x) + 1:
        raise ValueError("invalid or retrospective start")
    rows = state.get("events")
    if not isinstance(rows, list) or len(rows) > HORIZON * 2:
        raise ValueError("too many prospective records")
    previous = "GENESIS"
    cumulative_e = 1.0
    for i, value in enumerate(rows):
        raw = {k: v for k, v in value.items() if k != "event_sha256"}
        if (value.get("sequence") != i + 1
                or value.get("previous_sha256") != previous
                or value.get("event_sha256") != digest(raw)):
            raise ValueError("append-only event integrity violation")
        target = start + i // 2
        if i % 2 == 0:
            if value.get("kind") != "forecast" or target > len(x) + 1:
                raise ValueError("nonchronological future freeze")
            prior = x[:target - 1]
            expected = forecast_payload(
                prior, target, expression, value["prediction"]["scheduled_draw_date"])
            if value.get("prediction") != expected:
                raise ValueError("changed issued research vector or data prefix")
            if value.get("prediction_sha256") != digest(expected):
                raise ValueError("forecast digest mismatch")
            at = datetime.fromisoformat(value["issued_at_utc"])
            if at.tzinfo is None or at.utcoffset() is None:
                raise ValueError("naive freeze timestamp")
            if at.astimezone(JST).date() >= datetime.fromisoformat(
                    expected["scheduled_draw_date"]).date():
                raise ValueError("forecast not frozen before target calendar date")
        else:
            if value.get("kind") != "grade" or target > len(x):
                raise ValueError("grade recorded before actual draw")
            freeze = rows[i - 1]
            y = x[target - 1]
            if (draw_dates[target - 1] != freeze["prediction"]["scheduled_draw_date"]
                    or value.get("forecast_event_sha256") != freeze["event_sha256"]
                    or value.get("actual_numbers") != (np.flatnonzero(y) + 1).tolist()):
                raise ValueError("grade does not match locked outcome/date")
            expected_edge = brier_edge(freeze["prediction"]["model_probabilities"], y)
            if value.get("brier_edge_vs_uniform") != expected_edge:
                raise ValueError("grade score drift")
            cumulative_e *= 1.0 + expected_edge
            if value.get("anytime_e_value") != cumulative_e:
                raise ValueError("grade e-process not reproducible")
        previous = value["event_sha256"]
    grades = (len(rows) // 2)
    if state.get("trusted_grades") != grades:
        raise ValueError("grade count mismatch")
    if state.get("anytime_e_value") != cumulative_e:
        raise ValueError("tracked e-value contradicts event ledger")
    eligible = grades == HORIZON and cumulative_e >= REQUIRED_E
    if state.get("research_adopted") is not eligible:
        raise ValueError("automatic research adoption gate is inconsistent")
    if (state.get("production_modified") is not False
            or state.get("original_future_ledgers_modified") is not False):
        raise ValueError("prospective study claims unauthorized edits")


def run(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    csv_path = root / "loto7.csv"
    src_path = root / "loto7_agent_output/source_validation.json"
    validation = validate_trusted_source(csv_path, src_path)
    if validation.get("trusted") is not True:
        raise ValueError("untrusted draw result source")
    x, frame = make_history(read_csv_flexible(csv_path))
    if [parse_round(r) for r in frame["回別"]] != list(range(1, len(x) + 1)):
        raise ValueError("draw IDs are not consecutive")
    source = json.loads(src_path.read_text(encoding="utf-8"))
    if (source.get("verification_provenance", {}).get("draw_csv_sha256")
            != fingerprint_file(csv_path)):
        raise ValueError("source attestation does not bind exact CSV bytes")
    dates = [v.date().isoformat() for v in frame["抽せん日"]]
    path = root / REGISTRY
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if state is None:
        paper = json.loads((root / PAPER_REGISTRY).read_text(encoding="utf-8"))
        candidate = paper.get("candidate")
        if not isinstance(candidate, dict) or not candidate.get("eligible_for_future_only_shadow"):
            return {"status": "awaiting_full_text_verified_paper_candidate"}
        expression = candidate["candidate_expression"]
        reproducibility(expression)
        schedule = source.get("sources", {}).get("official_schedule", {})
        if schedule.get("round") != len(x) + 1 or not schedule.get("date"):
            return {"status": "awaiting_authoritative_next_draw_schedule"}
        if now.astimezone(JST).date() >= datetime.strptime(
                schedule["date"], "%Y-%m-%d").date():
            return {"status": "too_late_for_conservative_prior_day_freeze"}
        state = {
            "version": VERSION, "horizon": HORIZON,
            "registration": {
                "doi": candidate["doi"],
                "paper_sha256": candidate["fulltext_sha256"],
                "expression": expression,
                "expression_sha256": hashlib.sha256(expression.encode()).hexdigest(),
                "first_target_round": len(x) + 1,
                "alpha": ALPHA,
                "family_candidates": 1,
                "registered_at_utc": now.isoformat(),
                "paper_experiments_reproduced": False,
            },
            "events": [], "trusted_grades": 0, "anytime_e_value": 1.0,
            "research_adopted": False, "production_modified": False,
            "original_future_ledgers_modified": False,
        }
    else:
        assert_chain(state, x, dates)
    if state["trusted_grades"] == HORIZON:
        return state
    events = state["events"]
    next_target = state["registration"]["first_target_round"] + len(events) // 2
    if len(events) % 2 == 1:
        if next_target > len(x):
            return state  # Wait until verified next result exists.
        if next_target != len(x):
            raise ValueError("missed draw: cannot repair a prospective study with hindsight")
        frozen = events[-1]["prediction"]
        if dates[next_target - 1] != frozen["scheduled_draw_date"]:
            raise ValueError("future scheduled date changed")
        y = x[next_target - 1]
        edge = brier_edge(frozen["model_probabilities"], y)
        factor = 1.0 + edge
        if not 0 <= factor <= 2.0:
            raise ValueError("invalid fair-null e-factor")
        next_e = state["anytime_e_value"] * factor
        new = event({
            "kind": "grade", "target_round": next_target,
            "forecast_event_sha256": events[-1]["event_sha256"],
            "actual_numbers": (np.flatnonzero(y) + 1).tolist(),
            "brier_edge_vs_uniform": edge,
            "anytime_e_value": next_e,
        }, events[-1]["event_sha256"], len(events) + 1)
        events.append(new)
        state["trusted_grades"] += 1
        state["anytime_e_value"] = next_e
        if state["trusted_grades"] == HORIZON:
            state["research_adopted"] = bool(next_e >= REQUIRED_E)
            state["adoption_decision"] = (
                "research_shadow_adopted" if state["research_adopted"]
                else "insufficient_future_evidence_do_not_adopt")
    if state["trusted_grades"] < HORIZON and len(events) % 2 == 0:
        next_target = state["registration"]["first_target_round"] + len(events) // 2
        if next_target == len(x) + 1:
            schedule = source.get("sources", {}).get("official_schedule", {})
            if (schedule.get("round") == next_target
                    and isinstance(schedule.get("date"), str)
                    and now.astimezone(JST).date() < datetime.strptime(
                        schedule["date"], "%Y-%m-%d").date()):
                frozen = forecast_payload(x, next_target,
                    state["registration"]["expression"], schedule["date"])
                entry = event({
                    "kind": "forecast", "target_round": next_target,
                    "issued_at_utc": now.isoformat(),
                    "prediction": frozen,
                    "prediction_sha256": digest(frozen),
                }, events[-1]["event_sha256"] if events else "GENESIS", len(events) + 1)
                events.append(entry)
        elif next_target < len(x) + 1:
            raise ValueError("cannot backdate an unissued forecast")
    assert_chain(state, x, dates)
    atomic(path, state)
    return state


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    args = ap.parse_args()
    data = run(args.repo_root)
    print(json.dumps({
        "status": data.get("adoption_decision", data.get("status", "prospective_active")),
        "trusted_grades": data.get("trusted_grades", 0),
        "anytime_e_value": data.get("anytime_e_value"),
        "research_adopted": data.get("research_adopted", False),
        "production_modified": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
