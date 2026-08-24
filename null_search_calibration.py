#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

import loto7_v2_runner as v2
import separated_optimizer as so
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "bounded-null-search-v1"
DEFAULT_TARGET_WORLDS = 64
DEFAULT_SEARCH_STEPS = 16
RUN_EVERY_GENERATIONS = 50


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


def run_world(n_rows: int, min_train: int, world_index: int, search_steps: int) -> Dict[str, object]:
    x = synthetic_history(n_rows, 83_000_000 + world_index * 1009)
    parent = v2.DEFAULT_CHAMPION
    parent_windows, _ = so.replay_signal(x, parent, min_train, keep_q=False)
    parent_obj = so.weighted_signal_objective(parent_windows, parent)
    evaluations = 1
    accepts = 0
    for step in range(search_steps):
        candidates = so.signal_candidates(parent, f"null-world-{world_index}", step + 1, count=2)
        ranked = []
        for cfg in candidates:
            windows, _ = so.replay_signal(x, cfg, min_train, keep_q=False)
            obj = so.weighted_signal_objective(windows, cfg)
            evaluations += 1
            if obj > parent_obj + so.SIGNAL_MIN_GAIN:
                ranked.append((obj, cfg, windows))
        if ranked:
            ranked.sort(key=lambda z: z[0], reverse=True)
            parent_obj, parent, parent_windows = ranked[0]
            accepts += 1
    return {
        "world_index": world_index,
        "best_signal_objective": float(parent_obj),
        "best_signal_signature": so.signal_signature(parent),
        "candidate_evaluations": evaluations,
        "accepted_steps": accepts,
    }


def observed_signal(feedback_state: Dict[str, object], separated_state: Dict[str, object]) -> float:
    if separated_state:
        try:
            return float(separated_state.get("selected_signal_objective", 0.0))
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
    vals = np.asarray([float(w.get("best_signal_objective", 0.0)) for w in worlds if isinstance(w, dict)], dtype=float)
    if len(vals):
        percentile = float((1 + np.sum(vals >= observed)) / (len(vals) + 1))
        q50 = float(np.quantile(vals, 0.50))
        q95 = float(np.quantile(vals, 0.95))
        q99 = float(np.quantile(vals, 0.99))
        maximum = float(np.max(vals))
    else:
        percentile = 1.0
        q50 = q95 = q99 = maximum = 0.0
    return {
        "completed_worlds": int(len(vals)),
        "target_worlds": int(state.get("target_worlds", DEFAULT_TARGET_WORLDS)),
        "observed_real_signal_objective": float(observed),
        "empirical_tail_p_vs_bounded_null_search": percentile,
        "null_median_best": q50,
        "null_p95_best": q95,
        "null_p99_best": q99,
        "null_max_best": maximum,
        "calibration_complete": bool(len(vals) >= int(state.get("target_worlds", DEFAULT_TARGET_WORLDS))),
    }


def render_report(state: Dict[str, object], summary: Dict[str, object]) -> str:
    return "\n".join([
        "# Bounded Null-Search Calibration",
        "",
        f"- completed null worlds: **{summary['completed_worlds']}/{summary['target_worlds']}**",
        f"- search steps/world: **{state.get('search_steps')}** (2 signal candidates/step)",
        f"- observed real Signal objective: **{float(summary['observed_real_signal_objective']):+.5f}**",
        f"- null median best: **{float(summary['null_median_best']):+.5f}**",
        f"- null 95th percentile best: **{float(summary['null_p95_best']):+.5f}**",
        f"- null 99th percentile best: **{float(summary['null_p99_best']):+.5f}**",
        f"- empirical upper-tail p: **{float(summary['empirical_tail_p_vs_bounded_null_search']):.4f}**",
        f"- calibration complete: **{'YES' if summary['calibration_complete'] else 'NO'}**",
        "",
        "> 完全ランダムな7/37履歴に同じSignal探索手順をかけ、探索そのものが作る見かけの改善幅を測ります。",
        "> これは現在の全15,000+評価を完全再現するNullではなく、固定budgetのbounded calibrationです。world数が揃うまでは参考値です。",
        "",
    ])


def step(csv_path: Path = Path("loto7.csv"), out_dir: Path = Path("loto7_agent_output"),
         feedback_state_path: Path = Path("loto7_agent_output/research_feedback_state.json"),
         research_state_path: Path = Path("loto7_agent_output/v4_research_state.json"),
         min_train: int = 100, target_worlds: int = DEFAULT_TARGET_WORLDS,
         search_steps: int = DEFAULT_SEARCH_STEPS, force: bool = False) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    research = load_json(research_state_path, {})
    feedback = load_json(feedback_state_path, {})
    separated = load_json(out_dir / "separated_optimizer_state.json", {})
    generation = int(research.get("generation", 0))
    state_path = out_dir / "null_search_calibration_state.json"
    state = load_json(state_path, {})
    if state.get("report_version") != REPORT_VERSION or state.get("data_sha256") != data_sha:
        state = {
            "report_version": REPORT_VERSION, "data_sha256": data_sha,
            "target_worlds": int(target_worlds), "search_steps": int(search_steps), "worlds": [],
        }
    worlds = state.get("worlds") or []
    should_run = force or not worlds or (generation > 0 and generation % RUN_EVERY_GENERATIONS == 0)
    if len(worlds) >= target_worlds or not should_run:
        summary = summarize(state, observed_signal(feedback, separated))
        return {"ran_world": False, **summary}

    world = run_world(len(x), min_train, len(worlds), search_steps)
    worlds.append(world)
    state["worlds"] = worlds
    state["last_generation"] = generation
    summary = summarize(state, observed_signal(feedback, separated))
    state["summary"] = summary
    write_json(state_path, state)
    write_json(out_dir / "null_search_calibration_summary.json", {"report_version": REPORT_VERSION, "data_sha256": data_sha, **summary})
    (out_dir / "null_search_calibration_report.md").write_text(render_report(state, summary), encoding="utf-8")
    return {"ran_world": True, **summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Incrementally calibrate Signal search against synthetic 7/37 null histories")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--target-worlds", type=int, default=DEFAULT_TARGET_WORLDS)
    ap.add_argument("--search-steps", type=int, default=DEFAULT_SEARCH_STEPS)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    result = step(args.csv, args.out_dir, args.feedback_state, args.research_state,
                  args.min_train, args.target_worlds, args.search_steps, args.force)
    print(f"[NULL-CAL] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
