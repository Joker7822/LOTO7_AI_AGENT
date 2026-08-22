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

OPTIMIZER_VERSION = "feedback-optimizer-v1"
ETA_BOUNDS = (0.10, 6.0)
DECAY_BOUNDS = (0.975, 0.9998)
EXPERT_MIX_BOUNDS = (0.02, 0.50)
FINAL_MIX_BOUNDS = (0.02, 0.55)
OVERLAP_BOUNDS = (0.25, 2.00)
DEFAULT_TRIALS = 2


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
    """Generate deterministic full-history candidates with wider bounds than v4 short-window search.

    The current accepted parent has repeatedly sat at eta=0.8, the old lower bound. The
    feedback optimizer therefore explicitly explores eta below 0.8 and a wider overlap range.
    """
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
            # Bias the global trial toward stronger ticket diversification.
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


def simulate_model_only(x: np.ndarray, config: v2.ModelConfig, min_train: int,
                        pool_size: int) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, object]]]:
    """Replay a candidate without recomputing the model-independent random reference."""
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    seed_offset = int(hashlib.sha256(config.version().encode()).hexdigest()[:8], 16) % 100000
    numeric: List[Dict[str, float]] = []
    csv_rows: List[Dict[str, object]] = []

    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, config)
        tickets = make_ticket_portfolio(
            q,
            n_tickets=5,
            seed=6_000_000 + t * 1000 + seed_offset,
            pool_size=pool_size,
            overlap_penalty=config.overlap_penalty,
        )
        actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
        m = v2._portfolio_metrics(tickets, actual_set)
        score = float(v3.row_score(m))
        numeric.append({
            "max_hits": float(m["max_hits"]),
            "mean_hits": float(m["mean_hits"]),
            "ge3": float(m["ge3"]),
            "ge4": float(m["ge4"]),
            "score": score,
        })
        csv_rows.append({
            "round_index": t + 1,
            "model_version": config.version(),
            "model_score": f"{score:.6f}",
            "model_max_hits": f"{m['max_hits']:.0f}",
            "model_mean_hits": f"{m['mean_hits']:.6f}",
            "model_ge3": f"{m['ge3']:.0f}",
            "model_ge4": f"{m['ge4']:.0f}",
        })
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, config)

    windows = {"full": aggregate_model(numeric)}
    for n in (120, 60, 30):
        windows[str(n)] = aggregate_model(numeric[-min(n, len(numeric)):])
    return windows, csv_rows


def summary_with_reference(config: v2.ModelConfig, model_windows: Dict[str, Dict[str, float]],
                           reference_summary: Dict[str, object], data_sha: str,
                           min_train: int, pool_size: int) -> Dict[str, object]:
    ref_windows = reference_summary.get("windows") or {}
    windows: Dict[str, Dict[str, float]] = {}
    for name in ("full", "120", "60", "30"):
        m = model_windows[name]
        ref = ref_windows.get(name) or {}
        random_score = float(ref.get("random_score", 0.0))
        random_max = float(ref.get("random_max_hits", 0.0))
        windows[name] = {
            **m,
            "random_max_hits": random_max,
            "random_mean_hits": float(ref.get("random_mean_hits", 0.0)),
            "random_ge3": float(ref.get("random_ge3", 0.0)),
            "random_ge4": float(ref.get("random_ge4", 0.0)),
            "random_score": random_score,
            "score_delta_vs_random": float(m["score"] - random_score),
            "max_hits_delta_vs_random": float(m["max_hits"] - random_max),
        }
    objective = float(sum(
        rf.WINDOW_WEIGHTS[name] * float(windows[name]["score_delta_vs_random"])
        for name in rf.WINDOW_WEIGHTS
    ))
    return {
        "report_version": rf.REPORT_VERSION,
        "optimizer_version": OPTIMIZER_VERSION,
        "evaluation_type": "retrospective_full_history_feedback_optimizer",
        "model_version": config.version(),
        "config": asdict(config),
        "evaluated_rounds": int(reference_summary.get("evaluated_rounds", 0)),
        "min_train": int(min_train),
        "pool_size": int(pool_size),
        "windows": windows,
        "feedback_objective": objective,
        "independent_evidence": False,
        "promotion_eligible": False,
        "data_sha256": data_sha,
    }


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
    if isinstance(old, dict):
        return old, [], True
    model_windows, rows = simulate_model_only(x, config, min_train, pool_size)
    summary = summary_with_reference(config, model_windows, reference_summary, data_sha, min_train, pool_size)
    entries[key] = summary
    cache["optimizer_version"] = OPTIMIZER_VERSION
    return summary, rows, False


def choose_best(incumbent_summary: Dict[str, object], trials: Sequence[Tuple[v2.ModelConfig, Dict[str, object]]]) -> Tuple[Optional[v2.ModelConfig], Optional[Dict[str, object]], List[Dict[str, object]]]:
    decisions: List[Dict[str, object]] = []
    accepted: List[Tuple[float, v2.ModelConfig, Dict[str, object]]] = []
    for cfg, summary in trials:
        ok, decision = rf.decide_accept(summary, incumbent_summary)
        rec = {"version": cfg.version(), "accepted": bool(ok), **decision}
        decisions.append(rec)
        if ok:
            accepted.append((float(summary.get("feedback_objective", -1e9)), cfg, summary))
    if not accepted:
        return None, None, decisions
    accepted.sort(key=lambda x: x[0], reverse=True)
    return accepted[0][1], accepted[0][2], decisions


def write_best_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    if not rows:
        return
    fields = [
        "round_index", "model_version", "model_score", "model_max_hits",
        "model_mean_hits", "model_ge3", "model_ge4",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def render_report(record: Dict[str, object]) -> str:
    lines = [
        "# Full-History Feedback Optimizer",
        "",
        f"- generation: **{record.get('generation')}**",
        f"- incumbent: **{record.get('incumbent_version')}**",
        f"- trials: **{record.get('trial_count', 0)}**",
        f"- accepted: **{record.get('accepted_version') or 'なし'}**",
        f"- eta探索範囲: **{ETA_BOUNDS[0]}〜{ETA_BOUNDS[1]}**",
        f"- overlap_penalty探索範囲: **{OVERLAP_BOUNDS[0]}〜{OVERLAP_BOUNDS[1]}**",
        "- Production昇格証拠: **使用しない**",
        "",
    ]
    for d in record.get("decisions", []) or []:
        lines.append(
            f"- {d.get('version')}: objective gain **{float(d.get('objective_gain',0.0)):+.4f}** / "
            f"accepted **{'YES' if d.get('accepted') else 'NO'}**"
        )
    lines += [
        "",
        "> このoptimizerは過去データへの研究最適化です。精度の独立検証は未来OOSのみです。",
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
    configs = expanded_candidates(incumbent, data_sha, generation, count=trials)
    cache_path = out_dir / "feedback_optimizer_cache.json"
    cache = load_json(cache_path, {"optimizer_version": OPTIMIZER_VERSION, "entries": {}})

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

    selected, selected_summary, decisions = choose_best(incumbent_summary, evaluated)
    accepted = selected is not None and selected_summary is not None
    accepted_cfg = selected if accepted else incumbent
    accepted_summary = selected_summary if accepted else incumbent_summary

    feedback_state["optimizer_last_generation"] = generation
    feedback_state["optimizer_trials_total"] = int(feedback_state.get("optimizer_trials_total", 0)) + len(configs)
    feedback_state["optimizer_accept_count"] = int(feedback_state.get("optimizer_accept_count", 0)) + int(accepted)
    if accepted:
        feedback_state["accepted_parent_version"] = accepted_cfg.version()
        feedback_state["accepted_parent_config"] = asdict(accepted_cfg)
        feedback_state["accepted_parent_summary"] = accepted_summary

    research_state["research_parent_config"] = asdict(accepted_cfg)
    research_state["research_winner"] = accepted_cfg.version()
    research_state["feedback_optimizer_last"] = {
        "generation": generation,
        "accepted": bool(accepted),
        "accepted_version": accepted_cfg.version(),
        "trials": len(configs),
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
        "accepted_objective": float(accepted_summary.get("feedback_objective", 0.0)),
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
        f"objective={float(accepted_summary.get('feedback_objective',0.0)):+.6f}"
    )
    return record


def main() -> int:
    optimize_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
