#!/usr/bin/env python3
"""Indefinite, research-only prospective adaptive forecast loop.

Starts at target 701 after verified round 700. Every future target is frozen
before its actual outcome, graded only against two independently matching
result sources, and followed by a new strictly-prior-only adaptive forecast.
The algorithm, sources and scoring semantics are SHA locked on registration.
No future p-value or Production promotion is authorized by this monitor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

import predictive_expert_agent as learner
import joint_set_v2_signal_oos as immutable
from joint_set_v2_model import N_NUMBERS, PICKS, bernoulli_signal_metrics
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
import loto7_v4_runner as v4

VERSION = "continuous-learning-agent-v1"
JST = timezone(timedelta(hours=9))
START_TARGET = 701
EXCLUDED_TARGET = 700
MIN_TRAIN = 100
CHECKPOINT_DRAWS = 26
RESULT_TRUST = "verified_two_result_sources"
NAME = "continuous_learning_agent"
REGISTRATION = NAME + "_registration.json"
REGISTRY = NAME + "_registry.json"
STATE = NAME + "_state.json"
FREEZES = NAME + "_freeze_history.jsonl"
RESULTS = NAME + "_results.jsonl"
SUMMARY = NAME + "_summary.json"
REPORT = NAME + "_report.md"
FILES_LOCKED = (
    "continuous_learning_agent.py",
    "predictive_expert_agent.py",
    "joint_set_v2_model.py",
    "joint_set_v2_signal_oos_guard.py",
    "joint_set_v2_signal_oos.py",
)


def canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path, *, required: bool = False) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise ValueError("missing required registered evidence: " + path.name)
        return {}
    rec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rec, dict):
        raise ValueError("not an evidence object: " + path.name)
    return rec


def write_json(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(record), indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read_chain(path: Path, *, kind: str) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    prior = "GENESIS"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            raise ValueError(kind + " contains an empty line")
        r = json.loads(line)
        if not isinstance(r, dict) or r.get("previous_record_sha256") != prior:
            raise ValueError(kind + " evidence chain broken")
        original_hash = r.get("record_sha256")
        payload = {k: v for k, v in r.items() if k != "record_sha256"}
        if sha(payload) != original_hash:
            raise ValueError(kind + " record content/hash mismatch")
        if not isinstance(r.get("target_round"), int):
            raise ValueError(kind + " target round must be integer")
        records.append(r)
        prior = original_hash
    rounds = [r["target_round"] for r in records]
    if rounds != list(range(START_TARGET, START_TARGET + len(rounds))):
        raise ValueError(kind + " has missing/duplicate/retrospective round")
    return records


def append_chain(path: Path, payload: Mapping[str, Any], previous: List[Dict[str, Any]]) -> Dict[str, Any]:
    record = dict(payload)
    record["previous_record_sha256"] = previous[-1]["record_sha256"] if previous else "GENESIS"
    record["record_sha256"] = sha(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(canonical(record) + "\n")
    return record


def manifest(root: Path) -> Dict[str, Any]:
    file_hashes = {}
    for name in FILES_LOCKED:
        path = root / name
        if not path.exists():
            raise ValueError("cannot lock missing research implementation: " + name)
        file_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    data = {
        "version": VERSION, "start_target_round": START_TARGET,
        "excluded_previously_frozen_round": EXCLUDED_TARGET,
        "min_train": MIN_TRAIN, "checkpoint_draws": CHECKPOINT_DRAWS,
        "open_ended_monitoring_no_interim_p_value": True,
        "learning_family": list(learner.EXPERTS),
        "fixed_initial_expert_weights": [float(v) for v in learner.PRIOR],
        "fixed_online_log_edge_rate": learner.ONLINE_LOG_EDGE_RATE,
        "fixed_online_decay": learner.ONLINE_DECAY,
        "file_sha256": file_hashes,
    }
    data["manifest_sha256"] = sha(data)
    return data


def load_registration(root: Path, out: Path, latest: int, clock: datetime) -> Dict[str, Any]:
    locked = manifest(root)
    path = out / REGISTRATION
    existing = read_json(path)
    if existing:
        if existing.get("algorithm_manifest") != locked:
            raise ValueError("registered learning algorithm SHA drift; no retrospective version change allowed")
        if (existing.get("version") != VERSION
                or existing.get("promotion_role") != "diagnostic_only"
                or existing.get("start_target_round") != START_TARGET
                or existing.get("excluded_target_round") != EXCLUDED_TARGET
                or existing.get("inference_policy") != "open_ended_descriptive_no_p_values"):
            raise ValueError("registered lifelong-monitoring rules changed")
        return existing
    if latest >= START_TARGET:
        raise ValueError("too late to register: first eligible target already resolved")
    existing_outputs = [out / p for p in (REGISTRY, STATE, FREEZES, RESULTS)]
    if any(path.exists() for path in existing_outputs):
        raise ValueError("registered state exists without an immutable initial registration")
    reg = {
        "version": VERSION,
        "registered_at_jst": clock.isoformat(timespec="seconds"),
        "registered_latest_round": latest,
        "registered_data_sha256": fingerprint_file(root / "loto7.csv"),
        "start_target_round": START_TARGET,
        "excluded_target_round": EXCLUDED_TARGET,
        "learning_rule": "past_outcomes_only_exponential_weighting_of_fixed_experts",
        "inference_policy": "open_ended_descriptive_no_p_values",
        "checkpoint_at_trusted_draws": CHECKPOINT_DRAWS,
        "promotion_role": "diagnostic_only",
        "production_autonomy": False,
        "algorithm_manifest": locked,
    }
    write_json(path, reg)
    return reg


def validated_draws(csv_path: Path) -> Tuple[np.ndarray, Any, int]:
    x, clean = make_history(read_csv_flexible(csv_path))
    learner.assert_history(x)
    if "回別" not in clean:
        raise ValueError("contiguous published round identities are required")
    rounds = [int(v4.parse_round(v) or -1) for v in clean["回別"]]
    if rounds != list(range(1, len(rounds) + 1)):
        raise ValueError("history draw identities have a gap or duplicate")
    return x, clean, rounds[-1]


def next_probabilities(x: np.ndarray) -> Dict[str, Any]:
    """Reconstruct expert learning in temporal order, ending before next draw."""
    learner.assert_history(x, min_train=MIN_TRAIN)
    csum = np.vstack((
        np.zeros((1, N_NUMBERS), dtype=np.int64),
        np.cumsum(x.astype(np.int64), axis=0),
    ))
    running = np.zeros(len(learner.EXPERTS), dtype=float)
    for t in range(MIN_TRAIN, len(x)):
        vectors = learner.expert_vectors(csum, t)
        actual = np.flatnonzero(x[t])
        component_scores = [
            float(bernoulli_signal_metrics(p, actual)["log_edge"]) for p in vectors
        ]
        running = learner.ONLINE_DECAY * running + np.asarray(component_scores)
    weights = learner.weights_from_prior_scores(running)
    p = weights @ learner.expert_vectors(csum, len(x))
    encoded = immutable.canonical_vector(p)
    check = immutable.parse_inclusion(encoded)
    top7 = [int(v + 1) for v in np.argsort(-check, kind="mergesort")[:PICKS]]
    return {
        "inclusion_p_canonical": encoded,
        "inclusion_p_sha256": immutable.vector_sha256(encoded),
        "top7_numbers": top7,
        "expert_weights": [float(v) for v in weights],
        "running_prequential_log_edge": [float(v) for v in running],
    }


def validate_ledger(
    reg: Mapping[str, Any], out: Path, x: np.ndarray, clean: Any,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    state = read_json(out / STATE)
    registry = read_json(out / REGISTRY)
    freezes = read_chain(out / FREEZES, kind="freeze")
    grades = read_chain(out / RESULTS, kind="grading")
    if not state and (registry or freezes or grades):
        raise ValueError("research loop lost its state after it began")
    if len(grades) > len(freezes) or len(freezes) > len(grades) + 1:
        raise ValueError("freeze/grade balance invalid")
    if state:
        if (state.get("version") != VERSION or state.get("start_target_round") != START_TARGET
                or state.get("manifest_sha256") != reg["algorithm_manifest"]["manifest_sha256"]
                or int(state["trusted_draws"]) != len(grades)
                or state["graded_rounds"] != [r["target_round"] for r in grades]
                or state.get("current_target_round") != (freezes[-1]["target_round"] if freezes else None)):
            raise ValueError("registered state/counts/target mismatch")
    if not freezes and registry:
        raise ValueError("live registry exists without freeze history")
    if freezes and registry != freezes[-1]:
        raise ValueError("live frozen registry changed since its append-only record")
    if freezes and not registry:
        raise ValueError("live registry deleted despite recorded frozen vector")

    for i, frozen in enumerate(freezes):
        if (frozen.get("algorithm_manifest_sha256") != reg["algorithm_manifest"]["manifest_sha256"]
                or frozen.get("base_round") != frozen["target_round"] - 1
                or frozen.get("source_verification_at_freeze") != RESULT_TRUST
                or immutable.vector_sha256(frozen["inclusion_p_canonical"]) != frozen["inclusion_p_sha256"]):
            raise ValueError("invalid frozen algorithm/input identity/hash")
        p = immutable.parse_inclusion(frozen["inclusion_p_canonical"])
        if frozen.get("top7_numbers") != [
            int(v + 1) for v in np.argsort(-p, kind="mergesort")[:PICKS]
        ]:
            raise ValueError("frozen Top7 differs from locked vector")
        if (not isinstance(frozen.get("expert_weights"), list)
                or len(frozen["expert_weights"]) != len(learner.EXPERTS)
                or abs(sum(frozen["expert_weights"]) - 1) > 1e-10
                or min(frozen["expert_weights"]) < 0):
            raise ValueError("frozen expert weight snapshot malformed")
        if i < len(grades):
            rec = grades[i]
            target = frozen["target_round"]
            if target > len(x):
                raise ValueError("graded result is not in the actual CSV")
            actual = [int(v + 1) for v in np.flatnonzero(x[target - 1])]
            if (rec.get("source_verification") != RESULT_TRUST
                    or rec.get("actual_numbers") != actual
                    or rec.get("draw_date") != clean["抽せん日"].iloc[target - 1].date().isoformat()
                    or rec.get("inclusion_p_sha256") != frozen["inclusion_p_sha256"]
                    or rec.get("frozen_record_sha256") != frozen["record_sha256"]):
                raise ValueError("stored graded evidence conflicts with frozen pre-result vector/current actual")
            metrics = bernoulli_signal_metrics(p, np.asarray(actual, dtype=int) - 1)
            for field, key in (
                ("log_edge", "log_edge"), ("brier_edge", "brier_edge"),
                ("top7_hits", "top7_hits"),
            ):
                if abs(float(rec[field]) - float(metrics[key])) > 1e-11:
                    raise ValueError("graded " + field + " differs from independent recomputation")
    if freezes and (len(freezes) == len(grades) or len(freezes) != len(grades) + 1):
        raise ValueError("prospective next target must be frozen after every graded result")
    return state, registry, freezes, grades


def freeze(
    out: Path, reg: Mapping[str, Any], x: np.ndarray,
    latest: int, data_sha: str, clock: datetime,
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    target = latest + 1
    if target < START_TARGET or target != START_TARGET + len(history):
        raise ValueError("freeze does not follow registered prospective sequence")
    learned = next_probabilities(x)
    payload = {
        "version": VERSION, "target_round": target, "base_round": latest,
        "base_data_sha256": data_sha, "frozen_at_jst": clock.isoformat(timespec="seconds"),
        "source_verification_at_freeze": RESULT_TRUST,
        "algorithm_manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        **learned,
        "promotion_role": "diagnostic_only",
    }
    record = append_chain(out / FREEZES, payload, history)
    write_json(out / REGISTRY, record)
    return record


def grade(
    out: Path, registry: Mapping[str, Any], actual: np.ndarray,
    date: str, previous: List[Dict[str, Any]],
) -> Dict[str, Any]:
    target = registry["target_round"]
    p = immutable.parse_inclusion(registry["inclusion_p_canonical"])
    actual_idx = np.flatnonzero(actual)
    metrics = bernoulli_signal_metrics(p, actual_idx)
    return append_chain(out / RESULTS, {
        "version": VERSION, "target_round": target, "draw_date": date,
        "actual_numbers": [int(i + 1) for i in actual_idx],
        "source_verification": RESULT_TRUST,
        "frozen_record_sha256": registry["record_sha256"],
        "inclusion_p_sha256": registry["inclusion_p_sha256"],
        "log_edge": float(metrics["log_edge"]),
        "brier_edge": float(metrics["brier_edge"]),
        "top7_hits": int(metrics["top7_hits"]),
        "adaptive_weights_frozen_before_outcome": registry["expert_weights"],
    }, previous)


def summarise(
    reg: Mapping[str, Any], latest: int, trusted: bool,
    freezes: List[Dict[str, Any]], grades: List[Dict[str, Any]],
    status: str,
) -> Dict[str, Any]:
    logs = [float(row["log_edge"]) for row in grades]
    top7 = [float(row["top7_hits"]) for row in grades]
    briers = [float(row["brier_edge"]) for row in grades]
    recent = logs[-min(12, len(logs)):]
    return {
        "version": VERSION, "status": status, "latest_seen_round": latest,
        "latest_source_trusted": trusted, "start_target_round": START_TARGET,
        "current_prefrozen_target": freezes[-1]["target_round"] if freezes else None,
        "trusted_draws": len(grades), "continuous_learning_ongoing": True,
        "learning_rule_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "primary_endpoint": "descriptive_mean_proper_log_score_edge_vs_uniform",
        "promotion_role": "diagnostic_only",
        "independent_evidence_only_after_prefreeze": True,
        "p_value_authorized": False, "production_promotion_eligible": False,
        "adaptive_weights_current": freezes[-1]["expert_weights"] if freezes else None,
        "descriptive_future_only": {
            "mean_log_edge_vs_uniform": float(np.mean(logs)) if logs else None,
            "mean_brier_edge_vs_uniform": float(np.mean(briers)) if briers else None,
            "mean_top7_hits": float(np.mean(top7)) if top7 else None,
            "uniform_expected_top7_hits": PICKS * PICKS / N_NUMBERS,
        },
        "drift_monitoring": {
            "recent_observed_draws": len(recent),
            "recent_mean_log_edge": float(np.mean(recent)) if recent else None,
            "watch_no_claim_of_improvement": bool(recent and np.mean(recent) <= 0),
        },
        "fixed_26_draw_descriptive_checkpoint_reached": len(grades) >= CHECKPOINT_DRAWS,
        "interpretation": (
            "Genuine prospective read-only research after pre-draw forecast freeze. "
            "Weights adapt only after each trusted real outcome. Continuing forever "
            "means anytime peeking cannot justify fixed-horizon p-values, model "
            "selection, or Production promotion. A separate preregistration is required."
        ),
    }


def run(
    root: Path, out: Path, source_report: Path,
    *, now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root = root.resolve()
    out = out.resolve()
    source_report = source_report.resolve()
    now = (now or datetime.now(JST)).astimezone(JST)
    csv_path = root / "loto7.csv"
    x, clean, latest = validated_draws(csv_path)
    source = validate_trusted_source(csv_path, source_report)
    if int(source["round"]) != latest:
        raise ValueError("validated latest round does not match local draw sequence")
    trusted = bool(source["trusted"])
    reg = load_registration(root, out, latest, now)
    state, registry, freezes, grades = validate_ledger(reg, out, x, clean)
    previous_hash = state.get("manifest_sha256") if state else reg["algorithm_manifest"]["manifest_sha256"]
    if previous_hash != reg["algorithm_manifest"]["manifest_sha256"]:
        raise ValueError("state manifest changed")

    status = "waiting_for_verified_round_700_prefix"
    if not freezes:
        if latest >= START_TARGET:
            raise ValueError("first registered target already published without pre-draw freeze")
        if latest == START_TARGET - 1 and trusted:
            record = freeze(out, reg, x, latest, fingerprint_file(csv_path), now, freezes)
            freezes.append(record)
            registry = record
            status = "active_prefrozen_waiting_result"
        elif latest == START_TARGET - 1:
            status = "awaiting_two_source_round_700"
    else:
        target = registry["target_round"]
        if latest > target:
            raise ValueError("missing target result/freeze: retrospective recovery forbidden")
        if latest == target:
            if not trusted:
                status = "awaiting_two_source_verification"
            else:
                if len(grades) != len(freezes) - 1:
                    raise ValueError("target already graded yet no subsequent frozen target")
                graded = grade(
                    out, registry, x[-1], clean["抽せん日"].iloc[-1].date().isoformat(), grades
                )
                grades.append(graded)
                new_registry = freeze(
                    out, reg, x, latest, fingerprint_file(csv_path), now, freezes
                )
                freezes.append(new_registry)
                registry = new_registry
                status = "graded_then_next_prefrozen"
        else:
            status = "active_prefrozen_waiting_result"

    new_state = {
        "version": VERSION, "manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "start_target_round": START_TARGET,
        "status": status, "trusted_draws": len(grades),
        "graded_rounds": [r["target_round"] for r in grades],
        "current_target_round": freezes[-1]["target_round"] if freezes else None,
        "promotion_role": "diagnostic_only",
    }
    if state != new_state:
        write_json(out / STATE, new_state)
    report = summarise(reg, latest, trusted, freezes, grades, status)
    write_json(out / SUMMARY, report)
    lines = [
        "# Continuous Learning Agent — prospective forecast lifecycle",
        "", "- version: " + VERSION,
        "- latest verified draw round: " + str(latest) + " / trusted=" + str(trusted),
        "- status: **" + status + "**",
        "- frozen next-round target: **" + str(report["current_prefrozen_target"]) + "**",
        "- genuine future draws graded: **" + str(len(grades)) + "**",
        "- fixed first checkpoint (descriptive): **" + str(CHECKPOINT_DRAWS) + "**",
        "- algorithm manifest SHA: " + str(report["learning_rule_sha256"]),
        "- current prior-only adaptive expert weights: " + str(report["adaptive_weights_current"]),
        "- future mean proper log edge vs uniform: " + str(report["descriptive_future_only"]["mean_log_edge_vs_uniform"]),
        "- future mean Top7 hits: " + str(report["descriptive_future_only"]["mean_top7_hits"]),
        "- recent-12 negative proper score drift watch: " + str(report["drift_monitoring"]["watch_no_claim_of_improvement"]),
        "", "No automatic tuning of model family or Production authority. This is an ongoing descriptive",
        "prospective experiment with **no repeated-testing p-values or promotion claim**.",
        "",
    ]
    (out / REPORT).write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Locked, self-updating prospective research signal")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    parser.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    args = parser.parse_args()
    report = run(args.repo_root, args.out_dir, args.source_report)
    print(json.dumps({
        "status": report["status"],
        "trusted_draws": report["trusted_draws"],
        "current_prefrozen_target": report["current_prefrozen_target"],
        "promotion_eligible": report["production_promotion_eligible"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
