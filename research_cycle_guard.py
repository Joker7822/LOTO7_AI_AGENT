#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import separated_optimizer as so
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "research-cycle-guard-v2-data-scoped"
MAX_SIGNAL_TRIALS_PER_DATA = 800
MAX_STALE_GENERATIONS = 300
ERA_RANGES = ((101, 250), (251, 400), (401, 550), (551, 10**9))


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


def cfg_from_obj(obj: object) -> Optional[v2.ModelConfig]:
    return so.cfg_from_obj(obj)


def parse_generation_from_model(version_or_name: str) -> Optional[int]:
    m = re.search(r"(?:^|-)g(\d{1,7})(?:-|$)", str(version_or_name or ""))
    return int(m.group(1)) if m else None


def _round_no(clean, t: int) -> int:
    if "回別" in clean.columns:
        text = str(clean["回別"].iloc[t])
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return int(digits)
    return t + 1


def era_signal_metrics(x: np.ndarray, clean, cfg: v2.ModelConfig, min_train: int) -> List[Dict[str, object]]:
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    buckets: Dict[Tuple[int, int], List[Dict[str, float]]] = {r: [] for r in ERA_RANGES}
    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, cfg)
        actual_idx = np.flatnonzero(x[t])
        row = so.signal_row(q, actual_idx)
        round_no = _round_no(clean, t)
        for lo, hi in ERA_RANGES:
            if lo <= round_no <= hi:
                buckets[(lo, hi)].append(row)
                break
        logw = v2._update_log_weights(x[:t], actual_idx, keys, logw, cfg)

    out: List[Dict[str, object]] = []
    for lo, hi in ERA_RANGES:
        rows = buckets[(lo, hi)]
        agg = so.aggregate_signal(rows)
        out.append({
            "label": f"{lo}-{hi if hi < 10**9 else 'latest'}",
            "first_round": lo,
            "last_round": None if hi >= 10**9 else hi,
            "evaluated_rounds": len(rows),
            "signal_objective": so.signal_quality(agg),
            "top7_hits": float(agg.get("top7_hits", 0.0)),
            "top7_delta_vs_uniform": float(agg.get("top7_hits_delta_vs_uniform", 0.0)),
            "actual_mass_delta_vs_uniform": float(agg.get("actual_mass_delta_vs_uniform", 0.0)),
            "log_edge_vs_uniform": float(agg.get("log_edge_vs_uniform", 0.0)),
            "brier_edge_vs_uniform": float(agg.get("brier_edge_vs_uniform", 0.0)),
        })
    return out


def render_era_report(model_version: str, eras: Sequence[Dict[str, object]]) -> str:
    lines = [
        "# Research Parent Era Signal Robustness",
        "",
        f"- model: **{model_version}**",
        "- use: **Research robustness diagnostic only**",
        "",
        "| Era | rounds | Signal objective | Top7 edge | log edge | Brier edge |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for e in eras:
        lines.append(
            f"| {e['label']} | {e['evaluated_rounds']} | {float(e['signal_objective']):+.5f} | "
            f"{float(e['top7_delta_vs_uniform']):+.4f} | {float(e['log_edge_vs_uniform']):+.5f} | "
            f"{float(e['brier_edge_vs_uniform']):+.6f} |"
        )
    if eras:
        vals = [float(e["signal_objective"]) for e in eras]
        lines += [
            "",
            f"- positive eras: **{sum(v > 0 for v in vals)}/{len(vals)}**",
            f"- worst-era Signal objective: **{min(vals):+.5f}**",
            "",
        ]
    lines += [
        "> 全期間平均だけでなく、時代をまたいで同じ方向のSignalが出ているかを確認します。",
        "",
    ]
    return "\n".join(lines)


def decide_guard(
    data_sha: str,
    generation: int,
    last_data_change_generation: int,
    parent_version: str,
    signal_trials_total: int,
    previous: Dict[str, object],
    max_trials: int = MAX_SIGNAL_TRIALS_PER_DATA,
    max_stale_generations: int = MAX_STALE_GENERATIONS,
    validation_complete: bool = False,
) -> Dict[str, object]:
    previous_sha = str(previous.get("data_sha256", ""))
    data_changed_since_guard = bool(previous_sha) and previous_sha != data_sha

    # Trial budgets are scoped to one immutable data SHA. On a new draw, record the
    # current cumulative counter as the new baseline instead of carrying the old
    # exhausted budget into the next research cycle.
    if data_changed_since_guard:
        trial_counter_at_data_start = int(signal_trials_total)
        data_start_generation = int(generation)
    else:
        trial_counter_at_data_start = int(previous.get("trial_counter_at_data_start", 0))
        data_start_generation = int(previous.get("data_start_generation", last_data_change_generation))

    signal_trials_this_data = max(0, int(signal_trials_total) - trial_counter_at_data_start)

    parent_generation = parse_generation_from_model(parent_version)
    if parent_generation is None:
        parent_generation = data_start_generation

    # A model selected on the previous data receives a fresh plateau clock after a
    # genuinely new draw arrives. This prevents SEARCH from reopening for only one
    # generation and then immediately re-pausing because the model name is old.
    plateau_anchor_generation = max(
        int(parent_generation),
        int(last_data_change_generation),
        int(data_start_generation),
    )
    stale_generations = max(0, int(generation) - plateau_anchor_generation)

    reasons: List[str] = []
    if signal_trials_this_data >= max_trials:
        reasons.append("signal_trial_budget_exhausted")
    if stale_generations >= max_stale_generations:
        reasons.append("signal_parent_plateau")

    search_enabled = bool(data_changed_since_guard or not reasons)
    if data_changed_since_guard:
        reasons = ["new_data_reopens_search"]

    if search_enabled:
        mode = "SEARCH"
    elif validation_complete:
        mode = "WAIT_FOR_NEW_DATA"
        reasons = [*reasons, "matched_null_calibration_complete"]
    else:
        mode = "VALIDATION_ONLY"

    return {
        "report_version": REPORT_VERSION,
        "data_sha256": data_sha,
        "generation": int(generation),
        "last_data_change_generation": int(last_data_change_generation),
        "data_start_generation": int(data_start_generation),
        "trial_counter_at_data_start": int(trial_counter_at_data_start),
        "parent_version": parent_version,
        "parent_generation": int(parent_generation),
        "plateau_anchor_generation": int(plateau_anchor_generation),
        "generations_since_plateau_anchor": int(stale_generations),
        # Backward-compatible alias retained for existing status consumers.
        "generations_since_parent_change": int(stale_generations),
        "signal_trials_total": int(signal_trials_total),
        "signal_trials_this_data": int(signal_trials_this_data),
        "max_signal_trials_per_data": int(max_trials),
        "max_stale_generations": int(max_stale_generations),
        "data_changed_since_guard": bool(data_changed_since_guard),
        "search_enabled": bool(search_enabled),
        "validation_complete": bool(validation_complete),
        "mode": mode,
        "reasons": reasons,
    }


def matched_validation_complete(out_dir: Path, data_sha: str, expected_trial_budget: int) -> bool:
    obj = load_json(out_dir / "matched_budget_null_calibration_summary.json", {})
    if not obj:
        return False
    return bool(
        obj.get("data_sha256") == data_sha
        and int(obj.get("matched_signal_trial_budget", -1)) == int(expected_trial_budget)
        and obj.get("calibration_complete") is True
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Pause same-data Research after a scoped budget/plateau, emit era robustness, and wait after matched validation")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--max-trials", type=int, default=MAX_SIGNAL_TRIALS_PER_DATA)
    ap.add_argument("--max-stale-generations", type=int, default=MAX_STALE_GENERATIONS)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    research = load_json(args.research_state, {})
    feedback = load_json(args.feedback_state, {})
    state_path = args.out_dir / "research_cycle_guard.json"
    previous = load_json(state_path, {})

    data_sha = fingerprint_file(args.csv)
    generation = int(research.get("generation", 0))
    last_data_change_generation = int(research.get("last_data_change_generation", generation))
    parent_version = str(
        feedback.get("accepted_parent_version")
        or research.get("research_winner")
        or research.get("champion_version")
        or ""
    )
    signal_trials_total = int(feedback.get("separated_optimizer_trials_total", 0))

    provisional = decide_guard(
        data_sha, generation, last_data_change_generation, parent_version,
        signal_trials_total, previous, args.max_trials, args.max_stale_generations,
        validation_complete=False,
    )
    validation_complete = matched_validation_complete(
        args.out_dir, data_sha, int(provisional.get("signal_trials_this_data", 0))
    )
    guard = decide_guard(
        data_sha, generation, last_data_change_generation, parent_version,
        signal_trials_total, previous, args.max_trials, args.max_stale_generations,
        validation_complete=validation_complete,
    )

    parent = cfg_from_obj(feedback.get("accepted_parent_config") or research.get("research_parent_config"))
    if parent is not None and args.csv.exists():
        df = read_csv_flexible(args.csv)
        x, clean = make_history(df)
        eras = era_signal_metrics(x, clean, parent, args.min_train)
        era_summary = {
            "report_version": REPORT_VERSION,
            "data_sha256": data_sha,
            "model_version": parent.version(),
            "config": {
                "name": parent.name, "eta": parent.eta, "decay": parent.decay,
                "expert_uniform_mix": parent.expert_uniform_mix,
                "final_uniform_mix": parent.final_uniform_mix,
                "overlap_penalty": parent.overlap_penalty,
            },
            "eras": eras,
            "positive_eras": sum(float(e["signal_objective"]) > 0 for e in eras),
            "worst_era_signal_objective": min((float(e["signal_objective"]) for e in eras), default=0.0),
            "independent_evidence": False,
            "production_promotion_eligible": False,
        }
        write_json(args.out_dir / "era_signal_robustness.json", era_summary)
        (args.out_dir / "era_signal_robustness_report.md").write_text(
            render_era_report(parent.version(), eras), encoding="utf-8"
        )
        guard["era_positive_count"] = era_summary["positive_eras"]
        guard["era_worst_signal_objective"] = era_summary["worst_era_signal_objective"]

    write_json(state_path, guard)
    print(f"[RESEARCH-GUARD] mode={guard['mode']} generation={generation} trials_this_data={guard['signal_trials_this_data']} reasons={','.join(guard['reasons']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
