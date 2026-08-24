#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
import precision_random_baseline as prb
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

OPTIMIZER_VERSION = "separated-signal-portfolio-v1"
SIGNAL_WEIGHTS = {"full": 0.35, "120": 0.35, "60": 0.20, "30": 0.10}
SIGNAL_TRIALS = 2
SIGNAL_MIN_GAIN = 0.0005
SIGNAL_LOG_TOL = 0.00025
SIGNAL_RECENT_LOG_TOL = 0.001
ETA_BOUNDS = (0.05, 6.0)
DECAY_BOUNDS = (0.970, 0.9998)
EXPERT_MIX_BOUNDS = (0.0, 0.50)
FINAL_MIX_BOUNDS = (0.0, 0.60)
PORTFOLIO_OVERLAPS = (0.40, 0.65, 0.90, 1.15, 1.40, 1.70, 2.00)
UNIFORM_Q = np.full(37, 1.0 / 37.0, dtype=float)
UNIFORM_TOP7_HITS = 49.0 / 37.0
UNIFORM_ACTUAL_MASS = 7.0 / 37.0
UNIFORM_LOG_PROB = math.log(1.0 / 37.0)


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
    if not isinstance(obj, dict):
        return None
    try:
        return v2.ModelConfig(
            name=str(obj["name"]), eta=float(obj["eta"]), decay=float(obj["decay"]),
            expert_uniform_mix=float(obj["expert_uniform_mix"]),
            final_uniform_mix=float(obj["final_uniform_mix"]), overlap_penalty=float(obj["overlap_penalty"]),
        )
    except Exception:
        return None


def signal_signature(cfg: v2.ModelConfig) -> str:
    raw = json.dumps({
        "eta": round(float(cfg.eta), 9), "decay": round(float(cfg.decay), 9),
        "expert_uniform_mix": round(float(cfg.expert_uniform_mix), 9),
        "final_uniform_mix": round(float(cfg.final_uniform_mix), 9),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def clamp(v: float, bounds: Tuple[float, float]) -> float:
    return min(bounds[1], max(bounds[0], float(v)))


def signal_candidates(parent: v2.ModelConfig, data_sha: str, generation: int,
                      count: int = SIGNAL_TRIALS) -> List[v2.ModelConfig]:
    seed = int(hashlib.sha256(
        f"{OPTIMIZER_VERSION}|{data_sha}|{generation}|{signal_signature(parent)}".encode()
    ).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    out: List[v2.ModelConfig] = []
    seen = {signal_signature(parent)}
    for i in range(max(0, count)):
        if i == 0:
            eta = parent.eta * math.exp(float(rng.normal(0.0, 0.30)))
            decay = parent.decay + float(rng.normal(0.0, 0.0025))
            eum = parent.expert_uniform_mix + float(rng.normal(0.0, 0.035))
            fum = parent.final_uniform_mix + float(rng.normal(0.0, 0.045))
        else:
            eta = math.exp(rng.uniform(math.log(ETA_BOUNDS[0]), math.log(ETA_BOUNDS[1])))
            decay = rng.uniform(*DECAY_BOUNDS)
            eum = rng.uniform(*EXPERT_MIX_BOUNDS)
            fum = rng.uniform(*FINAL_MIX_BOUNDS)
        cfg = v2.ModelConfig(
            name=f"signal-g{generation:05d}-c{i+1:02d}",
            eta=round(clamp(eta, ETA_BOUNDS), 6),
            decay=round(clamp(decay, DECAY_BOUNDS), 6),
            expert_uniform_mix=round(clamp(eum, EXPERT_MIX_BOUNDS), 6),
            final_uniform_mix=round(clamp(fum, FINAL_MIX_BOUNDS), 6),
            overlap_penalty=float(parent.overlap_penalty),
        )
        sig = signal_signature(cfg)
        if sig not in seen:
            seen.add(sig)
            out.append(cfg)
    return out


def uniform_brier(actual_idx: np.ndarray) -> float:
    y = np.zeros(37, dtype=float)
    y[actual_idx] = 1.0 / 7.0
    return float(np.sum((UNIFORM_Q - y) ** 2))


def signal_row(q: np.ndarray, actual_idx: np.ndarray) -> Dict[str, float]:
    q = np.maximum(np.asarray(q, dtype=float), 1e-15)
    q = q / q.sum()
    y = np.zeros(37, dtype=float)
    y[actual_idx] = 1.0 / 7.0
    top7 = set(np.argsort(q)[-7:].tolist())
    actual = set(int(i) for i in actual_idx.tolist())
    return {
        "top7_hits": float(len(top7 & actual)),
        "actual_mass": float(q[actual_idx].sum()),
        "mean_log_prob_actual": float(np.mean(np.log(q[actual_idx]))),
        "brier": float(np.sum((q - y) ** 2)),
        "uniform_brier": uniform_brier(actual_idx),
    }


def aggregate_signal(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {k: 0.0 for k in (
            "top7_hits", "actual_mass", "mean_log_prob_actual", "brier", "uniform_brier",
            "top7_hits_delta_vs_uniform", "actual_mass_delta_vs_uniform",
            "log_edge_vs_uniform", "brier_edge_vs_uniform",
        )}
    out = {
        "top7_hits": float(np.mean([r["top7_hits"] for r in rows])),
        "actual_mass": float(np.mean([r["actual_mass"] for r in rows])),
        "mean_log_prob_actual": float(np.mean([r["mean_log_prob_actual"] for r in rows])),
        "brier": float(np.mean([r["brier"] for r in rows])),
        "uniform_brier": float(np.mean([r["uniform_brier"] for r in rows])),
    }
    out["top7_hits_delta_vs_uniform"] = out["top7_hits"] - UNIFORM_TOP7_HITS
    out["actual_mass_delta_vs_uniform"] = out["actual_mass"] - UNIFORM_ACTUAL_MASS
    out["log_edge_vs_uniform"] = out["mean_log_prob_actual"] - UNIFORM_LOG_PROB
    out["brier_edge_vs_uniform"] = out["uniform_brier"] - out["brier"]
    return out


def signal_quality(s: Dict[str, float]) -> float:
    return float(
        s.get("log_edge_vs_uniform", 0.0)
        + 2.0 * s.get("actual_mass_delta_vs_uniform", 0.0)
        + 0.10 * s.get("top7_hits_delta_vs_uniform", 0.0)
        + 25.0 * s.get("brier_edge_vs_uniform", 0.0)
    )


def signal_boundary_penalty(cfg: v2.ModelConfig) -> float:
    values = [
        (cfg.eta, ETA_BOUNDS), (cfg.decay, DECAY_BOUNDS),
        (cfg.expert_uniform_mix, EXPERT_MIX_BOUNDS), (cfg.final_uniform_mix, FINAL_MIX_BOUNDS),
    ]
    total = 0.0
    for value, (lo, hi) in values:
        frac = (float(value) - lo) / max(hi - lo, 1e-12)
        dist = min(frac, 1.0 - frac)
        total += max(0.0, (0.05 - dist) / 0.05)
    return float(total)


def replay_signal(x: np.ndarray, cfg: v2.ModelConfig, min_train: int,
                  keep_q: bool = False) -> Tuple[Dict[str, Dict[str, float]], List[np.ndarray]]:
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    rows: List[Dict[str, float]] = []
    qs: List[np.ndarray] = []
    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, cfg)
        actual_idx = np.flatnonzero(x[t])
        rows.append(signal_row(q, actual_idx))
        if keep_q:
            qs.append(np.asarray(q, dtype=float).copy())
        logw = v2._update_log_weights(x[:t], actual_idx, keys, logw, cfg)
    windows: Dict[str, Dict[str, float]] = {"full": aggregate_signal(rows)}
    for n in (120, 60, 30):
        windows[str(n)] = aggregate_signal(rows[-min(n, len(rows)):])
    return windows, qs


def weighted_signal_objective(windows: Dict[str, Dict[str, float]], cfg: Optional[v2.ModelConfig] = None) -> float:
    value = sum(SIGNAL_WEIGHTS[name] * signal_quality(windows[name]) for name in SIGNAL_WEIGHTS)
    if cfg is not None:
        value -= 0.005 * signal_boundary_penalty(cfg)
    return float(value)


def signal_accept(candidate_windows: Dict[str, Dict[str, float]], incumbent_windows: Dict[str, Dict[str, float]],
                  candidate_cfg: v2.ModelConfig, incumbent_cfg: v2.ModelConfig) -> Tuple[bool, Dict[str, object]]:
    cobj = weighted_signal_objective(candidate_windows, candidate_cfg)
    iobj = weighted_signal_objective(incumbent_windows, incumbent_cfg)
    cf = candidate_windows["full"]
    inf = incumbent_windows["full"]
    c120 = candidate_windows["120"]
    i120 = incumbent_windows["120"]
    checks = {
        "signal_objective_improves": cobj >= iobj + SIGNAL_MIN_GAIN,
        "full_log_not_regressed": float(cf["log_edge_vs_uniform"]) >= float(inf["log_edge_vs_uniform"]) - SIGNAL_LOG_TOL,
        "recent120_log_not_regressed": float(c120["log_edge_vs_uniform"]) >= float(i120["log_edge_vs_uniform"]) - SIGNAL_RECENT_LOG_TOL,
        "full_brier_not_regressed": float(cf["brier_edge_vs_uniform"]) >= float(inf["brier_edge_vs_uniform"]) - 0.00005,
    }
    return all(checks.values()), {
        "candidate_signal_objective": cobj,
        "incumbent_signal_objective": iobj,
        "signal_gain": cobj - iobj,
        "checks": checks,
    }


def aggregate_portfolio(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {"max_hits": 0.0, "mean_hits": 0.0, "ge3": 0.0, "ge4": 0.0, "score": 0.0}
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in rows])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in rows])),
        "ge3": float(np.mean([r["ge3"] for r in rows])),
        "ge4": float(np.mean([r["ge4"] for r in rows])),
        "score": float(np.mean([r["score"] for r in rows])),
    }


def portfolio_windows(x: np.ndarray, qs: Sequence[np.ndarray], overlap: float,
                      min_train: int, pool_size: int) -> Dict[str, Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for offset, t in enumerate(range(min_train, len(x))):
        q = qs[offset]
        tickets = make_ticket_portfolio(
            q, n_tickets=5, seed=65_000_000 + t * 1009,
            pool_size=pool_size, overlap_penalty=float(overlap),
        )
        actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
        m = v2._portfolio_metrics(tickets, actual_set)
        rows.append({
            "max_hits": float(m["max_hits"]), "mean_hits": float(m["mean_hits"]),
            "ge3": float(m["ge3"]), "ge4": float(m["ge4"]), "score": float(v3.row_score(m)),
        })
    windows: Dict[str, Dict[str, float]] = {"full": aggregate_portfolio(rows)}
    for n in (120, 60, 30):
        windows[str(n)] = aggregate_portfolio(rows[-min(n, len(rows)):])
    return windows


def combined_summary(cfg: v2.ModelConfig, signal_windows: Dict[str, Dict[str, float]],
                     portfolio: Dict[str, Dict[str, float]], random_summary: Dict[str, object],
                     data_sha: str, min_train: int, pool_size: int) -> Dict[str, object]:
    rw = random_summary.get("windows") or {}
    windows: Dict[str, Dict[str, object]] = {}
    for name in ("full", "120", "60", "30"):
        p = portfolio[name]
        r = rw.get(name) or {}
        windows[name] = {
            **p,
            "random_max_hits": float(r.get("random_max_hits", 0.0)),
            "random_mean_hits": float(r.get("random_mean_hits", 0.0)),
            "random_ge3": float(r.get("random_ge3", 0.0)),
            "random_ge4": float(r.get("random_ge4", 0.0)),
            "random_score": float(r.get("random_score", 0.0)),
            "score_delta_vs_random": float(p["score"]) - float(r.get("random_score", 0.0)),
            "max_hits_delta_vs_random": float(p["max_hits"]) - float(r.get("random_max_hits", 0.0)),
            "signal": signal_windows[name],
        }
    feedback_obj = float(sum(
        SIGNAL_WEIGHTS[name] * float(windows[name]["score_delta_vs_random"]) for name in SIGNAL_WEIGHTS
    ))
    return {
        "report_version": "research-feedback-v1",
        "optimizer_version": OPTIMIZER_VERSION,
        "evaluation_type": "signal_primary_then_portfolio_policy",
        "model_version": cfg.version(), "config": asdict(cfg),
        "evaluated_rounds": int(random_summary.get("evaluated_rounds", 0)),
        "min_train": int(min_train), "pool_size": int(pool_size),
        "windows": windows,
        "feedback_objective": feedback_obj,
        "signal_objective": weighted_signal_objective(signal_windows, cfg),
        "data_sha256": data_sha,
        "independent_evidence": False, "promotion_eligible": False,
    }


def choose_overlap(x: np.ndarray, qs: Sequence[np.ndarray], signal_cfg: v2.ModelConfig,
                   random_summary: Dict[str, object], min_train: int, pool_size: int) -> Tuple[float, Dict[str, Dict[str, float]], List[Dict[str, float]]]:
    candidates = sorted(set([round(float(signal_cfg.overlap_penalty), 6), *PORTFOLIO_OVERLAPS]))
    trials: List[Tuple[float, float, Dict[str, Dict[str, float]]]] = []
    records: List[Dict[str, float]] = []
    rw = random_summary.get("windows") or {}
    for overlap in candidates:
        windows = portfolio_windows(x, qs, overlap, min_train, pool_size)
        objective = float(sum(
            SIGNAL_WEIGHTS[name] * (float(windows[name]["score"]) - float((rw.get(name) or {}).get("random_score", 0.0)))
            for name in SIGNAL_WEIGHTS
        ))
        records.append({"overlap_penalty": float(overlap), "portfolio_objective": objective})
        trials.append((objective, float(overlap), windows))
    trials.sort(key=lambda x: (x[0], -abs(x[1] - 1.0)), reverse=True)
    return trials[0][1], trials[0][2], records


def render_report(record: Dict[str, object]) -> str:
    lines = [
        "# Signal-Primary / Portfolio-Separate Optimizer",
        "",
        f"- generation: **{record.get('generation')}**",
        f"- incumbent: **{record.get('incumbent_version')}**",
        f"- signal candidate accepted: **{'YES' if record.get('signal_accepted') else 'NO'}**",
        f"- selected parent: **{record.get('selected_version')}**",
        f"- Signal objective: **{float(record.get('selected_signal_objective',0.0)):+.5f}**",
        f"- Portfolio overlap: **{float(record.get('selected_overlap',0.0)):.3f}**",
        "- Signal選択で overlap_penalty を使用: **NO**",
        "- Portfolio最適化で Signal候補を変更: **NO**",
        "- Production昇格証拠: **使用しない**",
        "",
    ]
    for item in record.get("signal_trials", []) or []:
        lines.append(
            f"- {item.get('version')}: signal gain **{float(item.get('signal_gain',0.0)):+.5f}** / "
            f"accepted **{'YES' if item.get('accepted') else 'NO'}**"
        )
    if record.get("portfolio_trials"):
        lines += ["", "Portfolio policy trials:"]
        for item in record["portfolio_trials"]:
            lines.append(f"- overlap={float(item['overlap_penalty']):.3f}: objective **{float(item['portfolio_objective']):+.4f}**")
    lines += [
        "",
        "> Signalパラメータを先に確定し、その後に5口分散ポリシーだけを最適化します。",
        "> 過去Researchであり、Future OOS Champion昇格には使用しません。",
        "",
    ]
    return "\n".join(lines)


def optimize_once(csv_path: Path = Path("loto7.csv"), out_dir: Path = Path("loto7_agent_output"),
                  feedback_state_path: Path = Path("loto7_agent_output/research_feedback_state.json"),
                  research_state_path: Path = Path("loto7_agent_output/v4_research_state.json"),
                  min_train: int = 100, pool_size: int = 350, random_reps: int = 4096,
                  trials: int = SIGNAL_TRIALS) -> Dict[str, object]:
    feedback = load_json(feedback_state_path, {})
    research = load_json(research_state_path, {})
    parent = cfg_from_obj(feedback.get("accepted_parent_config"))
    if parent is None:
        return {"optimized": False, "reason": "accepted parent unavailable"}
    generation = int(research.get("generation", feedback.get("last_generation", 0)))
    if int(feedback.get("separated_optimizer_last_generation", -1)) >= generation:
        return {"optimized": False, "reason": "generation already processed"}

    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    random_summary = prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)

    cache_path = out_dir / "separated_signal_cache.json"
    cache = load_json(cache_path, {"optimizer_version": OPTIMIZER_VERSION, "entries": {}})
    entries = cache.setdefault("entries", {})
    assert isinstance(entries, dict)

    def cached_signal(cfg: v2.ModelConfig, keep_q: bool = False):
        key = hashlib.sha256(f"{OPTIMIZER_VERSION}|{data_sha}|{signal_signature(cfg)}|{min_train}".encode()).hexdigest()
        if not keep_q and isinstance(entries.get(key), dict):
            return entries[key], []
        windows, qs = replay_signal(x, cfg, min_train, keep_q=keep_q)
        if not keep_q:
            entries[key] = windows
        return windows, qs

    incumbent_windows, _ = cached_signal(parent)
    ranked: List[Tuple[float, v2.ModelConfig, Dict[str, Dict[str, float]], Dict[str, object]]] = []
    trial_records: List[Dict[str, object]] = []
    for cfg in signal_candidates(parent, data_sha, generation, count=trials):
        windows, _ = cached_signal(cfg)
        ok, decision = signal_accept(windows, incumbent_windows, cfg, parent)
        trial_records.append({"version": cfg.version(), "accepted": bool(ok), **decision})
        if ok:
            ranked.append((weighted_signal_objective(windows, cfg), cfg, windows, decision))

    signal_accepted = bool(ranked)
    if ranked:
        ranked.sort(key=lambda z: z[0], reverse=True)
        signal_cfg = ranked[0][1]
        signal_windows = ranked[0][2]
    else:
        signal_cfg = parent
        signal_windows = incumbent_windows

    portfolio_trials: List[Dict[str, float]] = []
    if signal_accepted:
        signal_windows, qs = replay_signal(x, signal_cfg, min_train, keep_q=True)
        overlap, p_windows, portfolio_trials = choose_overlap(
            x, qs, signal_cfg, random_summary, min_train, pool_size
        )
        selected = v2.ModelConfig(
            name=signal_cfg.name, eta=signal_cfg.eta, decay=signal_cfg.decay,
            expert_uniform_mix=signal_cfg.expert_uniform_mix,
            final_uniform_mix=signal_cfg.final_uniform_mix,
            overlap_penalty=round(float(overlap), 6),
        )
        summary = combined_summary(selected, signal_windows, p_windows, random_summary, data_sha, min_train, pool_size)
        feedback["accepted_parent_version"] = selected.version()
        feedback["accepted_parent_config"] = asdict(selected)
        feedback["accepted_parent_summary"] = summary
        research["research_parent_config"] = asdict(selected)
        research["research_winner"] = selected.version()
        research["separated_optimizer_last"] = {
            "generation": generation, "signal_accepted": True,
            "selected_version": selected.version(), "signal_objective": summary["signal_objective"],
            "portfolio_overlap": selected.overlap_penalty,
        }
        events_path = out_dir / "run_events.json"
        events = load_json(events_path, {})
        events["separated_signal_parent_updated"] = True
        events["force_checkpoint"] = True
        write_json(events_path, events)
    else:
        selected = parent
        summary = feedback.get("accepted_parent_summary") if isinstance(feedback.get("accepted_parent_summary"), dict) else {}
        research["separated_optimizer_last"] = {
            "generation": generation, "signal_accepted": False,
            "selected_version": selected.version(),
            "signal_objective": weighted_signal_objective(signal_windows, selected),
            "portfolio_overlap": selected.overlap_penalty,
        }

    feedback["separated_optimizer_last_generation"] = generation
    feedback["separated_optimizer_trials_total"] = int(feedback.get("separated_optimizer_trials_total", 0)) + len(trial_records)
    feedback["separated_optimizer_accept_count"] = int(feedback.get("separated_optimizer_accept_count", 0)) + int(signal_accepted)
    cache["optimizer_version"] = OPTIMIZER_VERSION
    write_json(cache_path, cache)
    write_json(feedback_state_path, feedback)
    write_json(research_state_path, research)

    record: Dict[str, object] = {
        "optimizer_version": OPTIMIZER_VERSION, "generation": generation,
        "data_sha256": data_sha, "incumbent_version": parent.version(),
        "signal_accepted": signal_accepted, "selected_version": selected.version(),
        "selected_signal_objective": weighted_signal_objective(signal_windows, selected),
        "selected_overlap": float(selected.overlap_penalty),
        "signal_trials": trial_records, "portfolio_trials": portfolio_trials,
        "precision_random_reps": int(random_summary.get("random_portfolios_per_round", 0)),
        "independent_evidence": False, "production_promotion_eligible": False,
    }
    write_json(out_dir / "separated_optimizer_state.json", record)
    (out_dir / "separated_optimizer_report.md").write_text(render_report(record), encoding="utf-8")
    return {"optimized": True, **record}


def main() -> int:
    ap = argparse.ArgumentParser(description="Optimize probability Signal first, then optimize only the five-ticket overlap policy")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--pool-size", type=int, default=350)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--trials", type=int, default=SIGNAL_TRIALS)
    args = ap.parse_args()
    result = optimize_once(args.csv, args.out_dir, args.feedback_state, args.research_state,
                           args.min_train, args.pool_size, args.random_reps, args.trials)
    print(f"[SEPARATED-OPT] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
