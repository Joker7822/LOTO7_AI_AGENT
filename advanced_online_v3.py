#!/usr/bin/env python3
"""Advanced research-only online model, separately registered from v1 and v2.

A predetermined six-expert, three-rate, three-temperature learner freezes its
whole forecast before each draw, then learns exclusively from corroborated
results. Its exact fixed-size-set e-process is a mathematically valid test of
the *uniform seven-of-37 subset null* (not a claim of lottery predictability).

Do not modify this file after registration without creating a new protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round
from predictive_expert_agent import expert_vectors
from recursive_self_evolution_agent import predict_inclusion_probability

VERSION = "advanced-online-v3-exact-set-eprocess-1"
JST = timezone(timedelta(hours=9))
FIRST_TARGET = 703
REGISTRATION = Path("research/advanced_online_v3/registration.json")
STATE = Path("research/advanced_online_v3/state.json")
NUMBERS, PICKS = 37, 7
FAIR = PICKS / NUMBERS
MIN_TRAIN = 100
EXPERT_NAMES = (
    "uniform", "bayes_short40", "bayes_long160", "momentum_shrink",
    "prior_frequency_pair", "prior_decay_gap",
)
FORMULAS = ("tanh(hot20 + 0.35 * pair)", "tanh(decay + 0.35 * gap)")
EXPERT_PRIOR = (0.40, 0.10, 0.10, 0.10, 0.15, 0.15)
RATES = (2.0, 8.0, 20.0)
META_PRIOR = (1 / 3, 1 / 3, 1 / 3)
TEMPERATURES = (0.70, 1.0, 1.25)
TEMP_PRIOR = (1 / 3, 1 / 3, 1 / 3)
EXPERT_DECAY, META_DECAY, TEMP_DECAY = 0.97, 0.97, 0.97
META_RATE, TEMP_RATE = 8.0, 8.0
WEIGHT_FLOOR = 0.10
UNIFORM_ANCHOR = 0.40
DRIFT_ANCHOR = 0.75
DRIFT_WINDOW = 6
E_BETS = (0.025, 0.05, 0.10, 0.20)
E_THRESHOLD = 40.0
MIN_FUTURE_EVALUATIONS = 26
# A new fixed-size-set probability distribution is induced from the
# 37 inclusion scores by bounded odds, not mistaken for exact marginals.
ODDS_LOWER, ODDS_UPPER = 0.25, 4.0
ALLOWED_FILES = (
    "advanced_online_v3.py",
    "predictive_expert_agent.py",
    "recursive_self_evolution_agent.py",
    "joint_set_v2_model.py",
    "joint_set_v2_signal_oos.py",
    "joint_set_v2_signal_oos_guard.py",
    "loto7_v4_runner.py",
    "loto7_evolving_agent.py",
)


def digest(item: object) -> str:
    return hashlib.sha256(json.dumps(
        item, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def assert_vector(vector: np.ndarray) -> None:
    p = np.asarray(vector, dtype=float)
    if (p.shape != (NUMBERS,) or not np.isfinite(p).all()
            or np.any(p <= 0) or np.any(p >= 1)
            or not np.isclose(p.sum(), PICKS, rtol=0, atol=1e-9)):
        raise ValueError("invalid 37-number inclusion vector")


def assert_draw(y: np.ndarray) -> None:
    if (y.shape != (NUMBERS,) or not np.issubdtype(y.dtype, np.integer)
            or np.any((y != 0) & (y != 1))
            or int(y.sum()) != PICKS):
        raise ValueError("invalid seven-of-37 result")


def proper_edge(vector: np.ndarray, y: np.ndarray) -> float:
    assert_vector(vector)
    assert_draw(y)
    p = np.asarray(vector, dtype=float)
    return float(np.mean(
        y * np.log(p / FAIR)
        + (1 - y) * np.log((1 - p) / (1 - FAIR))))


def set_likelihood_ratio(weights: np.ndarray, selected: np.ndarray,
                         picks: int) -> float:
    """Exact normalized Fisher-weighted fixed-cardinality subset LR.

    P_w(S) = product(w_i for i in S) / e_k(w);
    e_k is the k-th elementary symmetric polynomial.
    P_0(S) = 1 / comb(n,k), so E_0[LR | all past data] = 1, exactly.
    """
    w = np.asarray(weights, dtype=float)
    indices = np.asarray(selected)
    n = len(w)
    if (w.ndim != 1 or n < 2 or not 1 <= picks < n
            or not np.isfinite(w).all() or np.any(w <= 0)
            or indices.ndim != 1 or len(indices) != picks
            or not np.issubdtype(indices.dtype, np.integer)
            or len(set(indices.tolist())) != picks
            or np.any(indices < 0) or np.any(indices >= n)):
        raise ValueError("invalid fixed-size subset likelihood")
    normalized = w / np.exp(np.mean(np.log(w)))
    coefficients = np.zeros(picks + 1, dtype=float)
    coefficients[0] = 1.0
    for weight in normalized:
        for k in range(picks, 0, -1):
            coefficients[k] += weight * coefficients[k - 1]
    if not np.isfinite(coefficients[picks]) or coefficients[picks] <= 0:
        raise ValueError("invalid subset partition function")
    result = (math.comb(n, picks) *
              float(np.prod(normalized[indices])) / coefficients[picks])
    if not math.isfinite(result) or result <= 0:
        raise ValueError("invalid exact-set likelihood ratio")
    return result


def predicted_subset_ratio(vector: np.ndarray, y: np.ndarray) -> float:
    assert_vector(vector)
    assert_draw(y)
    p = np.asarray(vector, dtype=float)
    bounded_odds = np.clip(p / (1 - p), ODDS_LOWER, ODDS_UPPER)
    return set_likelihood_ratio(bounded_odds, np.flatnonzero(y), PICKS)


def soft_weights(prior: tuple[float, ...], scores: np.ndarray,
                 speed: float) -> np.ndarray:
    base = np.asarray(prior, dtype=float)
    if (scores.shape != base.shape or not np.isfinite(scores).all()
            or not np.isclose(base.sum(), 1.0, rtol=0, atol=1e-12)):
        raise ValueError("invalid prior-only online weight scores")
    logits = np.log(base) + speed * scores
    logits -= logits.max()
    values = np.exp(logits)
    values /= values.sum()
    values = (1.0 - WEIGHT_FLOOR) * values + WEIGHT_FLOOR * base
    if not np.isclose(values.sum(), 1.0, atol=1e-12):
        raise ValueError("online expert weights not normalized")
    return values


def calibrated(vector: np.ndarray, temperature: float) -> np.ndarray:
    """Bounded affine recalibration with capped-simplex projection."""
    assert_vector(vector)
    raw = FAIR + temperature * (np.asarray(vector, dtype=float) - FAIR)
    lo, hi = -2.0, 2.0
    for _ in range(70):
        mid = (lo + hi) * .5
        projected = np.clip(raw + mid, 1e-8, 1 - 1e-8)
        if projected.sum() > PICKS:
            hi = mid
        else:
            lo = mid
    p = np.clip(raw + (lo + hi) * .5, 1e-8, 1 - 1e-8)
    assert_vector(p)
    return p


def experts(prior: np.ndarray) -> np.ndarray:
    if (prior.ndim != 2 or prior.shape[1] != NUMBERS
            or len(prior) < MIN_TRAIN + 1):
        raise ValueError("insufficient prior-only training history")
    y = np.asarray(prior, dtype=np.int64)
    if np.any((y != 0) & (y != 1)) or np.any(y.sum(axis=1) != PICKS):
        raise ValueError("untrusted model history")
    csum = np.vstack((np.zeros((1, NUMBERS), dtype=np.int64),
                      np.cumsum(y, axis=0)))
    first = expert_vectors(csum, len(y))
    structured = [predict_inclusion_probability(y, f) for f in FORMULAS]
    models = np.vstack((first, *structured))
    if models.shape != (len(EXPERT_NAMES), NUMBERS):
        raise ValueError("registered six-expert family shape changed")
    for p in models:
        assert_vector(p)
    return models


def empty_scores() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float], list[float]]:
    return (np.zeros(len(EXPERT_NAMES)),
            np.zeros(len(RATES)),
            np.zeros(len(TEMPERATURES)), [], [0.0] * len(E_BETS))


def model_forecast(prior: np.ndarray, expert_scores: np.ndarray,
                   meta_scores: np.ndarray, temp_scores: np.ndarray,
                   past_edges: list[float]) -> dict:
    family = experts(prior)
    rate_weights = np.vstack([
        soft_weights(EXPERT_PRIOR, expert_scores, rate) for rate in RATES])
    tracks = rate_weights @ family
    for p in tracks:
        assert_vector(p)
    meta = soft_weights(META_PRIOR, meta_scores, META_RATE)
    collective = meta @ tracks
    assert_vector(collective)
    candidates = np.vstack([calibrated(collective, t) for t in TEMPERATURES])
    temperature_weights = soft_weights(TEMP_PRIOR, temp_scores, TEMP_RATE)
    calibrated_mix = temperature_weights @ candidates
    is_drift = (len(past_edges) >= DRIFT_WINDOW and
                float(np.mean(past_edges[-DRIFT_WINDOW:])) < 0)
    uniform_ratio = DRIFT_ANCHOR if is_drift else UNIFORM_ANCHOR
    result = (uniform_ratio * np.full(NUMBERS, FAIR) +
              (1 - uniform_ratio) * calibrated_mix)
    assert_vector(result)
    return {
        "prefix_sha256": digest(prior.astype(int).tolist()),
        "expert_vectors": family.tolist(),
        "rate_expert_weights": rate_weights.tolist(),
        "rate_predictions": tracks.tolist(),
        "meta_weights": meta.tolist(),
        "temperature_candidates": candidates.tolist(),
        "temperature_weights": temperature_weights.tolist(),
        "probabilities": result.tolist(),
        "top7": sorted(int(i + 1) for i in np.argsort(
            -result, kind="mergesort")[:PICKS]),
        "anchor_fraction": float(uniform_ratio),
        "drift_guard": bool(is_drift),
        "prior_verified_scores": len(past_edges),
        "expert_score_before": expert_scores.tolist(),
        "meta_score_before": meta_scores.tolist(),
        "temperature_score_before": temp_scores.tolist(),
        "e_process_values_before": [],
    }


def score_frozen(freeze: dict, y: np.ndarray,
                 prior_log_wealth: list[float]) -> dict:
    assert_draw(y)
    pred = freeze["prediction"]
    p = np.asarray(pred["probabilities"], dtype=float)
    ex = np.asarray(pred["expert_vectors"], dtype=float)
    tracks = np.asarray(pred["rate_predictions"], dtype=float)
    temps = np.asarray(pred["temperature_candidates"], dtype=float)
    if (ex.shape != (len(EXPERT_NAMES), NUMBERS)
            or tracks.shape != (len(RATES), NUMBERS)
            or temps.shape != (len(TEMPERATURES), NUMBERS)):
        raise ValueError("stored prospective feature predictions malformed")
    for v in (*ex, *tracks, *temps):
        assert_vector(v)
    assert_vector(p)
    exact_lr = predicted_subset_ratio(p, y)
    updates = [
        float(before + math.log1p(bet * (exact_lr - 1)))
        for before, bet in zip(prior_log_wealth, E_BETS)
    ]
    if len(updates) != len(E_BETS):
        raise ValueError("incorrect registered e-process budget")
    log_mean = float(np.logaddexp.reduce(updates) - math.log(len(updates)))
    return {
        "frozen_event_sha256": freeze["event_sha256"],
        "actual_numbers": (np.flatnonzero(y) + 1).tolist(),
        "mean_log_edge_vs_fair_marginal": proper_edge(p, y),
        "mean_brier_edge_vs_fair_marginal":
            float(np.mean((FAIR - y) ** 2 - (p - y) ** 2)),
        "top7_hits": int(y[np.asarray(pred["top7"], dtype=int) - 1].sum()),
        "expert_log_edges": [proper_edge(v, y) for v in ex],
        "track_log_edges": [proper_edge(v, y) for v in tracks],
        "temperature_log_edges": [proper_edge(v, y) for v in temps],
        "exact_7_of_37_set_likelihood_ratio": exact_lr,
        "e_process_log_wealth": updates,
        "e_process_log_mixture": log_mean,
        "e_process_e_value_capped": float(math.exp(min(log_mean, 100))),
        "e_process_threshold_crossed": bool(log_mean >= math.log(E_THRESHOLD)),
    }


def learn(expert_scores: np.ndarray, meta_scores: np.ndarray,
          temp_scores: np.ndarray, edge_history: list[float],
          log_wealth: list[float], scored: dict) -> None:
    expert_scores *= EXPERT_DECAY
    expert_scores += np.asarray(scored["expert_log_edges"])
    meta_scores *= META_DECAY
    meta_scores += np.asarray(scored["track_log_edges"])
    temp_scores *= TEMP_DECAY
    temp_scores += np.asarray(scored["temperature_log_edges"])
    edge_history.append(float(scored["mean_log_edge_vs_fair_marginal"]))
    log_wealth[:] = list(scored["e_process_log_wealth"])


def manifest(root: Path) -> dict:
    hashes = {}
    for name in ALLOWED_FILES:
        source = root / name
        if not source.is_file():
            raise ValueError("missing registered scientific dependency: " + name)
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    definition = {
        "version": VERSION,
        "start_target_round": FIRST_TARGET,
        "expert_names": list(EXPERT_NAMES),
        "formulas": list(FORMULAS),
        "expert_prior": list(EXPERT_PRIOR),
        "learning_rates": list(RATES),
        "meta_prior": list(META_PRIOR),
        "temperatures": list(TEMPERATURES),
        "temperature_prior": list(TEMP_PRIOR),
        "expert_decay": EXPERT_DECAY,
        "meta_decay": META_DECAY,
        "temp_decay": TEMP_DECAY,
        "meta_rate": META_RATE, "temp_rate": TEMP_RATE,
        "weight_floor": WEIGHT_FLOOR,
        "uniform_anchor": UNIFORM_ANCHOR,
        "drift_anchor": DRIFT_ANCHOR,
        "drift_window": DRIFT_WINDOW,
        "e_bets": list(E_BETS),
        "e_threshold": E_THRESHOLD,
        "min_future_evaluations": MIN_FUTURE_EVALUATIONS,
        "odds_bounds": [ODDS_LOWER, ODDS_UPPER],
        "subset_likelihood": "exact_elementary_symmetric_polynomial_v1",
        "report_only_no_production_promotion": True,
        "file_sha256": hashes,
    }
    definition["manifest_sha256"] = digest(definition)
    return definition


def append(events: list[dict], info: dict) -> dict:
    event = {
        "sequence": len(events) + 1,
        "previous_event_sha256":
            events[-1]["event_sha256"] if events else "GENESIS",
        **info,
    }
    event["event_sha256"] = digest(event)
    events.append(event)
    return event


def checked_schedule(report: dict, target: int) -> str | None:
    item = report.get("sources", {}).get("official_schedule")
    if not isinstance(item, dict) or item.get("round") != target:
        return None
    try:
        return datetime.strptime(item["date"], "%Y-%m-%d").date().isoformat()
    except (KeyError, TypeError, ValueError):
        return None


def verify_source(root: Path, latest: int) -> tuple[bool, dict]:
    source_path = root / "loto7_agent_output/source_validation.json"
    checked = validate_trusted_source(root / "loto7.csv", source_path)
    if checked["round"] != latest:
        raise ValueError("verified source round does not match CSV prefix")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if (source.get("verification_provenance", {}).get("draw_csv_sha256")
            != fingerprint_file(root / "loto7.csv")):
        raise ValueError("trusted report does not attest exact draw history bytes")
    return checked["trusted"], source


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".advanced-v3-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate_state(state: dict, registration: dict, root: Path,
                   x: np.ndarray, frame) -> tuple:
    if (state.get("version") != VERSION
            or state.get("registration_sha256") != registration["registration_sha256"]
            or state.get("role") != "independent_research_only"):
        raise ValueError("invalid independent research ledger registration")
    events = state.get("events")
    if not isinstance(events, list) or not events or len(events) % 2 != 1:
        raise ValueError("missing future freeze or incomplete event transition")
    es, ms, ts, edges, wealth = empty_scores()
    previous = "GENESIS"
    for i, event in enumerate(events):
        payload = {k: v for k, v in event.items() if k != "event_sha256"}
        if (event.get("sequence") != i + 1
                or event.get("previous_event_sha256") != previous
                or event.get("event_sha256") != digest(payload)):
            raise ValueError("prospective event chain tampered")
        target = FIRST_TARGET + i // 2
        if event.get("target_round") != target:
            raise ValueError("missing or duplicate future evaluation")
        if i % 2 == 0:
            if event.get("kind") != "freeze" or target > len(x) + 1:
                raise ValueError("retrospective or missing forecast")
            stamp = datetime.fromisoformat(event["issued_at_jst"])
            scheduled = datetime.strptime(
                event["scheduled_draw_date"], "%Y-%m-%d").date()
            if (stamp.tzinfo is None or stamp.utcoffset() is None
                    or stamp.astimezone(JST).date() >= scheduled):
                raise ValueError("prediction not frozen before official draw date")
            if (i == 0 and
                    datetime.fromisoformat(registration["registered_at_jst"]).date()
                    >= scheduled):
                raise ValueError("independent protocol was registered too late")
            expected = model_forecast(x[:target - 1], es, ms, ts, edges)
            expected["e_process_values_before"] = list(wealth)
            if event.get("prediction") != expected:
                raise ValueError("frozen probabilities or history have changed")
        else:
            if event.get("kind") != "grade" or target > len(x):
                raise ValueError("unverified or nonchronological grading")
            frozen = events[i - 1]
            actual_date = frame["抽せん日"].iloc[target - 1].date().isoformat()
            if event.get("draw_date") != actual_date or (
                    frozen["scheduled_draw_date"] != actual_date):
                raise ValueError("source result date differs from frozen schedule")
            scored = score_frozen(frozen, x[target - 1], wealth)
            if event.get("metrics") != scored:
                raise ValueError("graded evidence differs from frozen forecast")
            learn(es, ms, ts, edges, wealth, scored)
        previous = event["event_sha256"]
    if (state.get("trusted_grades") != len(edges)
            or state.get("current_target_round") != events[-1]["target_round"]):
        raise ValueError("online count or current target changed")
    return es, ms, ts, edges, wealth


def freeze(events: list[dict], prior: np.ndarray,
           scores: tuple, schedule: str, now: datetime) -> dict:
    target = len(prior) + 1
    es, ms, ts, edges, wealth = scores
    if target != FIRST_TARGET + len(edges):
        raise ValueError("new prediction cannot skip a future draw")
    date = datetime.strptime(schedule, "%Y-%m-%d").date()
    if now.astimezone(JST).date() >= date:
        raise ValueError("cannot backdate a prediction on or after draw date")
    forecast = model_forecast(prior, es, ms, ts, edges)
    forecast["e_process_values_before"] = list(wealth)
    return append(events, {
        "kind": "freeze",
        "target_round": target,
        "scheduled_draw_date": schedule,
        "issued_at_jst": now.astimezone(JST).isoformat(timespec="seconds"),
        "prediction": forecast,
    })


def run(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("timezone-aware JST event time required")
    now = (now or datetime.now(JST)).astimezone(JST)
    x, frame = make_history(read_csv_flexible(root / "loto7.csv"))
    if [parse_round(v) for v in frame["回別"]] != list(range(1, len(x) + 1)):
        raise ValueError("nonconsecutive official draw numbers")
    if len(x) < MIN_TRAIN + 2:
        raise ValueError("insufficient verified training observations")
    latest = len(x)
    trusted, source = verify_source(root, latest)
    reg_path, state_path = root / REGISTRATION, root / STATE
    registered_manifest = manifest(root)
    registration = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else None
    if registration is None:
        if state_path.exists():
            raise ValueError("research state exists without preregistration")
        if latest >= FIRST_TARGET:
            raise ValueError("cannot retrospectively register first future target")
        if not trusted:
            return {"status": "awaiting_two_source_verification_before_registration"}
        registration = {
            "version": VERSION,
            "registered_at_jst": now.isoformat(timespec="seconds"),
            "registered_latest_round": latest,
            "first_target_round": FIRST_TARGET,
            "registered_history_sha256": fingerprint_file(root / "loto7.csv"),
            "algorithm_manifest": registered_manifest,
            "role": "independent_research_only",
            "anytime_alpha": 1 / E_THRESHOLD,
            "production_promotion_authorized": False,
        }
        registration["registration_sha256"] = digest(registration)
        write_atomic(reg_path, registration)
    else:
        raw = {k: v for k, v in registration.items()
               if k != "registration_sha256"}
        if (registration.get("registration_sha256") != digest(raw)
                or registration.get("algorithm_manifest") != registered_manifest
                or registration.get("version") != VERSION
                or registration.get("first_target_round") != FIRST_TARGET
                or registration.get("role") != "independent_research_only"
                or registration.get("production_promotion_authorized") is not False):
            raise ValueError("registered v3 method, protocol, or provenance drift")
    if not state_path.exists():
        if latest < FIRST_TARGET - 1 or not trusted:
            return {"status": "awaiting_verified_round_702",
                    "registered": True, "graded_draws": 0}
        if latest > FIRST_TARGET - 1:
            raise ValueError("first future draw has already occurred without a freeze")
        schedule = checked_schedule(source, FIRST_TARGET)
        if not schedule:
            return {"status": "awaiting_verified_703_schedule",
                    "registered": True, "graded_draws": 0}
        scores = empty_scores()
        events: list[dict] = []
        freeze(events, x, scores, schedule, now)
        state = {
            "version": VERSION,
            "registration_sha256": registration["registration_sha256"],
            "role": "independent_research_only",
            "events": events,
            "trusted_grades": 0,
            "current_target_round": FIRST_TARGET,
        }
        write_atomic(state_path, state)
    else:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        scores = validate_state(state, registration, root, x, frame)
        target = state["current_target_round"]
        if latest > target:
            raise ValueError("missing a prospective freeze; no historical backfill")
        if latest == target:
            if not trusted:
                return {"status": "awaiting_two_source_trusted_target",
                        "registered": True, "graded_draws": state["trusted_grades"]}
            next_schedule = checked_schedule(source, target + 1)
            if not next_schedule:
                return {"status": "awaiting_verified_following_schedule",
                        "registered": True, "graded_draws": state["trusted_grades"]}
            scored = score_frozen(state["events"][-1], x[-1], scores[-1])
            append(state["events"], {
                "kind": "grade", "target_round": target,
                "draw_date": frame["抽せん日"].iloc[-1].date().isoformat(),
                "metrics": scored,
            })
            es, ms, ts, edges, wealth = scores
            learn(es, ms, ts, edges, wealth, scored)
            freeze(state["events"], x, scores, next_schedule, now)
            state["trusted_grades"] = len(edges)
            state["current_target_round"] = target + 1
            write_atomic(state_path, state)
    scores = validate_state(state, registration, root, x, frame)
    n = len(scores[3])
    log_e = float(np.logaddexp.reduce(scores[4]) - math.log(len(E_BETS)))
    return {
        "status": "prospective_v3_frozen_waiting_outcome",
        "target_round": state["current_target_round"],
        "scheduled_draw_date": state["events"][-1]["scheduled_draw_date"],
        "future_verified_grades": n,
        "exact_set_e_value_capped": float(math.exp(min(log_e, 100))),
        "e_threshold": E_THRESHOLD,
        "research_evidence_gate_met":
            bool(n >= MIN_FUTURE_EVALUATIONS and log_e >= math.log(E_THRESHOLD)),
        "mean_prospective_log_edge":
            float(np.mean(scores[3])) if n else None,
        "production_modified": False,
        "existing_v1_v2_ledgers_modified": False,
        "automatic_production_promotion": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(run(args.repo_root), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
