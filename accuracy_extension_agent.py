#!/usr/bin/env python3
"""Fifth prior-only prediction hypothesis and independent prospective research shadow.

A heavily smoothed one-draw-lag transition expert competes against the existing
four experts. All expert weights are learned only after outcomes are observed.
The new hypothesis is NOT asserted to predict a fair independent lottery.
Never imports or writes Production/Champion or the pre-registered v2/adaptive OOS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import continuous_learning_agent as evidence
import joint_set_v2_signal_oos as vector_codec
import predictive_expert_agent as scout
from joint_set_v2_model import N_NUMBERS, PICKS, UNIFORM_INCLUSION, bernoulli_signal_metrics
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file

VERSION = "accuracy-extension-agent-v1"
EXPERTS = (*scout.EXPERTS, "shrunken_lag1_transition")
PRIOR_WEIGHTS = np.array([0.50, 0.12, 0.12, 0.11, 0.15], dtype=float)
WARMUP = 100
TRANSITION_WINDOW = 160
TRANSITION_VIRTUAL_EXPOSURES = 500
FINAL_UNIFORM_SHRINK = 0.25
ONLINE_RATE = 10.0
ONLINE_DECAY = 0.995
EVAL_LAST_N = 60
FAIR_NULL_WORLDS = 32
SEED = 28194171
START_TARGET = 701
JST = timezone(timedelta(hours=9))
SOURCE_TRUST = "verified_two_result_sources"
FILES_LOCKED = (
    "accuracy_extension_agent.py", "predictive_expert_agent.py",
    "continuous_learning_agent.py", "joint_set_v2_model.py",
    "joint_set_v2_signal_oos.py", "joint_set_v2_signal_oos_guard.py",
)
STEM = "accuracy_extension_agent"
REG = STEM + "_registration.json"
STATE = STEM + "_state.json"
REGISTRY = STEM + "_registry.json"
FREEZES = STEM + "_freezes.jsonl"
GRADES = STEM + "_grades.jsonl"
SUMMARY = STEM + "_summary.json"
REPORT = STEM + "_report.md"


def assert_history(x: np.ndarray, *, require_history: bool = True) -> None:
    if not isinstance(x, np.ndarray) or x.ndim != 2 or x.shape[1] != N_NUMBERS:
        raise ValueError("37-column draw history required")
    if len(x) < WARMUP + int(require_history) or np.any((x != 0) & (x != 1)):
        raise ValueError("invalid or insufficient binary draw history")
    if np.any(x.sum(axis=1) != PICKS):
        raise ValueError("each historical draw must contain exactly seven values")


def transition_expert(pair_counts: np.ndarray, previous: np.ndarray) -> np.ndarray:
    """P(next includes n | previous 7), using *only* earlier transitions."""
    if (pair_counts.shape != (N_NUMBERS, N_NUMBERS)
            or previous.shape != (N_NUMBERS,) or previous.sum() != PICKS
            or np.any((previous != 0) & (previous != 1))
            or np.any(pair_counts < 0)):
        raise ValueError("invalid prior-only transition inputs")
    selected = pair_counts[previous.astype(bool)]
    observations = selected.sum(axis=0).astype(float)
    exposure = float(selected.sum()) / PICKS
    p = (observations + TRANSITION_VIRTUAL_EXPOSURES * UNIFORM_INCLUSION) / (
        exposure + TRANSITION_VIRTUAL_EXPOSURES
    )
    if (not np.isfinite(p).all() or abs(float(p.sum()) - PICKS) > 1e-9
            or np.any(p <= 0) or np.any(p >= 1)):
        raise ValueError("transition inclusion probabilities not normalized")
    return p


def prefix_pairs(x: np.ndarray, n: int) -> np.ndarray:
    """Observed transitions s->s+1, s+1 strictly before target index n."""
    if n < 2 or n > len(x):
        raise ValueError("invalid prefix size for lag-one expert")
    pair = np.zeros((N_NUMBERS, N_NUMBERS), dtype=np.int64)
    for s in range(max(0, n - 1 - TRANSITION_WINDOW), n - 1):
        pair += np.outer(x[s], x[s + 1])
    return pair


def weights(running: np.ndarray) -> np.ndarray:
    if running.shape != (len(EXPERTS),) or not np.isfinite(running).all():
        raise ValueError("invalid online proper-score state")
    logits = np.log(PRIOR_WEIGHTS) + ONLINE_RATE * running
    z = np.exp(logits - logits.max())
    return z / z.sum()


def predict(vectors: np.ndarray, running: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if vectors.shape != (len(EXPERTS), N_NUMBERS):
        raise ValueError("unexpected predictor count")
    w = weights(running)
    p = FINAL_UNIFORM_SHRINK * UNIFORM_INCLUSION + (1.0 - FINAL_UNIFORM_SHRINK) * (w @ vectors)
    if abs(p.sum() - PICKS) > 1e-9 or np.any(p <= 0) or np.any(p >= 1):
        raise RuntimeError("invalid 7-of-37 inclusion marginals")
    return p, w


def walk(x: np.ndarray, *, last_n: int = EVAL_LAST_N) -> tuple[dict, list[dict], dict]:
    """Evaluate target t BEFORE feeding x[t] to the transition/weight learner."""
    assert_history(x)
    if not 1 <= last_n <= len(x) - WARMUP:
        raise ValueError("last_n overlaps warmup or is empty")
    cumulative = np.vstack((np.zeros((1, N_NUMBERS), dtype=np.int64),
                            np.cumsum(x.astype(np.int64), axis=0)))
    pair = prefix_pairs(x, WARMUP)
    running = np.zeros(len(EXPERTS), dtype=float)
    output: list[dict] = []
    last_forecast: dict = {}
    for t in range(WARMUP, len(x) + 1):
        vectors = np.vstack((
            scout.expert_vectors(cumulative, t),
            transition_expert(pair, x[t - 1])
        ))
        p, w = predict(vectors, running)
        if t == len(x):
            canonical = vector_codec.canonical_vector(p)
            last_forecast = {
                "inclusion_p_canonical": canonical,
                "inclusion_p_sha256": vector_codec.vector_sha256(canonical),
                "top7_numbers": [int(i + 1) for i in np.argsort(-p, kind="stable")[:PICKS]],
                "expert_weights": [float(q) for q in w],
                "expert_names": list(EXPERTS),
            }
            break
        actual = np.flatnonzero(x[t])
        result = bernoulli_signal_metrics(p, actual)
        component = [bernoulli_signal_metrics(v, actual) for v in vectors]
        if t >= len(x) - last_n:
            output.append({
                "round": t + 1, "top7_hits": int(result["top7_hits"]),
                "log_edge": float(result["log_edge"]),
                "brier_edge": float(result["brier_edge"]),
                "transition_log_edge": float(component[-1]["log_edge"]),
                "weights": [float(v) for v in w],
            })
        # Update the fitted ensemble only after scoring this target.
        running = ONLINE_DECAY * running + np.array([c["log_edge"] for c in component])
        pair += np.outer(x[t - 1], x[t])
        oldest = t - 1 - TRANSITION_WINDOW
        if oldest >= 0:
            pair -= np.outer(x[oldest], x[oldest + 1])
    if len(output) != last_n:
        raise RuntimeError("chronological evaluation window incomplete")
    summary = {
        "mean_top7_hits": float(np.mean([v["top7_hits"] for v in output])),
        "mean_log_edge": float(np.mean([v["log_edge"] for v in output])),
        "mean_brier_edge": float(np.mean([v["brier_edge"] for v in output])),
        "mean_transition_log_edge": float(np.mean([v["transition_log_edge"] for v in output])),
        "evaluated_rounds": last_n,
        "evaluated_start": output[0]["round"],
        "evaluated_end": output[-1]["round"],
    }
    return summary, output, last_forecast


def matched_fair_null(n: int, *, worlds: int = FAIR_NULL_WORLDS,
                      last_n: int = EVAL_LAST_N) -> dict:
    if not 1 <= worlds <= 256 or n - last_n < WARMUP:
        raise ValueError("invalid fair-world evaluation budget")
    vals, tops = [], []
    for i in range(worlds):
        fair = scout.synthetic_fair_history(n, SEED + 7187 * i)
        outcome, _, _ = walk(fair, last_n=last_n)
        vals.append(outcome["mean_log_edge"])
        tops.append(outcome["mean_top7_hits"])
    return {
        "worlds": worlds,
        "mean_log_edge": float(np.mean(vals)),
        "mean_top7_hits": float(np.mean(tops)),
        "full_learner_rerun_each_fair_world": True,
        "no_prospective_claim": True,
        "log_edges": vals,
    }


def manifest(root: Path) -> dict:
    digest = {}
    for path in FILES_LOCKED:
        f = root / path
        if not f.is_file():
            raise ValueError("cannot lock missing algorithm file: " + path)
        digest[path] = hashlib.sha256(f.read_bytes()).hexdigest()
    data = {
        "version": VERSION, "start_target_round": START_TARGET,
        "excluded_already_frozen_round": 700, "warmup": WARMUP,
        "history_pair_window": TRANSITION_WINDOW,
        "transition_virtual_exposures": TRANSITION_VIRTUAL_EXPOSURES,
        "final_uniform_shrink": FINAL_UNIFORM_SHRINK,
        "online_rate": ONLINE_RATE, "online_decay": ONLINE_DECAY,
        "prior_weights": PRIOR_WEIGHTS.tolist(), "expert_names": list(EXPERTS),
        "code_sha256": digest,
        "no_fixed_horizon_significance_from_anytime_monitor": True,
    }
    data["manifest_sha256"] = evidence.sha(data)
    return data


def register(root: Path, out: Path, latest: int, when: datetime) -> dict:
    expected = manifest(root)
    path = out / REG
    reg = evidence.read_json(path)
    if reg:
        if (reg.get("algorithm_manifest") != expected
                or reg.get("start_target_round") != START_TARGET
                or reg.get("promotion_role") != "diagnostic_only"):
            raise ValueError("registered extension algorithm drift / governance mismatch")
        return reg
    if latest >= START_TARGET or any((out / name).exists() for name in (REGISTRY, STATE, FREEZES, GRADES)):
        raise ValueError("first prospective registration too late or orphaned evidence")
    reg = {
        "version": VERSION, "registered_at_jst": when.isoformat(timespec="seconds"),
        "registered_at_latest_round": latest,
        "registered_data_sha256": fingerprint_file(root / "loto7.csv"),
        "start_target_round": START_TARGET, "promotion_role": "diagnostic_only",
        "fixed_horizon_p_values_authorized": False,
        "automatic_model_adoption": False,
        "algorithm_manifest": expected,
    }
    evidence.write_json(path, reg)
    return reg


def audit(out: Path, reg: Mapping[str, Any], x: np.ndarray, clean: Any) -> tuple[list, list, dict, dict]:
    freezes = evidence.read_chain(out / FREEZES, kind="extension freeze")
    grades = evidence.read_chain(out / GRADES, kind="extension grade")
    state = evidence.read_json(out / STATE)
    registry = evidence.read_json(out / REGISTRY)
    if len(grades) > len(freezes) or len(freezes) > len(grades) + 1:
        raise ValueError("prospective forecast / grade evidence is unbalanced")
    if len(freezes) != len(grades) + 1 and len(freezes) != 0:
        raise ValueError("next unseen target was not prefrozen")
    if state:
        if (state.get("manifest_sha256") != reg["algorithm_manifest"]["manifest_sha256"]
                or state.get("trusted_draws") != len(grades)
                or state.get("current_target_round") != (freezes[-1]["target_round"] if freezes else None)):
            raise ValueError("registered extension state altered or inconsistent")
    elif registry or freezes or grades:
        raise ValueError("extension state missing")
    if registry != (freezes[-1] if freezes else {}):
        raise ValueError("frozen extension registry changed")
    for i, frozen in enumerate(freezes):
        target = frozen["target_round"]
        if (frozen.get("base_round") != target - 1
                or frozen.get("algorithm_manifest_sha256") != reg["algorithm_manifest"]["manifest_sha256"]
                or frozen.get("source_verification_at_freeze") != SOURCE_TRUST
                or target - 1 > len(x) or target < START_TARGET):
            raise ValueError("invalid extension freeze provenance")
        p = vector_codec.parse_inclusion(frozen["inclusion_p_canonical"])
        if (frozen.get("inclusion_p_sha256") != vector_codec.vector_sha256(frozen["inclusion_p_canonical"])
                or frozen.get("top7_numbers") != [int(q + 1) for q in np.argsort(-p, kind="stable")[:PICKS]]
                or len(frozen.get("expert_weights", [])) != len(EXPERTS)
                or abs(sum(frozen["expert_weights"]) - 1) > 1e-10):
            raise ValueError("extension frozen vector/weight mismatch")
        data_prefix = hashlib.sha256(x[:target - 1].tobytes()).hexdigest()
        if frozen.get("base_history_sha256") != data_prefix:
            raise ValueError("extension frozen historical outcomes changed")
        if i < len(grades):
            grade = grades[i]
            if target > len(x):
                raise ValueError("graded extension round missing in current CSV")
            actual = [int(j + 1) for j in np.flatnonzero(x[target - 1])]
            metrics = bernoulli_signal_metrics(p, np.array(actual) - 1)
            if (grade.get("actual_numbers") != actual or grade.get("source_verification") != SOURCE_TRUST
                    or grade.get("frozen_record_sha256") != frozen["record_sha256"]
                    or grade.get("inclusion_p_sha256") != frozen["inclusion_p_sha256"]
                    or grade.get("draw_date") != clean["抽せん日"].iloc[target - 1].date().isoformat()
                    or any(abs(grade[name] - metrics[metric]) > 1e-10 for name, metric in (
                        ("log_edge", "log_edge"), ("brier_edge", "brier_edge"),
                        ("top7_hits", "top7_hits")))):
                raise ValueError("graded extension actual result / score conflicts with freeze")
            freeze_date = datetime.fromisoformat(frozen["frozen_at_jst"])
            draw_deadline = datetime.fromisoformat(grade["draw_date"] + "T20:00:00+09:00")
            if freeze_date.tzinfo is None or freeze_date >= draw_deadline:
                raise ValueError("no verified pre-draw extension freeze")
    return freezes, grades, registry, state


def freeze(out: Path, reg: dict, x: np.ndarray, latest: int, when: datetime, freezes: list,
           learned: dict | None = None) -> dict:
    if latest + 1 != START_TARGET + len(freezes):
        raise ValueError("cannot backfill missed extension forecast")
    if learned is None:
        _, _, learned = walk(x, last_n=1)
    event = {
        "version": VERSION, "target_round": latest + 1, "base_round": latest,
        "base_history_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
        "frozen_at_jst": when.isoformat(timespec="seconds"),
        "source_verification_at_freeze": SOURCE_TRUST,
        "algorithm_manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        **learned, "promotion_role": "diagnostic_only",
    }
    record = evidence.append_chain(out / FREEZES, event, freezes)
    evidence.write_json(out / REGISTRY, record)
    return record


def grade(out: Path, frozen: dict, x: np.ndarray, date: str, previous: list) -> dict:
    p = vector_codec.parse_inclusion(frozen["inclusion_p_canonical"])
    actual = np.flatnonzero(x)
    metrics = bernoulli_signal_metrics(p, actual)
    return evidence.append_chain(out / GRADES, {
        "version": VERSION, "target_round": frozen["target_round"],
        "draw_date": date, "actual_numbers": [int(i + 1) for i in actual],
        "source_verification": SOURCE_TRUST,
        "frozen_record_sha256": frozen["record_sha256"],
        "inclusion_p_sha256": frozen["inclusion_p_sha256"],
        "log_edge": float(metrics["log_edge"]),
        "brier_edge": float(metrics["brier_edge"]),
        "top7_hits": int(metrics["top7_hits"]),
    }, previous)


def run(root: Path, out: Path, source_report: Path, *,
        now: datetime | None = None, null_worlds: int = FAIR_NULL_WORLDS) -> dict:
    root, out = root.resolve(), out.resolve()
    when = (now or datetime.now(JST)).astimezone(JST)
    x, clean, latest = evidence.validated_draws(root / "loto7.csv")
    check = validate_trusted_source(root / "loto7.csv", source_report.resolve())
    if int(check["round"]) != latest:
        raise ValueError("latest verified source ID does not match historical sequence")
    trusted = bool(check["trusted"])
    reg = register(root, out, latest, when)
    freezes, grades, registry, old_state = audit(out, reg, x, clean)
    status = "waiting_for_verified_round_700_prefix"
    if not freezes:
        if latest >= START_TARGET:
            raise ValueError("cannot register first extension target after it was drawn")
        if latest == 700 and trusted:
            registry = freeze(out, reg, x, latest, when, freezes)
            freezes.append(registry)
            status = "prefrozen_waiting_next_draw"
        elif latest == 700:
            status = "awaiting_two_source_round_700"
    else:
        target = registry["target_round"]
        if latest > target:
            raise ValueError("missing prefrozen extension grade; no retrospective recovery")
        if latest == target and trusted:
            if len(grades) != len(freezes) - 1:
                raise ValueError("already graded extension draw without next freeze")
            # Compute next forecast before writing any irreversible event.
            _, _, next_prediction = walk(x, last_n=1)
            scored = grade(out, registry, x[-1], clean["抽せん日"].iloc[-1].date().isoformat(), grades)
            grades.append(scored)
            registry = freeze(out, reg, x, latest, when, freezes, next_prediction)
            freezes.append(registry)
        status = "prefrozen_waiting_next_draw" if latest < registry["target_round"] else "awaiting_verified_result"
    state = {
        "version": VERSION, "manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "status": status, "trusted_draws": len(grades),
        "current_target_round": registry["target_round"] if registry else None,
        "graded_rounds": [r["target_round"] for r in grades],
        "promotion_role": "diagnostic_only",
    }
    if old_state != state:
        evidence.write_json(out / STATE, state)

    # Diagnostic scores reuse previously examined real draws. They cannot
    # establish genuine accuracy improvement or change the registered rules.
    data_sha = fingerprint_file(root / "loto7.csv")
    existing = evidence.read_json(out / SUMMARY)
    if (existing.get("historical_data_sha256") == data_sha
            and existing.get("model_manifest_sha256") == reg["algorithm_manifest"]["manifest_sha256"]
            and existing.get("full_budget_fair_null", {}).get("worlds") == null_worlds):
        historical = existing["historical_reused_diagnostics"]
        null = existing["full_budget_fair_null"]
        reference = existing.get("prior_four_expert_reference", {})
    else:
        historical, _, _ = walk(x, last_n=EVAL_LAST_N)
        null = matched_fair_null(len(x), worlds=null_worlds)
        observed = historical["mean_log_edge"]
        null["one_sided_empirical_p_exploratory_only"] = (
            1 + sum(v >= observed - 1e-15 for v in null["log_edges"])
        ) / (null_worlds + 1)
        del null["log_edges"]
        old_scout = evidence.read_json(out / "predictive_expert_agent_summary.json")
        reference = {}
        if (old_scout.get("data_sha256") == data_sha
                and old_scout.get("evaluated_rounds") == EVAL_LAST_N):
            reference = {
                "same_historical_window": True,
                "mean_log_edge": old_scout["scout"]["mean_log_edge_vs_uniform"],
                "mean_top7_hits": old_scout["scout"]["mean_top7_hits"],
                "mean_brier_edge": old_scout["scout"]["mean_brier_edge_vs_uniform"],
            }
    future = {
        "observed": len(grades),
        "mean_top7_hits": float(np.mean([r["top7_hits"] for r in grades])) if grades else None,
        "mean_log_edge": float(np.mean([r["log_edge"] for r in grades])) if grades else None,
        "mean_brier_edge": float(np.mean([r["brier_edge"] for r in grades])) if grades else None,
    }
    summary = {
        "version": VERSION, "status": status, "latest_seen_round": latest,
        "latest_source_trusted": trusted, "first_target_round": START_TARGET,
        "current_prefrozen_target": registry["target_round"] if registry else None,
        "trusted_future_draws": len(grades), "future_descriptive_only": future,
        "historical_data_sha256": data_sha,
        "historical_reused_diagnostics": historical,
        "full_budget_fair_null": null,
        "prior_four_expert_reference": reference,
        "model_manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "scope": "research_only", "independent_future_only_after_prefreeze": True,
        "production_changed": False, "original_registered_shadows_changed": False,
        "promotion_eligible": False, "p_values_valid_for_continual_monitoring": False,
        "interpretation": (
            "Additional conditional lag hypothesis is exploratory. Existing historical draws "
            "were reused during research. Separate independent future results after an "
            "auditable pre-draw freeze are descriptive only; not a Production promotion test."
        ),
    }
    evidence.write_json(out / SUMMARY, summary)
    lines = [
        "# Accuracy Extension Agent — registered research-only fifth expert", "",
        f"- Status: **{status}**; source trusted: **{trusted}**",
        f"- Latest history: **{latest}**; first registered future target **701**",
        f"- Prefrozen target: **{summary['current_prefrozen_target']}**",
        f"- New future draws graded: **{len(grades)}**",
        f"- Previously mined history: {historical['evaluated_start']}–{historical['evaluated_end']}",
        f"- Historical Top7: **{historical['mean_top7_hits']:.4f}** (uniform 1.3243)",
        f"- Historical log-score edge: **{historical['mean_log_edge']:+.8f}**",
        f"- Matched fair histories: {null_worlds}; exploratory p: {null['one_sided_empirical_p_exploratory_only']:.4f}",
        f"- Existing four-expert comparator: {reference or 'not same data SHA'}",
        f"- Future-only mean log edge: {future['mean_log_edge']}",
        "", "The lag-1 hypothesis is aggressively shrunk toward fair uniform 7/37.",
        "No discovered signal is assumed, no repeated-monitor p values, and no automatic",
        "changes to Champion, Production, prior v2 or adaptive registered shadow.", "",
    ]
    (out / REPORT).write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Predeclared fifth-expert accuracy research")
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--null-worlds", type=int, default=FAIR_NULL_WORLDS)
    args = ap.parse_args()
    s = run(args.repo_root, args.out_dir, args.source_report, null_worlds=args.null_worlds)
    print(json.dumps({
        "status": s["status"], "future_draws": s["trusted_future_draws"],
        "next_frozen_round": s["current_prefrozen_target"],
        "historical_log_edge": s["historical_reused_diagnostics"]["mean_log_edge"],
        "promotion_eligible": s["promotion_eligible"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
