#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
import research_feedback as rf
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

OPTIMIZER_VERSION = "feedback-optimizer-v2-signal-gated"
ETA_BOUNDS = (0.10, 6.0)
DECAY_BOUNDS = (0.975, 0.9998)
EXPERT_MIX_BOUNDS = (0.02, 0.50)
FINAL_MIX_BOUNDS = (0.02, 0.55)
OVERLAP_BOUNDS = (0.25, 2.00)
DEFAULT_TRIALS = 2
UNIFORM_Q = np.full(37, 1.0 / 37.0, dtype=float)
UNIFORM_TOP7_HITS = 49.0 / 37.0
UNIFORM_ACTUAL_MASS = 7.0 / 37.0
UNIFORM_LOG_PROB = math.log(1.0 / 37.0)
SIGNAL_FULL_LOG_TOL = 0.0005
SIGNAL_FULL_TOP7_TOL = 0.01
SIGNAL_RECENT_LOG_TOL = 0.002
SIGNAL_REQUIRED_IMPROVEMENT_WHEN_NONPOSITIVE = 0.0005
BOUNDARY_REG_WEIGHT = 0.01
SIGNAL_RANK_WEIGHT = 0.25


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


def append_jsonl(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def clamp(v: float, bounds: Tuple[float, float]) -> float:
    return min(bounds[1], max(bounds[0], float(v)))


def config_signature(cfg: v2.ModelConfig) -> str:
    payload = {
        "eta": round(float(cfg.eta), 9),
        "decay": round(float(cfg.decay), 9),
        "expert_uniform_mix": round(float(cfg.expert_uniform_mix), 9),
        "final_uniform_mix": round(float(cfg.final_uniform_mix), 9),
        "overlap_penalty": round(float(cfg.overlap_penalty), 9),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def expanded_candidates(parent: v2.ModelConfig, data_sha: str, generation: int,
                        count: int = DEFAULT_TRIALS) -> List[v2.ModelConfig]:
    if count <= 0:
        return []
    seed = int(hashlib.sha256(
        f"{OPTIMIZER_VERSION}|{data_sha}|{generation}|{config_signature(parent)}".encode()
    ).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    out: List[v2.ModelConfig] = []
    seen = {config_signature(parent)}

    for i in range(count):
        if i == 0 and parent.eta <= 0.85:
            eta = math.exp(rng.uniform(math.log(ETA_BOUNDS[0]), math.log(0.80)))
        elif i == 0:
            eta = parent.eta * math.exp(float(rng.normal(0.0, 0.40)))
        else:
            eta = math.exp(rng.uniform(math.log(ETA_BOUNDS[0]), math.log(ETA_BOUNDS[1])))

        if i == 0:
            decay = parent.decay + float(rng.normal(0.0, 0.0040))
            eum = parent.expert_uniform_mix + float(rng.normal(0.0, 0.060))
            fum = parent.final_uniform_mix + float(rng.normal(0.0, 0.075))
            overlap = parent.overlap_penalty + float(rng.normal(0.0, 0.28))
        else:
            decay = float(rng.uniform(*DECAY_BOUNDS))
            eum = float(rng.uniform(*EXPERT_MIX_BOUNDS))
            fum = float(rng.uniform(*FINAL_MIX_BOUNDS))
            overlap = float(rng.uniform(max(0.70, OVERLAP_BOUNDS[0]), OVERLAP_BOUNDS[1]))

        cfg = v2.ModelConfig(
            name=f"feedback-g{generation:05d}-c{i+1:02d}",
            eta=round(clamp(eta, ETA_BOUNDS), 6),
            decay=round(clamp(decay, DECAY_BOUNDS), 6),
            expert_uniform_mix=round(clamp(eum, EXPERT_MIX_BOUNDS), 6),
            final_uniform_mix=round(clamp(fum, FINAL_MIX_BOUNDS), 6),
            overlap_penalty=round(clamp(overlap, OVERLAP_BOUNDS), 6),
        )
        sig = config_signature(cfg)
        if sig not in seen:
            seen.add(sig)
            out.append(cfg)
    return out


def uniform_brier(actual_idx: np.ndarray) -> float:
    y = np.zeros(37, dtype=float)
    y[actual_idx] = 1.0 / 7.0
    return float(np.sum((UNIFORM_Q - y) ** 2))


def signal_metrics(q: np.ndarray, actual_idx: np.ndarray) -> Dict[str, float]:
    q = np.asarray(q, dtype=float)
    q = np.maximum(q, 1e-15)
    q = q / q.sum()
    y = np.zeros(37, dtype=float)
    y[actual_idx] = 1.0 / 7.0
    top7 = set(np.argsort(q)[-7:].tolist())
    actual = set(int(i) for i in actual_idx.tolist())
    brier = float(np.sum((q - y) ** 2))
    return {
        "top7_hits": float(len(top7 & actual)),
        "actual_mass": float(q[actual_idx].sum()),
        "mean_log_prob_actual": float(np.mean(np.log(q[actual_idx]))),
        "brier": brier,
        "uniform_brier": uniform_brier(actual_idx),
    }


def aggregate_model(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {"max_hits": 0.0, "mean_hits": 0.0, "ge3": 0.0, "ge4": 0.0, "score": 0.0}
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in rows])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in rows])),
        "ge3": float(np.mean([r["ge3"] for r in rows])),
        "ge4": float(np.mean([r["ge4"] for r in rows])),
        "score": float(np.mean([r["score"] for r in rows])),
    }


def aggregate_signal(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {
            "top7_hits": 0.0, "actual_mass": 0.0, "mean_log_prob_actual": 0.0,
            "brier": 0.0, "uniform_brier": 0.0, "top7_hits_delta_vs_uniform": 0.0,
            "actual_mass_delta_vs_uniform": 0.0, "log_edge_vs_uniform": 0.0,
            "brier_edge_vs_uniform": 0.0,
        }
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


def signal_quality(signal: Dict[str, float]) -> float:
    return float(
        signal.get("log_edge_vs_uniform", 0.0)
        + 2.0 * signal.get("actual_mass_delta_vs_uniform", 0.0)
        + 0.10 * signal.get("top7_hits_delta_vs_uniform", 0.0)
        + 25.0 * signal.get("brier_edge_vs_uniform", 0.0)
    )


def simulate_model_only(x: np.ndarray, config: v2.ModelConfig, min_train: int,
                        pool_size: int) -> Tuple[Dict[str, Dict[str, object]], List[Dict[str, object]]]:
    """Replay a candidate and separately score probability signal and 5-ticket portfolio."""
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    seed_offset = int(hashlib.sha256(config.version().encode()).hexdigest()[:8], 16) % 100000
    portfolio_rows: List[Dict[str, float]] = []
    signal_rows: List[Dict[str, float]] = []
    csv_rows: List[Dict[str, object]] = []

    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, config)
        actual_idx = np.flatnonzero(x[t])
        sig = signal_metrics(q, actual_idx)
        tickets = make_ticket_portfolio(
            q,
            n_tickets=5,
            seed=6_000_000 + t * 1000 + seed_offset,
            pool_size=pool_size,
            overlap_penalty=config.overlap_penalty,
        )
        actual_set = set((actual_idx + 1).tolist())
        m = v2._portfolio_metrics(tickets, actual_set)
        score = float(v3.row_score(m))
        portfolio_rows.append({
            "max_hits": float(m["max_hits"]),
            "mean_hits": float(m["mean_hits"]),
            "ge3": float(m["ge3"]),
            "ge4": float(m["ge4"]),
            "score": score,
        })
        signal_rows.append(sig)
        csv_rows.append({
            "round_index": t + 1,
            "model_version": config.version(),
            "model_score": f"{score:.6f}",
            "model_max_hits": f"{m['max_hits']:.0f}",
            "model_mean_hits": f"{m['mean_hits']:.6f}",
            "model_ge3": f"{m['ge3']:.0f}",
            "model_ge4": f"{m['ge4']:.0f}",
            "signal_top7_hits": f"{sig['top7_hits']:.0f}",
            "signal_actual_mass": f"{sig['actual_mass']:.9f}",
            "signal_mean_log_prob": f"{sig['mean_log_prob_actual']:.9f}",
            "signal_brier": f"{sig['brier']:.9f}",
        })
        logw = v2._update_log_weights(x[:t], actual_idx, keys, logw, config)

    windows: Dict[str, Dict[str, object]] = {}
    slices = {"full": len(portfolio_rows), "120": 120, "60": 60, "30": 30}
    for name, n in slices.items():
        pn = portfolio_rows if name == "full" else portfolio_rows[-min(n, len(portfolio_rows)):]
        sn = signal_rows if name == "full" else signal_rows[-min(n, len(signal_rows)):]
        windows[name] = {**aggregate_model(pn), "signal": aggregate_signal(sn)}
    return windows, csv_rows


def summary_with_reference(config: v2.ModelConfig, model_windows: Dict[str, Dict[str, object]],
                           reference_summary: Dict[str, object], data_sha: str,
                           min_train: int, pool_size: int) -> Dict[str, object]:
    ref_windows = reference_summary.get("windows") or {}
    windows: Dict[str, Dict[str, object]] = {}
    for name in ("full", "120", "60", "30"):
        m = model_windows[name]
        ref = ref_windows.get(name) or {}
        random_score = float(ref.get("random_score", 0.0))
        random_max = float(ref.get("random_max_hits", 0.0))
        signal = m.get("signal") if isinstance(m.get("signal"), dict) else None
        windows[name] = {
            "max_hits": float(m.get("max_hits", 0.0)),
            "mean_hits": float(m.get("mean_hits", 0.0)),
            "ge3": float(m.get("ge3", 0.0)),
            "ge4": float(m.get("ge4", 0.0)),
            "score": float(m.get("score", 0.0)),
            "random_max_hits": random_max,
            "random_mean_hits": float(ref.get("random_mean_hits", 0.0)),
            "random_ge3": float(ref.get("random_ge3", 0.0)),
            "random_ge4": float(ref.get("random_ge4", 0.0)),
            "random_score": random_score,
            "score_delta_vs_random": float(m.get("score", 0.0)) - random_score,
            "max_hits_delta_vs_random": float(m.get("max_hits", 0.0)) - random_max,
        }
        if signal is not None:
            windows[name]["signal"] = signal
    objective = float(sum(
        rf.WINDOW_WEIGHTS[name] * float(windows[name]["score_delta_vs_random"])
        for name in rf.WINDOW_WEIGHTS
    ))
    full_signal = windows["full"].get("signal") if isinstance(windows["full"].get("signal"), dict) else {}
    return {
        "report_version": rf.REPORT_VERSION,
        "optimizer_version": OPTIMIZER_VERSION,
        "evaluation_type": "retrospective_full_history_feedback_optimizer_signal_separated",
        "model_version": config.version(),
        "config": asdict(config),
        "evaluated_rounds": int(reference_summary.get("evaluated_rounds", 0)),
        "min_train": int(min_train),
        "pool_size": int(pool_size),
        "windows": windows,
        "feedback_objective": objective,
        "signal_objective": signal_quality(full_signal) if full_signal else 0.0,
        "independent_evidence": False,
        "promotion_eligible": False,
        "data_sha256": data_sha,
    }


def boundary_penalty(cfg: v2.ModelConfig) -> float:
    values = [
        (cfg.eta, ETA_BOUNDS),
        (cfg.decay, DECAY_BOUNDS),
        (cfg.expert_uniform_mix, EXPERT_MIX_BOUNDS),
        (cfg.final_uniform_mix, FINAL_MIX_BOUNDS),
        (cfg.overlap_penalty, OVERLAP_BOUNDS),
    ]
    total = 0.0
    for value, (lo, hi) in values:
        frac = (float(value) - lo) / max(hi - lo, 1e-12)
        dist = min(frac, 1.0 - frac)
        total += max(0.0, (0.08 - dist) / 0.08)
    return float(total)


def effective_objective(summary: Dict[str, object], cfg: Optional[v2.ModelConfig] = None) -> float:
    value = float(summary.get("feedback_objective", 0.0))
    value += SIGNAL_RANK_WEIGHT * float(summary.get("signal_objective", 0.0))
    if cfg is not None:
        value -= BOUNDARY_REG_WEIGHT * boundary_penalty(cfg)
    return value


def _signal(summary: Dict[str, object], window: str) -> Optional[Dict[str, float]]:
    windows = summary.get("windows") or {}
    w = windows.get(window) if isinstance(windows, dict) else None
    if not isinstance(w, dict) or not isinstance(w.get("signal"), dict):
        return None
    return w["signal"]


def decide_accept(candidate: Dict[str, object], incumbent: Dict[str, object],
                  candidate_cfg: Optional[v2.ModelConfig] = None,
                  incumbent_cfg: Optional[v2.ModelConfig] = None) -> Tuple[bool, Dict[str, object]]:
    base_ok, decision = rf.decide_accept(candidate, incumbent)
    checks = dict(decision.get("checks") or {})
    cfull, ifull = _signal(candidate, "full"), _signal(incumbent, "full")
    c120, i120 = _signal(candidate, "120"), _signal(incumbent, "120")

    if cfull is not None and ifull is not None:
        clog = float(cfull.get("log_edge_vs_uniform", 0.0))
        ilog = float(ifull.get("log_edge_vs_uniform", 0.0))
        ctop = float(cfull.get("top7_hits_delta_vs_uniform", 0.0))
        itop = float(ifull.get("top7_hits_delta_vs_uniform", 0.0))
        checks["signal_full_log_not_regressed"] = clog >= ilog - SIGNAL_FULL_LOG_TOL
        checks["signal_full_top7_not_regressed"] = ctop >= itop - SIGNAL_FULL_TOP7_TOL
        if ilog <= 0.0:
            checks["signal_improves_when_incumbent_nonpositive"] = (
                clog >= ilog + SIGNAL_REQUIRED_IMPROVEMENT_WHEN_NONPOSITIVE
            )
    if c120 is not None and i120 is not None:
        checks["signal_recent120_log_not_regressed"] = (
            float(c120.get("log_edge_vs_uniform", 0.0))
            >= float(i120.get("log_edge_vs_uniform", 0.0)) - SIGNAL_RECENT_LOG_TOL
        )
    if candidate_cfg is not None and incumbent_cfg is not None:
        checks["boundary_penalty_not_worse"] = boundary_penalty(candidate_cfg) <= boundary_penalty(incumbent_cfg) + 0.25

    decision["checks"] = checks
    decision["candidate_signal_objective"] = float(candidate.get("signal_objective", 0.0))
    decision["incumbent_signal_objective"] = float(incumbent.get("signal_objective", 0.0))
    decision["candidate_effective_objective"] = effective_objective(candidate, candidate_cfg)
    decision["incumbent_effective_objective"] = effective_objective(incumbent, incumbent_cfg)
    return bool(base_ok and all(checks.values())), decision


def optimizer_cache_key(data_sha: str, config: v2.ModelConfig, min_train: int,
                        pool_size: int) -> str:
    raw = f"{OPTIMIZER_VERSION}|{data_sha}|{config_signature(config)}|{min_train}|{pool_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def evaluate_candidate(x: np.ndarray, config: v2.ModelConfig, data_sha: str,
                       reference_summary: Dict[str, object], cache: Dict[str, object],
                       min_train: int, pool_size: int) -> Tuple[Dict[str, object], List[Dict[str, object]], bool]:
    entries = cache.setdefault("entries", {})
    assert isinstance(entries, dict)
    key = optimizer_cache_key(data_sha, config, min_train, pool_size)
    old = entries.get(key)
    if isinstance(old, dict) and _signal(old, "full") is not None:
        return old, [], True
    model_windows, rows = simulate_model_only(x, config, min_train, pool_size)
    summary = summary_with_reference(config, model_windows, reference_summary, data_sha, min_train, pool_size)
    entries[key] = summary
    cache["optimizer_version"] = OPTIMIZER_VERSION
    return summary, rows, False


def choose_best(incumbent_summary: Dict[str, object],
                trials: Sequence[Tuple[v2.ModelConfig, Dict[str, object]]],
                incumbent_config: Optional[v2.ModelConfig] = None
                ) -> Tuple[Optional[v2.ModelConfig], Optional[Dict[str, object]], List[Dict[str, object]]]:
    decisions: List[Dict[str, object]] = []
    accepted: List[Tuple[float, v2.ModelConfig, Dict[str, object]]] = []
    for cfg, summary in trials:
        ok, decision = decide_accept(summary, incumbent_summary, cfg, incumbent_config)
        rec = {"version": cfg.version(), "accepted": bool(ok), **decision}
        decisions.append(rec)
        if ok:
            accepted.append((effective_objective(summary, cfg), cfg, summary))
    if not accepted:
        return None, None, decisions
    accepted.sort(key=lambda x: x[0], reverse=True)
    return accepted[0][1], accepted[0][2], decisions


def write_best_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    if not rows:
        return
    fields = [
        "round_index", "model_version", "model_score", "model_max_hits",
        "model_mean_hits", "model_ge3", "model_ge4", "signal_top7_hits",
        "signal_actual_mass", "signal_mean_log_prob", "signal_brier",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def render_report(record: Dict[str, object]) -> str:
    lines = [
        "# Full-History Feedback Optimizer — Signal / Portfolio Separated",
        "",
        f"- generation: **{record.get('generation')}**",
        f"- incumbent: **{record.get('incumbent_version')}**",
        f"- trials: **{record.get('trial_count', 0)}**",
        f"- accepted: **{record.get('accepted_version') or 'なし'}**",
        f"- incumbent portfolio objective: **{float(record.get('incumbent_objective',0.0)):+.4f}**",
        f"- incumbent signal objective: **{float(record.get('incumbent_signal_objective',0.0)):+.4f}**",
        f"- eta探索範囲: **{ETA_BOUNDS[0]}〜{ETA_BOUNDS[1]}**",
        f"- overlap_penalty探索範囲: **{OVERLAP_BOUNDS[0]}〜{OVERLAP_BOUNDS[1]}**",
        "- Production昇格証拠: **使用しない**",
        "",
    ]
    for d in record.get("decisions", []) or []:
        lines.append(
            f"- {d.get('version')}: portfolio gain **{float(d.get('objective_gain',0.0)):+.4f}** / "
            f"signal **{float(d.get('candidate_signal_objective',0.0)):+.4f}** / "
            f"accepted **{'YES' if d.get('accepted') else 'NO'}**"
        )
    lines += [
        "",
        "> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。",
        "> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。",
        "",
    ]
    return "\n".join(lines)


def optimize_once(csv_path: Path = Path("loto7.csv"),
                  out_dir: Path = Path("loto7_agent_output"),
                  research_state_path: Path = Path("loto7_agent_output/v4_research_state.json"),
                  evaluation_path: Path = Path("loto7_agent_output/v4_research_evaluation.json"),
                  feedback_state_path: Path = Path("loto7_agent_output/research_feedback_state.json"),
                  min_train: int = 100,
                  pool_size: int = 350,
                  trials: int = DEFAULT_TRIALS) -> Dict[str, object]:
    if not csv_path.exists() or not feedback_state_path.exists() or not evaluation_path.exists():
        return {"optimized": False, "reason": "required state not ready"}

    feedback_state = load_json(feedback_state_path, {})
    research_state = load_json(research_state_path, {})
    evaluation = load_json(evaluation_path, {})
    incumbent = rf.cfg_from_obj(feedback_state.get("accepted_parent_config"))
    incumbent_summary = feedback_state.get("accepted_parent_summary")
    if incumbent is None or not isinstance(incumbent_summary, dict):
        return {"optimized": False, "reason": "accepted parent summary not ready"}

    data_sha = fingerprint_file(csv_path)
    if str(feedback_state.get("data_sha256", "")) != data_sha:
        return {"optimized": False, "reason": "new data must be refreshed by research_feedback first"}

    generation = int(evaluation.get("generation", research_state.get("generation", 0)))
    if int(feedback_state.get("optimizer_last_generation", -1)) >= generation:
        return {"optimized": False, "reason": "generation already optimized"}

    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    cache_path = out_dir / "feedback_optimizer_cache.json"
    cache = load_json(cache_path, {"optimizer_version": OPTIMIZER_VERSION, "entries": {}})

    # Upgrade an incumbent created before signal separation exactly once for this data/config.
    if _signal(incumbent_summary, "full") is None:
        incumbent_summary, _, _ = evaluate_candidate(
            x, incumbent, data_sha, incumbent_summary, cache, min_train, pool_size
        )
        feedback_state["accepted_parent_summary"] = incumbent_summary

    configs = expanded_candidates(incumbent, data_sha, generation, count=trials)
    evaluated: List[Tuple[v2.ModelConfig, Dict[str, object]]] = []
    rows_by_version: Dict[str, List[Dict[str, object]]] = {}
    cache_hits = 0
    for cfg in configs:
        summary, rows, hit = evaluate_candidate(
            x, cfg, data_sha, incumbent_summary, cache, min_train, pool_size
        )
        evaluated.append((cfg, summary))
        rows_by_version[cfg.version()] = rows
        cache_hits += int(hit)

    selected, selected_summary, decisions = choose_best(incumbent_summary, evaluated, incumbent)
    accepted = selected is not None and selected_summary is not None
    accepted_cfg = selected if accepted else incumbent
    accepted_summary = selected_summary if accepted else incumbent_summary

    feedback_state["optimizer_last_generation"] = generation
    feedback_state["optimizer_trials_total"] = int(feedback_state.get("optimizer_trials_total", 0)) + len(configs)
    feedback_state["optimizer_accept_count"] = int(feedback_state.get("optimizer_accept_count", 0)) + int(accepted)
    feedback_state["accepted_parent_summary"] = accepted_summary
    if accepted:
        feedback_state["accepted_parent_version"] = accepted_cfg.version()
        feedback_state["accepted_parent_config"] = asdict(accepted_cfg)

    research_state["research_parent_config"] = asdict(accepted_cfg)
    research_state["research_winner"] = accepted_cfg.version()
    research_state["feedback_optimizer_last"] = {
        "generation": generation,
        "accepted": bool(accepted),
        "accepted_version": accepted_cfg.version(),
        "trials": len(configs),
        "signal_gated": True,
    }

    record: Dict[str, object] = {
        "optimizer_version": OPTIMIZER_VERSION,
        "generation": generation,
        "data_sha256": data_sha,
        "incumbent_version": incumbent.version(),
        "trial_count": len(configs),
        "cache_hits": cache_hits,
        "accepted": bool(accepted),
        "accepted_version": accepted_cfg.version() if accepted else None,
        "accepted_config": asdict(accepted_cfg) if accepted else None,
        "incumbent_objective": float(incumbent_summary.get("feedback_objective", 0.0)),
        "incumbent_signal_objective": float(incumbent_summary.get("signal_objective", 0.0)),
        "accepted_objective": float(accepted_summary.get("feedback_objective", 0.0)),
        "accepted_signal_objective": float(accepted_summary.get("signal_objective", 0.0)),
        "incumbent_boundary_penalty": boundary_penalty(incumbent),
        "accepted_boundary_penalty": boundary_penalty(accepted_cfg),
        "decisions": decisions,
        "independent_evidence": False,
        "production_promotion_eligible": False,
    }
    feedback_state["optimizer_last_record"] = record
    write_json(feedback_state_path, feedback_state)
    write_json(research_state_path, research_state)
    write_json(cache_path, cache)
    write_json(out_dir / "feedback_optimizer_summary.json", record)
    (out_dir / "feedback_optimizer_report.md").write_text(render_report(record), encoding="utf-8")
    append_jsonl(out_dir / "feedback_optimizer_history.jsonl", record)
    if accepted:
        write_best_rows(out_dir / "feedback_optimizer_best_rounds.csv", rows_by_version.get(accepted_cfg.version(), []))
        events_path = out_dir / "run_events.json"
        events = load_json(events_path, {})
        events["feedback_optimizer_accepted"] = True
        events["feedback_optimizer_parent"] = accepted_cfg.version()
        events["force_checkpoint"] = True
        write_json(events_path, events)

    print(
        f"[FEEDBACK-OPT] generation={generation} trials={len(configs)} "
        f"accepted={accepted} parent={accepted_cfg.version()} "
        f"portfolio={float(accepted_summary.get('feedback_objective',0.0)):+.6f} "
        f"signal={float(accepted_summary.get('signal_objective',0.0)):+.6f}"
    )
    return record


def main() -> int:
    optimize_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
