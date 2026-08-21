#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import loto7_v2_runner as v2
from loto7_evolving_agent import (
    N_NUMBERS,
    RANDOM_HIT_MEAN,
    expert_probabilities,
    fingerprint_file,
    make_history,
    make_ticket_portfolio,
    read_csv_flexible,
    walk_forward_evolve,
)

JST = dt.timezone(dt.timedelta(hours=9))


def now_jst() -> dt.datetime:
    return dt.datetime.now(JST)


def clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, float(v)))


def load_json(path: Path, default: Dict[str, object]) -> Dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def make_mutants(champion: v2.ModelConfig, data_sha: str, generation: int, count: int = 6) -> List[v2.ModelConfig]:
    """Create deterministic bounded challengers around the current champion."""
    seed_hex = hashlib.sha256(f"{data_sha}|{generation}|{champion.version()}".encode()).hexdigest()[:16]
    rng = np.random.default_rng(int(seed_hex, 16))
    out: List[v2.ModelConfig] = []
    seen = {champion.version()}
    attempts = 0
    while len(out) < count and attempts < count * 20:
        attempts += 1
        eta = clamp(champion.eta * math.exp(float(rng.normal(0, 0.18))), 0.8, 6.0)
        decay = clamp(champion.decay + float(rng.normal(0, 0.0025)), 0.982, 0.9995)
        eum = clamp(champion.expert_uniform_mix + float(rng.normal(0, 0.035)), 0.08, 0.35)
        fum = clamp(champion.final_uniform_mix + float(rng.normal(0, 0.045)), 0.10, 0.42)
        overlap = clamp(champion.overlap_penalty + float(rng.normal(0, 0.09)), 0.35, 1.10)
        cfg = v2.ModelConfig(
            name=f"evo-g{generation:05d}-c{len(out)+1:02d}",
            eta=round(eta, 6),
            decay=round(decay, 6),
            expert_uniform_mix=round(eum, 6),
            final_uniform_mix=round(fum, 6),
            overlap_penalty=round(overlap, 6),
        )
        if cfg.version() not in seen:
            seen.add(cfg.version())
            out.append(cfg)
    return out


def row_score(m: Dict[str, float]) -> float:
    return float(m["max_hits"] + 0.35 * m["ge3"] + 0.75 * m["ge4"] + 0.10 * m["mean_hits"])


def aggregate(rows: List[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {"max_hits":0.0,"mean_hits":0.0,"ge3_rate":0.0,"ge4_rate":0.0,"score":0.0}
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in rows])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in rows])),
        "ge3_rate": float(np.mean([r["ge3"] for r in rows])),
        "ge4_rate": float(np.mean([r["ge4"] for r in rows])),
        "score": float(np.mean([row_score(r) for r in rows])),
    }


def evaluate_config(x: np.ndarray, config: v2.ModelConfig, min_train: int = 100,
                    max_window: int = 120, pool_size: int = 650) -> Dict[str, object]:
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    eval_start = max(min_train, len(x) - max_window)
    model_rows: List[Dict[str, float]] = []
    random_rows: List[Dict[str, float]] = []

    for t in range(min_train, len(x)):
        if t >= eval_start:
            q = v2._score_distribution(x[:t], keys, logw, config)
            portfolio = make_ticket_portfolio(
                q, n_tickets=5, seed=100000 + t, pool_size=pool_size,
                overlap_penalty=config.overlap_penalty
            )
            actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
            model_rows.append(v2._portfolio_metrics(portfolio, actual_set))
            reps = []
            for rep in range(8):
                rng = np.random.default_rng(700000 + t * 31 + rep)
                reps.append(v2._portfolio_metrics(v2._random_portfolio(rng), actual_set))
            random_rows.append({
                k: float(np.mean([r[k] for r in reps]))
                for k in ("max_hits","mean_hits","ge3","ge4")
            })
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, config)

    windows: Dict[str, object] = {}
    for window in (30, 60, 120):
        n = min(window, len(model_rows))
        m = aggregate(model_rows[-n:])
        r = aggregate(random_rows[-n:])
        windows[str(window)] = {
            "draws": n, "model": m, "random": r,
            "score_delta_vs_random": m["score"] - r["score"],
            "max_hits_delta_vs_random": m["max_hits"] - r["max_hits"],
        }

    final_weights = v2._weights_from_log(logw, config.expert_uniform_mix)
    q = v2._score_distribution(x, keys, logw, config)
    return {
        "config": asdict(config),
        "version": config.version(),
        "windows": windows,
        "expert_keys": keys,
        "final_weights": {k: float(final_weights[i]) for i, k in enumerate(keys)},
        "final_q": q,
        "daily_scores": [row_score(r) for r in model_rows],
    }


def paired_signflip_p(champion_scores: List[float], challenger_scores: List[float],
                      seed: int, reps: int = 4096) -> float:
    """One-sided paired randomization p-value for challenger mean > champion mean."""
    a = np.asarray(champion_scores, dtype=float)
    b = np.asarray(challenger_scores, dtype=float)
    n = min(len(a), len(b))
    if n == 0:
        return 1.0
    d = b[-n:] - a[-n:]
    observed = float(d.mean())
    if observed <= 0:
        return 1.0
    rng = np.random.default_rng(seed)
    exceed = 0
    left = reps
    while left > 0:
        m = min(left, 512)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(m, n))
        means = (signs * d).mean(axis=1)
        exceed += int(np.sum(means >= observed))
        left -= m
    return (exceed + 1.0) / (reps + 1.0)


def alpha_per_candidate(data_day_index: int, candidate_count: int, family_alpha: float = 0.05) -> float:
    # Sequential alpha spending: sum 1/(d(d+1)) = 1, Bonferroni within each daily family.
    d = max(1, int(data_day_index))
    m = max(1, int(candidate_count))
    return family_alpha / (d * (d + 1) * m)


def candidate_decision(champ: Dict[str, object], cand: Dict[str, object],
                       alpha: float, seed: int) -> Tuple[bool, Dict[str, object]]:
    deltas: Dict[str, float] = {}
    max_deltas: Dict[str, float] = {}
    for w in ("30","60","120"):
        deltas[w] = float(cand["windows"][w]["model"]["score"]) - float(champ["windows"][w]["model"]["score"])
        max_deltas[w] = float(cand["windows"][w]["model"]["max_hits"]) - float(champ["windows"][w]["model"]["max_hits"])
    p120 = paired_signflip_p(champ["daily_scores"][-120:], cand["daily_scores"][-120:], seed=seed)
    random_delta120 = float(cand["windows"]["120"]["score_delta_vs_random"])
    checks = {
        "window30_nonnegative": deltas["30"] >= 0.0,
        "window60_improves": deltas["60"] > 0.01,
        "window120_improves": deltas["120"] > 0.01,
        "max_hits60_not_regressed": max_deltas["60"] >= -0.01,
        "max_hits120_not_regressed": max_deltas["120"] >= -0.01,
        "beats_random120": random_delta120 > 0.0,
        "paired_p120_pass": p120 <= alpha,
    }
    eligible = all(checks.values())
    return eligible, {
        "eligible": eligible,
        "score_delta": deltas,
        "max_hits_delta": max_deltas,
        "paired_p120": p120,
        "alpha_threshold": alpha,
        "score_delta_vs_random120": random_delta120,
        "checks": checks,
    }


def append_hash_chain(path: Path, record: Dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    prev_hash = "GENESIS"
    if path.exists():
        try:
            lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            if lines:
                prev_hash = str(json.loads(lines[-1]).get("record_hash", "GENESIS"))
        except Exception:
            prev_hash = "UNREADABLE_PREVIOUS"
    payload = dict(record)
    payload["prev_hash"] = prev_hash
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["record_hash"] = record_hash
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return record_hash


def research_portfolio(eval_obj: Dict[str, object], clean, generation: int) -> Tuple[int, List[Tuple[int, ...]]]:
    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    digits = "".join(ch for ch in latest_round_text if ch.isdigit())
    target_round = int(digits) + 1 if digits else len(clean) + 1
    cfg = v2.ModelConfig(**eval_obj["config"])
    q = np.asarray(eval_obj["final_q"], dtype=float)
    tickets = make_ticket_portfolio(
        q, 5, seed=900000 + target_round * 1000 + generation,
        pool_size=2500, overlap_penalty=cfg.overlap_penalty
    )
    return target_round, tickets


def write_research_outputs(out_dir: Path, eval_obj: Dict[str, object], clean, generation: int,
                           created_at: str) -> None:
    target, tickets = research_portfolio(eval_obj, clean, generation)
    rows = ["ticket,numbers,sum,odd_count"]
    lines = [
        "LOTO7 日次進化・研究予測",
        "=" * 60,
        f"対象回: 第{target}回",
        f"研究世代: {generation}",
        f"モデル: {eval_obj['version']}",
        f"生成日時(JST): {created_at}",
        "",
    ]
    for i, t in enumerate(tickets, 1):
        ns = " ".join(f"{n:02d}" for n in t)
        rows.append(f'{i},"{ns}",{sum(t)},{sum(n % 2 for n in t)}')
        lines.append(f"{i}. {ns}")
    lines += ["", "※ 研究予測は日次で更新されます。本番のappend-only予測履歴は変更しません。"]
    (out_dir / "research_candidate_tickets.csv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    (out_dir / "latest_research_prediction.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="LOTO7 AI Agent v3 continuous daily evolution")
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--evolution-state", type=Path, default=Path("loto7_agent_output/evolution_state.json"))
    ap.add_argument("--evolution-history", type=Path, default=Path("loto7_agent_output/evolution_history.jsonl"))
    ap.add_argument("--tickets", type=int, default=5)
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--mutants", type=int, default=6)
    ap.add_argument("--portfolio-backtest-pool", type=int, default=650)
    args = ap.parse_args()
    if args.tickets != 5:
        raise SystemExit("v3 production runner requires exactly --tickets 5")

    created_at = now_jst().isoformat(timespec="seconds")
    df = read_csv_flexible(args.csv)
    x, clean = make_history(df)
    data_sha = fingerprint_file(args.csv)
    current_champion = v2.load_champion(args.champion_file)
    state = load_json(args.evolution_state, {
        "generation": 0, "current_data_sha": "", "data_day_index": 0,
        "last_promotion_data_sha": "", "total_evaluations": 0, "total_promotions": 0,
    })
    generation = int(state.get("generation", 0)) + 1
    same_data = state.get("current_data_sha") == data_sha
    data_day_index = int(state.get("data_day_index", 0)) + 1 if same_data else 1

    mutants = make_mutants(current_champion, data_sha, generation, count=args.mutants)
    configs = [current_champion] + mutants
    evaluations = [
        evaluate_config(x, cfg, min_train=args.min_train, pool_size=args.portfolio_backtest_pool)
        for cfg in configs
    ]
    champ_eval = evaluations[0]
    alpha = alpha_per_candidate(data_day_index, len(mutants))
    decisions = []
    eligible = []
    for idx, ev in enumerate(evaluations[1:], 1):
        ok, detail = candidate_decision(
            champ_eval, ev, alpha,
            seed=int(hashlib.sha256(f"{data_sha}|{generation}|{idx}".encode()).hexdigest()[:16], 16)
        )
        detail["challenger"] = ev["version"]
        decisions.append(detail)
        if ok:
            eligible.append(ev)

    promotion_locked = str(state.get("last_promotion_data_sha", "")) == data_sha
    promoted = False
    selected_eval = champ_eval
    if eligible and not promotion_locked:
        selected_eval = max(
            eligible,
            key=lambda ev: (
                float(ev["windows"]["120"]["model"]["score"]) +
                0.5 * float(ev["windows"]["60"]["model"]["score"]) +
                0.2 * float(ev["windows"]["30"]["model"]["score"])
            ),
        )
        promoted = True

    selected = v2.ModelConfig(**selected_eval["config"])
    research_eval = max(
        evaluations,
        key=lambda ev: (
            float(ev["windows"]["120"]["model"]["score"]) +
            0.5 * float(ev["windows"]["60"]["model"]["score"]) +
            0.2 * float(ev["windows"]["30"]["model"]["score"])
        ),
    )

    outputs = v2.build_current_outputs(x, clean, selected, args.out_dir, args.tickets, args.min_train)
    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    latest_round = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else None
    git_sha = os.environ.get("GITHUB_SHA", "local")
    model_version = selected.version()

    old_champion_meta = load_json(args.champion_file, {})
    champion_obj = {
        "model_version": model_version,
        "config": asdict(selected),
        "selected_at_data_round": latest_round if promoted or not old_champion_meta else old_champion_meta.get("selected_at_data_round"),
        "selected_at_data_date": latest_date if promoted or not old_champion_meta else old_champion_meta.get("selected_at_data_date"),
        "selected_at_generation": generation if promoted or not old_champion_meta else old_champion_meta.get("selected_at_generation", 0),
        "last_evaluated_data_sha256": data_sha,
        "data_sha256": data_sha,
        "git_sha": git_sha,
    }
    args.champion_file.parent.mkdir(parents=True, exist_ok=True)
    args.champion_file.write_text(json.dumps(champion_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "created_at_jst": created_at,
        "generation": generation,
        "data_sha256": data_sha,
        "data_day_index": data_day_index,
        "family_alpha": 0.05,
        "per_candidate_alpha": alpha,
        "champion_before": champ_eval["version"],
        "selected_version": selected_eval["version"],
        "research_winner": research_eval["version"],
        "promotion_locked_for_data_sha": promotion_locked,
        "promoted": promoted,
        "promotion_checks": decisions,
        "evaluations": [{k:v for k,v in ev.items() if k not in ("final_q","daily_scores")} for ev in evaluations],
    }
    (args.out_dir / "model_evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_research_outputs(args.out_dir, research_eval, clean, generation, created_at)

    bt = outputs["bt"]; ranking = outputs["ranking"]; q = outputs["q"]
    agent_state = {
        "agent_version": "v3-continuous-evolution",
        "model_version": model_version,
        "model_config": asdict(selected),
        "git_sha": git_sha,
        "data_sha256": data_sha,
        "rows": int(len(clean)),
        "latest_draw_date": latest_date,
        "latest_round": latest_round,
        "target_round": f"第{outputs['target_round']}回",
        "evolution_generation": generation,
        "research_winner": research_eval["version"],
        "promoted_today": promoted,
        "promotion_locked_for_data_sha": promotion_locked,
        "walk_forward_draws": bt.draws_tested,
        "mean_top7_hits": bt.mean_hits,
        "random_theoretical_mean_hits": RANDOM_HIT_MEAN,
        "z_vs_random": bt.z_vs_random,
        "approx_two_sided_p": bt.approx_two_sided_p,
        "signal_claim": "not_confirmed" if bt.approx_two_sided_p >= 0.05 else "requires_independent_validation",
        "expert_weights": {k: float(bt.final_weights[i]) for i,k in enumerate(bt.keys)},
        "top15": [
            {"number": int(n), "relative_score": float(q[n-1]),
             "score_index_vs_uniform": float(q[n-1] / (1/N_NUMBERS))}
            for n in ranking[:15]
        ],
        "seed": outputs["seed"],
        "portfolio_backtest": report,
    }
    (args.out_dir / "agent_state.json").write_text(json.dumps(agent_state, ensure_ascii=False, indent=2), encoding="utf-8")

    total_promotions = int(state.get("total_promotions", 0)) + int(promoted)
    new_state = {
        "agent_version": "v3-continuous-evolution",
        "generation": generation,
        "current_data_sha": data_sha,
        "data_day_index": data_day_index,
        "last_run_jst": created_at,
        "last_promotion_data_sha": data_sha if promoted else str(state.get("last_promotion_data_sha", "")),
        "champion_version": model_version,
        "research_winner": research_eval["version"],
        "total_evaluations": int(state.get("total_evaluations", 0)) + len(mutants),
        "total_promotions": total_promotions,
        "promotion_locked_for_data_sha": promotion_locked or promoted,
        "per_candidate_alpha": alpha,
    }
    args.evolution_state.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    history_record = {
        "created_at_jst": created_at,
        "generation": generation,
        "data_sha256": data_sha,
        "data_day_index": data_day_index,
        "champion_before": champ_eval["version"],
        "champion_after": model_version,
        "research_winner": research_eval["version"],
        "promoted": promoted,
        "promotion_locked_for_data_sha": promotion_locked,
        "per_candidate_alpha": alpha,
        "candidates_evaluated": len(mutants),
        "top_research_score120": float(research_eval["windows"]["120"]["model"]["score"]),
    }
    history_hash = append_hash_chain(args.evolution_history, history_record)
    new_state["last_history_hash"] = history_hash
    args.evolution_state.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[EVOLUTION] generation={generation} data_day={data_day_index} candidates={len(mutants)}")
    print(f"[MODEL] champion={model_version} promoted={promoted} locked={promotion_locked or promoted}")
    print(f"[RESEARCH] winner={research_eval['version']} alpha/candidate={alpha:.8f}")
    for w in ("30","60","120"):
        m = selected_eval["windows"][w]["model"]; r = selected_eval["windows"][w]["random"]
        print(f"[BACKTEST {w}] score={m['score']:.4f} random={r['score']:.4f} max_hits={m['max_hits']:.3f}")
    print("[PRODUCTION PREDICTIONS]")
    for i, t in enumerate(outputs["portfolio"], 1):
        print(f"{i}. {' '.join(f'{n:02d}' for n in t)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
