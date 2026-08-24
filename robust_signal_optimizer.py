#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import precision_random_baseline as prb
import separated_optimizer as so
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, read_csv_flexible

OPTIMIZER_VERSION = "robust-signal-era-gated-v1"
ERA_RANGES = ((101, 250), (251, 400), (401, 550), (551, 10**9))
ERA_MAX_REGRESSION = 0.003
ERA_MIN_IMPROVED = 2
ERA_IMPROVEMENT_EPS = 0.00025
WORST_ERA_MAX_REGRESSION = 0.002


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


def aggregate_windows(rows: Sequence[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    windows: Dict[str, Dict[str, float]] = {"full": so.aggregate_signal(rows)}
    for n in (120, 60, 30):
        windows[str(n)] = so.aggregate_signal(rows[-min(n, len(rows)):])
    return windows


def replay_signal_with_eras(
    x: np.ndarray,
    cfg: v2.ModelConfig,
    min_train: int,
    keep_q: bool = False,
) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, object]], List[np.ndarray]]:
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    all_rows: List[Dict[str, float]] = []
    era_rows: Dict[Tuple[int, int], List[Dict[str, float]]] = {r: [] for r in ERA_RANGES}
    qs: List[np.ndarray] = []

    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, cfg)
        actual_idx = np.flatnonzero(x[t])
        row = so.signal_row(q, actual_idx)
        all_rows.append(row)
        round_no = t + 1
        for lo, hi in ERA_RANGES:
            if lo <= round_no <= hi:
                era_rows[(lo, hi)].append(row)
                break
        if keep_q:
            qs.append(np.asarray(q, dtype=float).copy())
        logw = v2._update_log_weights(x[:t], actual_idx, keys, logw, cfg)

    eras: List[Dict[str, object]] = []
    for lo, hi in ERA_RANGES:
        agg = so.aggregate_signal(era_rows[(lo, hi)])
        eras.append({
            "label": f"{lo}-{hi if hi < 10**9 else 'latest'}",
            "evaluated_rounds": len(era_rows[(lo, hi)]),
            "signal_objective": so.signal_quality(agg),
            "top7_delta_vs_uniform": float(agg.get("top7_hits_delta_vs_uniform", 0.0)),
            "actual_mass_delta_vs_uniform": float(agg.get("actual_mass_delta_vs_uniform", 0.0)),
            "log_edge_vs_uniform": float(agg.get("log_edge_vs_uniform", 0.0)),
            "brier_edge_vs_uniform": float(agg.get("brier_edge_vs_uniform", 0.0)),
        })
    return aggregate_windows(all_rows), eras, qs


def era_accept(candidate_eras: Sequence[Dict[str, object]], incumbent_eras: Sequence[Dict[str, object]]) -> Tuple[bool, Dict[str, object]]:
    cvals = [float(e.get("signal_objective", 0.0)) for e in candidate_eras]
    ivals = [float(e.get("signal_objective", 0.0)) for e in incumbent_eras]
    n = min(len(cvals), len(ivals))
    if n == 0:
        return False, {"era_reason": "no_era_metrics"}
    cvals = cvals[:n]
    ivals = ivals[:n]
    deltas = [c - i for c, i in zip(cvals, ivals)]
    improved = sum(d >= ERA_IMPROVEMENT_EPS for d in deltas)
    checks = {
        "all_eras_not_materially_regressed": all(d >= -ERA_MAX_REGRESSION for d in deltas),
        "multiple_eras_improve": improved >= ERA_MIN_IMPROVED,
        "worst_era_not_regressed": min(cvals) >= min(ivals) - WORST_ERA_MAX_REGRESSION,
    }
    return all(checks.values()), {
        "era_checks": checks,
        "era_deltas": deltas,
        "candidate_era_objectives": cvals,
        "incumbent_era_objectives": ivals,
        "improved_era_count": improved,
        "candidate_worst_era": min(cvals),
        "incumbent_worst_era": min(ivals),
    }


def render_report(record: Dict[str, object]) -> str:
    lines = [
        "# Robust Signal Optimizer — Era Gated",
        "",
        f"- generation: **{record.get('generation')}**",
        f"- incumbent: **{record.get('incumbent_version')}**",
        f"- selected: **{record.get('selected_version')}**",
        f"- accepted: **{'YES' if record.get('signal_accepted') else 'NO'}**",
        f"- selected Signal objective: **{float(record.get('selected_signal_objective', 0.0)):+.5f}**",
        f"- selected overlap: **{float(record.get('selected_overlap', 0.0)):.3f}**",
        "- era gate: **4 eras / >=2 improve / no material era regression**",
        "- Production promotion evidence: **NO**",
        "",
    ]
    for item in record.get("signal_trials", []) or []:
        lines.append(
            f"- {item.get('version')}: overall gain **{float(item.get('signal_gain',0.0)):+.5f}** / "
            f"era improved **{int(item.get('improved_era_count',0))}/4** / "
            f"accepted **{'YES' if item.get('accepted') else 'NO'}**"
        )
    lines += [
        "",
        "> 全期間平均だけでなく複数時代で同方向に改善する候補だけをResearch Parentへ採用します。",
        "> overlap_penaltyはSignal採用後にだけ最適化し、Signal選択には使いません。",
        "",
    ]
    return "\n".join(lines)


def optimize_once(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    feedback_state_path: Path = Path("loto7_agent_output/research_feedback_state.json"),
    research_state_path: Path = Path("loto7_agent_output/v4_research_state.json"),
    guard_path: Path = Path("loto7_agent_output/research_cycle_guard.json"),
    min_train: int = 100,
    pool_size: int = 350,
    random_reps: int = 4096,
    trials: int = 2,
) -> Dict[str, object]:
    guard = load_json(guard_path, {})
    if guard and not bool(guard.get("search_enabled", True)):
        return {"optimized": False, "reason": "research_guard_validation_only"}

    feedback = load_json(feedback_state_path, {})
    research = load_json(research_state_path, {})
    parent = so.cfg_from_obj(feedback.get("accepted_parent_config"))
    if parent is None:
        return {"optimized": False, "reason": "accepted parent unavailable"}

    generation = int(research.get("generation", feedback.get("last_generation", 0)))
    if int(feedback.get("robust_optimizer_last_generation", -1)) >= generation:
        return {"optimized": False, "reason": "generation already processed"}

    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    random_summary = prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)

    incumbent_windows, incumbent_eras, _ = replay_signal_with_eras(x, parent, min_train, keep_q=False)
    ranked: List[Tuple[float, v2.ModelConfig, Dict[str, Dict[str, float]], List[Dict[str, object]]]] = []
    trial_records: List[Dict[str, object]] = []

    for cfg in so.signal_candidates(parent, data_sha, generation, count=trials):
        windows, eras, _ = replay_signal_with_eras(x, cfg, min_train, keep_q=False)
        base_ok, base_decision = so.signal_accept(windows, incumbent_windows, cfg, parent)
        era_ok, era_decision = era_accept(eras, incumbent_eras)
        ok = bool(base_ok and era_ok)
        rec = {
            "version": cfg.version(),
            "accepted": ok,
            **base_decision,
            **era_decision,
        }
        trial_records.append(rec)
        if ok:
            ranked.append((so.weighted_signal_objective(windows, cfg), cfg, windows, eras))

    signal_accepted = bool(ranked)
    if ranked:
        ranked.sort(key=lambda z: z[0], reverse=True)
        _, signal_cfg, signal_windows, selected_eras = ranked[0]
        signal_windows, selected_eras, qs = replay_signal_with_eras(x, signal_cfg, min_train, keep_q=True)
        overlap, p_windows, portfolio_trials = so.choose_overlap(
            x, qs, signal_cfg, random_summary, min_train, pool_size
        )
        selected = v2.ModelConfig(
            name=signal_cfg.name,
            eta=signal_cfg.eta,
            decay=signal_cfg.decay,
            expert_uniform_mix=signal_cfg.expert_uniform_mix,
            final_uniform_mix=signal_cfg.final_uniform_mix,
            overlap_penalty=round(float(overlap), 6),
        )
        summary = so.combined_summary(
            selected, signal_windows, p_windows, random_summary, data_sha, min_train, pool_size
        )
        feedback["accepted_parent_version"] = selected.version()
        feedback["accepted_parent_config"] = asdict(selected)
        feedback["accepted_parent_summary"] = summary
        research["research_parent_config"] = asdict(selected)
        research["research_winner"] = selected.version()

        events_path = out_dir / "run_events.json"
        events = load_json(events_path, {})
        events["robust_signal_parent_updated"] = True
        events["force_checkpoint"] = True
        write_json(events_path, events)
    else:
        selected = parent
        selected_eras = incumbent_eras
        portfolio_trials = []
        summary = feedback.get("accepted_parent_summary") if isinstance(feedback.get("accepted_parent_summary"), dict) else {}

    selected_signal_objective = so.weighted_signal_objective(
        signal_windows if signal_accepted else incumbent_windows,
        selected,
    )
    research["robust_optimizer_last"] = {
        "generation": generation,
        "signal_accepted": signal_accepted,
        "selected_version": selected.version(),
        "signal_objective": selected_signal_objective,
        "portfolio_overlap": selected.overlap_penalty,
        "era_positive_count": sum(float(e.get("signal_objective", 0.0)) > 0 for e in selected_eras),
        "worst_era_signal_objective": min((float(e.get("signal_objective", 0.0)) for e in selected_eras), default=0.0),
    }

    feedback["robust_optimizer_last_generation"] = generation
    feedback["robust_optimizer_trials_total"] = int(feedback.get("robust_optimizer_trials_total", 0)) + len(trial_records)
    feedback["robust_optimizer_accept_count"] = int(feedback.get("robust_optimizer_accept_count", 0)) + int(signal_accepted)
    # Keep the shared signal-trial budget monotone across old/new separated optimizers.
    feedback["separated_optimizer_trials_total"] = int(feedback.get("separated_optimizer_trials_total", 0)) + len(trial_records)

    write_json(feedback_state_path, feedback)
    write_json(research_state_path, research)

    era_summary = {
        "report_version": OPTIMIZER_VERSION,
        "data_sha256": data_sha,
        "model_version": selected.version(),
        "eras": selected_eras,
        "positive_eras": sum(float(e.get("signal_objective", 0.0)) > 0 for e in selected_eras),
        "worst_era_signal_objective": min((float(e.get("signal_objective", 0.0)) for e in selected_eras), default=0.0),
        "independent_evidence": False,
        "production_promotion_eligible": False,
    }
    write_json(out_dir / "era_signal_robustness.json", era_summary)

    record: Dict[str, object] = {
        "optimizer_version": OPTIMIZER_VERSION,
        "generation": generation,
        "data_sha256": data_sha,
        "incumbent_version": parent.version(),
        "signal_accepted": signal_accepted,
        "selected_version": selected.version(),
        "selected_signal_objective": selected_signal_objective,
        "selected_overlap": float(selected.overlap_penalty),
        "selected_eras": selected_eras,
        "signal_trials": trial_records,
        "portfolio_trials": portfolio_trials,
        "precision_random_reps": int(random_summary.get("random_portfolios_per_round", 0)),
        "independent_evidence": False,
        "production_promotion_eligible": False,
    }
    write_json(out_dir / "robust_signal_optimizer_state.json", record)
    (out_dir / "robust_signal_optimizer_report.md").write_text(render_report(record), encoding="utf-8")
    return {"optimized": True, **record}


def main() -> int:
    ap = argparse.ArgumentParser(description="Signal-primary optimizer with four-era robustness gate")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--guard", type=Path, default=Path("loto7_agent_output/research_cycle_guard.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--pool-size", type=int, default=350)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--trials", type=int, default=2)
    args = ap.parse_args()
    result = optimize_once(
        args.csv, args.out_dir, args.feedback_state, args.research_state,
        args.guard, args.min_train, args.pool_size, args.random_reps, args.trials,
    )
    print(f"[ROBUST-SIGNAL] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
