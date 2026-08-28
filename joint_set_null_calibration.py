#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

import joint_set_research as jsr
import precision_random_baseline as prb
from joint_set_model import candidate_configs, expected_utility_portfolio, forecast, portfolio_metrics
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "joint-set-matched-null-v1"


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def synthetic_fair_world(draws: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    x = np.zeros((int(draws), 37), dtype=np.int8)
    universe = np.arange(37)
    for i in range(len(x)):
        x[i, rng.choice(universe, size=7, replace=False)] = 1
    return x


def world_seed(data_sha: str, world_index: int) -> int:
    raw = hashlib.sha256(f"{REPORT_VERSION}|{data_sha}|{world_index}".encode()).hexdigest()[:16]
    return int(raw, 16) % (2**63 - 1)


def run_world(
    x: np.ndarray,
    metadata_design: np.ndarray,
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
    random_score: float,
    seed: int,
) -> Dict[str, float]:
    configs = candidate_configs()
    preq = {
        cfg.version(): jsr.build_prequential_signal(x, cfg, min_train, metadata_design)
        for cfg in configs
    }
    eval_start = max(min_train + 30, len(x) - int(last_n))
    deltas: List[float] = []
    gates: List[float] = []
    selected_scores: List[float] = []
    for t in range(eval_start, len(x)):
        prior_count = t - min_train
        cfg, selected_score = jsr.select_config(configs, preq, prior_count, selection_window)
        md_adj, md_diag = jsr.metadata_for_target(x, metadata_design, t)
        bundle = forecast(x[:t], cfg, preq[cfg.version()][:prior_count], md_adj, md_diag)
        tickets, _ = expected_utility_portfolio(
            bundle,
            seed=int(seed + t * 1009),
            scenarios=validation_scenarios,
            candidate_count=validation_candidates,
        )
        actual = set((np.flatnonzero(x[t]) + 1).tolist())
        pm = portfolio_metrics(tickets, actual)
        deltas.append(float(pm["score"] - random_score))
        gates.append(float(bundle.gate))
        selected_scores.append(float(selected_score))
    return {
        "score_delta_vs_random": float(np.mean(deltas)) if deltas else 0.0,
        "mean_gate": float(np.mean(gates)) if gates else 0.0,
        "mean_selected_prior_score": float(np.mean(selected_scores)) if selected_scores else 0.0,
    }


def percentile(values: List[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q)) if values else 0.0


def compatible_state(
    state: Dict[str, object],
    data_sha: str,
    metadata_sha: str,
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
    target_worlds: int,
) -> bool:
    return bool(
        state.get("report_version") == REPORT_VERSION
        and state.get("data_sha256") == data_sha
        and state.get("metadata_sha256") == metadata_sha
        and int(state.get("min_train", -1)) == int(min_train)
        and int(state.get("last_n", -1)) == int(last_n)
        and int(state.get("selection_window", -1)) == int(selection_window)
        and int(state.get("validation_scenarios", -1)) == int(validation_scenarios)
        and int(state.get("validation_candidates", -1)) == int(validation_candidates)
        and int(state.get("target_worlds", -1)) == int(target_worlds)
    )


def summarize(state: Dict[str, object], observed_delta: float) -> Dict[str, object]:
    worlds = list(state.get("worlds", []))
    values = [float(w["score_delta_vs_random"]) for w in worlds if isinstance(w, dict)]
    n = len(values)
    tail = sum(v >= float(observed_delta) for v in values)
    return {
        "report_version": REPORT_VERSION,
        "data_sha256": state["data_sha256"],
        "metadata_sha256": state["metadata_sha256"],
        "completed_worlds": n,
        "target_worlds": int(state["target_worlds"]),
        "calibration_complete": n >= int(state["target_worlds"]),
        "observed_true_nested_score_delta": float(observed_delta),
        "empirical_tail_p": float((tail + 1) / (n + 1)) if n else None,
        "null_median": percentile(values, 0.50),
        "null_p95": percentile(values, 0.95),
        "null_p99": percentile(values, 0.99),
        "null_max": max(values) if values else None,
        "matched_budget": {
            "predeclared_config_count": int(state["predeclared_config_count"]),
            "selection_window": int(state["selection_window"]),
            "last_n": int(state["last_n"]),
            "validation_scenarios": int(state["validation_scenarios"]),
            "validation_candidates": int(state["validation_candidates"]),
            "same_config_selection_rule": True,
            "same_dynamic_gate": True,
            "same_regime_and_pair_model": True,
            "same_metadata_covariates_with_randomized_draw_outcomes": True,
            "same_expected_utility_portfolio": True,
        },
        "independent_evidence": False,
        "promotion_eligible": False,
        "interpretation": "Synthetic fair 7/37 worlds repeat the same Joint Set configuration-selection and portfolio budget. This is Research calibration, not Future OOS evidence.",
    }


def render_report(summary: Dict[str, object]) -> str:
    p = summary.get("empirical_tail_p")
    p_text = "not available" if p is None else f"{float(p):.6f}"
    return "\n".join([
        "# Joint Set Matched-Budget Null Calibration",
        "",
        f"- worlds: **{summary['completed_worlds']} / {summary['target_worlds']}**",
        f"- observed strict True Nested score delta: **{summary['observed_true_nested_score_delta']:+.6f}**",
        f"- empirical upper-tail p: **{p_text}**",
        f"- null median: **{summary['null_median']:+.6f}**",
        f"- null p95: **{summary['null_p95']:+.6f}**",
        f"- null p99: **{summary['null_p99']:+.6f}**",
        f"- calibration complete: **{str(summary['calibration_complete']).lower()}**",
        "",
        "> 完全ランダム7/37世界でも、実データと同じconfig family・選択窓・Dynamic Gate・Joint pair/regime・5口scenario最適化を実行します。",
        "> Research-only。Production昇格証拠ではありません。",
        "",
    ])


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    metadata_path: Path = Path("loto7_agent_output/research_external_metadata.csv"),
    min_train: int = 100,
    last_n: int = 60,
    selection_window: int = 120,
    validation_scenarios: int = 512,
    validation_candidates: int = 96,
    random_reps: int = 4096,
    target_worlds: int = 64,
    worlds_per_run: int = 1,
    cutoff_hour_jst: int = 18,
) -> Dict[str, object]:
    summary_path = out_dir / "joint_set_true_nested_summary.json"
    jsr.run(
        csv_path=csv_path, out_dir=out_dir, metadata_path=metadata_path,
        min_train=min_train, last_n=last_n, selection_window=selection_window,
        validation_scenarios=validation_scenarios, validation_candidates=validation_candidates,
        current_scenarios=1024, current_candidates=max(validation_candidates, 128),
        random_reps=random_reps, cutoff_hour_jst=cutoff_hour_jst, if_stale=True,
    )
    observed = json.loads(summary_path.read_text(encoding="utf-8"))
    observed_delta = float(observed["portfolio"]["score_delta_vs_random"]["mean"])

    df = read_csv_flexible(csv_path)
    x_real, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    metadata_design, _, _ = jsr.prepare_metadata(clean, metadata_path, cutoff_hour_jst)
    metadata_sha = jsr.file_sha(metadata_path)
    random_summary = prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_score = float(random_summary["windows"]["full"]["random_score"])

    state_path = out_dir / "joint_set_null_calibration_state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    else:
        state = {}
    if not compatible_state(
        state, data_sha, metadata_sha, min_train, last_n, selection_window,
        validation_scenarios, validation_candidates, target_worlds,
    ):
        state = {
            "report_version": REPORT_VERSION,
            "data_sha256": data_sha,
            "metadata_sha256": metadata_sha,
            "min_train": int(min_train),
            "last_n": int(last_n),
            "selection_window": int(selection_window),
            "validation_scenarios": int(validation_scenarios),
            "validation_candidates": int(validation_candidates),
            "predeclared_config_count": len(candidate_configs()),
            "target_worlds": int(target_worlds),
            "worlds": [],
        }

    worlds = list(state.get("worlds", []))
    remaining = max(0, int(target_worlds) - len(worlds))
    todo = min(max(0, int(worlds_per_run)), remaining)
    for _ in range(todo):
        world_index = len(worlds) + 1
        seed = world_seed(data_sha, world_index)
        x_null = synthetic_fair_world(len(x_real), seed)
        result = run_world(
            x_null, metadata_design, min_train, last_n, selection_window,
            validation_scenarios, validation_candidates, random_score, seed,
        )
        worlds.append({"world": world_index, "seed": seed, **result})
        state["worlds"] = worlds
        write_json(state_path, state)

    summary = summarize(state, observed_delta)
    write_json(out_dir / "joint_set_null_calibration_summary.json", summary)
    (out_dir / "joint_set_null_calibration_report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Matched-budget synthetic-null calibration for the Joint Set Research suite")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--metadata", type=Path, default=Path("loto7_agent_output/research_external_metadata.csv"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--selection-window", type=int, default=120)
    ap.add_argument("--validation-scenarios", type=int, default=512)
    ap.add_argument("--validation-candidates", type=int, default=96)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--target-worlds", type=int, default=64)
    ap.add_argument("--worlds-per-run", type=int, default=1)
    ap.add_argument("--cutoff-hour-jst", type=int, default=18)
    args = ap.parse_args()
    result = run(
        args.csv, args.out_dir, args.metadata, args.min_train, args.last_n,
        args.selection_window, args.validation_scenarios, args.validation_candidates,
        args.random_reps, args.target_worlds, args.worlds_per_run, args.cutoff_hour_jst,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
