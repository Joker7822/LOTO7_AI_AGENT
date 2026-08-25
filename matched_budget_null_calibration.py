#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import robust_signal_optimizer as robust
import separated_optimizer as so
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "matched-budget-null-search-v1"
DEFAULT_TARGET_WORLDS = 64
DEFAULT_CANDIDATES_PER_GENERATION = 2
DEFAULT_MAX_STALE_GENERATIONS = 300


def load_json(path: Path, default: Dict[str, object]) -> Dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def synthetic_history(n_rows: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros((n_rows, 37), dtype=float)
    for t in range(n_rows):
        idx = rng.choice(37, size=7, replace=False)
        x[t, idx] = 1.0
    return x


def _best_candidate(
    x: np.ndarray,
    parent: v2.ModelConfig,
    parent_windows: Dict[str, Dict[str, float]],
    parent_eras: Sequence[Dict[str, object]],
    data_key: str,
    generation: int,
    min_train: int,
    count: int,
) -> Tuple[v2.ModelConfig | None, Dict[str, Dict[str, float]] | None, List[Dict[str, object]] | None, int]:
    ranked: List[Tuple[float, v2.ModelConfig, Dict[str, Dict[str, float]], List[Dict[str, object]]]] = []
    evaluated = 0
    for cfg in so.signal_candidates(parent, data_key, generation, count=count):
        windows, eras, _ = robust.replay_signal_with_eras(x, cfg, min_train, keep_q=False)
        evaluated += 1
        base_ok, _ = so.signal_accept(windows, parent_windows, cfg, parent)
        era_ok, _ = robust.era_accept(eras, parent_eras)
        if base_ok and era_ok:
            ranked.append((so.weighted_signal_objective(windows, cfg), cfg, windows, eras))
    if not ranked:
        return None, None, None, evaluated
    ranked.sort(key=lambda z: z[0], reverse=True)
    _, cfg, windows, eras = ranked[0]
    return cfg, windows, eras, evaluated


def run_world(
    n_rows: int,
    min_train: int,
    world_index: int,
    trial_budget: int,
    max_stale_generations: int = DEFAULT_MAX_STALE_GENERATIONS,
    candidates_per_generation: int = DEFAULT_CANDIDATES_PER_GENERATION,
) -> Dict[str, object]:
    """Run the current Signal+era selection policy on a synthetic 7/37 history.

    The null search stops under the same two controls used by real Research:
    candidate-trial budget and consecutive generations without a parent update.
    """
    x = synthetic_history(n_rows, 97_000_000 + world_index * 1009)
    parent = v2.DEFAULT_CHAMPION
    parent_windows, parent_eras, _ = robust.replay_signal_with_eras(x, parent, min_train, keep_q=False)
    parent_obj = so.weighted_signal_objective(parent_windows, parent)

    candidate_trials = 0
    generations = 0
    stale_generations = 0
    accepted_generations = 0

    while candidate_trials < trial_budget and stale_generations < max_stale_generations:
        generations += 1
        requested = min(candidates_per_generation, trial_budget - candidate_trials)
        cfg, windows, eras, evaluated = _best_candidate(
            x,
            parent,
            parent_windows,
            parent_eras,
            f"matched-null-world-{world_index}",
            generations,
            min_train,
            requested,
        )
        candidate_trials += evaluated
        # Defensive stop if deterministic de-duplication ever produces no candidates.
        if evaluated == 0:
            stale_generations += 1
            continue
        if cfg is None or windows is None or eras is None:
            stale_generations += 1
            continue
        parent = cfg
        parent_windows = windows
        parent_eras = eras
        parent_obj = so.weighted_signal_objective(parent_windows, parent)
        accepted_generations += 1
        stale_generations = 0

    stop_reason = "trial_budget_exhausted" if candidate_trials >= trial_budget else "signal_parent_plateau"
    era_values = [float(e.get("signal_objective", 0.0)) for e in parent_eras]
    return {
        "world_index": int(world_index),
        "best_signal_objective": float(parent_obj),
        "best_signal_signature": so.signal_signature(parent),
        "candidate_trials": int(candidate_trials),
        "trial_budget": int(trial_budget),
        "generations_run": int(generations),
        "accepted_generations": int(accepted_generations),
        "stale_generations_at_stop": int(stale_generations),
        "max_stale_generations": int(max_stale_generations),
        "stop_reason": stop_reason,
        "positive_eras": int(sum(v > 0 for v in era_values)),
        "worst_era_signal_objective": float(min(era_values) if era_values else 0.0),
    }


def observed_signal(out_dir: Path, feedback_state: Dict[str, object]) -> float:
    for name in ("robust_signal_optimizer_state.json", "separated_optimizer_state.json"):
        obj = load_json(out_dir / name, {})
        if obj:
            try:
                return float(obj.get("selected_signal_objective"))
            except Exception:
                pass
    summary = feedback_state.get("accepted_parent_summary") or {}
    if isinstance(summary, dict):
        try:
            return float(summary.get("signal_objective", 0.0))
        except Exception:
            pass
    return 0.0


def summarize(state: Dict[str, object], observed: float) -> Dict[str, object]:
    worlds = state.get("worlds") or []
    vals = np.asarray(
        [float(w.get("best_signal_objective", 0.0)) for w in worlds if isinstance(w, dict)],
        dtype=float,
    )
    if len(vals):
        tail_p = float((1 + np.sum(vals >= observed)) / (len(vals) + 1))
        q50 = float(np.quantile(vals, 0.50))
        q95 = float(np.quantile(vals, 0.95))
        q99 = float(np.quantile(vals, 0.99))
        maximum = float(np.max(vals))
    else:
        tail_p = 1.0
        q50 = q95 = q99 = maximum = 0.0
    target = int(state.get("target_worlds", DEFAULT_TARGET_WORLDS))
    return {
        "completed_worlds": int(len(vals)),
        "target_worlds": target,
        "matched_signal_trial_budget": int(state.get("trial_budget", 0)),
        "matched_max_stale_generations": int(state.get("max_stale_generations", DEFAULT_MAX_STALE_GENERATIONS)),
        "observed_real_signal_objective": float(observed),
        "empirical_tail_p_vs_matched_null_search": tail_p,
        "null_median_best": q50,
        "null_p95_best": q95,
        "null_p99_best": q99,
        "null_max_best": maximum,
        "calibration_complete": bool(len(vals) >= target),
    }


def render_report(state: Dict[str, object], summary: Dict[str, object]) -> str:
    return "\n".join([
        "# Matched-Budget Null-Search Calibration",
        "",
        f"- completed null worlds: **{summary['completed_worlds']}/{summary['target_worlds']}**",
        f"- matched candidate-trial budget/world: **{summary['matched_signal_trial_budget']}**",
        f"- matched plateau limit: **{summary['matched_max_stale_generations']} generations**",
        "- Signal gate matched: **YES**",
        "- four-era gate matched: **YES**",
        f"- observed real Signal objective: **{float(summary['observed_real_signal_objective']):+.5f}**",
        f"- null median best: **{float(summary['null_median_best']):+.5f}**",
        f"- null 95th percentile best: **{float(summary['null_p95_best']):+.5f}**",
        f"- null 99th percentile best: **{float(summary['null_p99_best']):+.5f}**",
        f"- empirical upper-tail p: **{float(summary['empirical_tail_p_vs_matched_null_search']):.4f}**",
        f"- calibration complete: **{'YES' if summary['calibration_complete'] else 'NO'}**",
        "",
        "> 実データ側で消費したSignal trial数と同じ候補budgetを各Null worldへ与え、現在のSignal/era採用ルールとplateau停止を同じように適用します。",
        "> 過去に使った旧optimizerの細部を完全再演するものではなく、現在のResearch選択ポリシーを同一探索量で較正する検定です。Production昇格証拠には使用しません。",
        "",
    ])


def step(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    feedback_state_path: Path = Path("loto7_agent_output/research_feedback_state.json"),
    guard_path: Path = Path("loto7_agent_output/research_cycle_guard.json"),
    min_train: int = 100,
    target_worlds: int = DEFAULT_TARGET_WORLDS,
    worlds_per_run: int = 1,
) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    feedback = load_json(feedback_state_path, {})
    guard = load_json(guard_path, {})

    trial_budget = int(guard.get("signal_trials_this_data", guard.get("signal_trials_total", 0)))
    max_stale = int(guard.get("max_stale_generations", DEFAULT_MAX_STALE_GENERATIONS))
    if trial_budget <= 0:
        return {"ran_worlds": 0, "reason": "no_signal_trial_budget"}

    state_path = out_dir / "matched_budget_null_calibration_state.json"
    state = load_json(state_path, {})
    reset = bool(
        state.get("report_version") != REPORT_VERSION
        or state.get("data_sha256") != data_sha
        or int(state.get("trial_budget", -1)) != trial_budget
        or int(state.get("max_stale_generations", -1)) != max_stale
        or int(state.get("target_worlds", -1)) != int(target_worlds)
    )
    if reset:
        state = {
            "report_version": REPORT_VERSION,
            "data_sha256": data_sha,
            "trial_budget": trial_budget,
            "max_stale_generations": max_stale,
            "candidates_per_generation": DEFAULT_CANDIDATES_PER_GENERATION,
            "target_worlds": int(target_worlds),
            "worlds": [],
        }

    worlds = state.get("worlds") or []
    remaining = max(0, int(target_worlds) - len(worlds))
    run_count = min(max(0, int(worlds_per_run)), remaining)
    for _ in range(run_count):
        worlds.append(run_world(
            len(x), min_train, len(worlds), trial_budget,
            max_stale_generations=max_stale,
            candidates_per_generation=DEFAULT_CANDIDATES_PER_GENERATION,
        ))
    state["worlds"] = worlds

    summary = summarize(state, observed_signal(out_dir, feedback))
    state["summary"] = summary
    write_json(state_path, state)
    write_json(out_dir / "matched_budget_null_calibration_summary.json", {
        "report_version": REPORT_VERSION,
        "data_sha256": data_sha,
        **summary,
        "independent_evidence": False,
        "production_promotion_eligible": False,
    })
    (out_dir / "matched_budget_null_calibration_report.md").write_text(
        render_report(state, summary), encoding="utf-8"
    )
    return {"ran_worlds": run_count, **summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibrate Signal search against 7/37 null histories using the real per-data search budget and plateau policy")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--guard", type=Path, default=Path("loto7_agent_output/research_cycle_guard.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--target-worlds", type=int, default=DEFAULT_TARGET_WORLDS)
    ap.add_argument("--worlds-per-run", type=int, default=1)
    args = ap.parse_args()
    result = step(
        args.csv, args.out_dir, args.feedback_state, args.guard,
        args.min_train, args.target_worlds, args.worlds_per_run,
    )
    print(f"[MATCHED-NULL] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
