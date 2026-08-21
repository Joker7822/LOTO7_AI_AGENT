#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
from loto7_evolving_agent import (
    N_NUMBERS,
    RANDOM_HIT_MEAN,
    fingerprint_file,
    make_history,
    make_ticket_portfolio,
    read_csv_flexible,
)

JST = dt.timezone(dt.timedelta(hours=9))
AGENT_VERSION = "v4-oos-governance"
POOL_LIMIT = 16
SHADOW_SLOTS = 6
MIN_TRUSTED_OOS_DRAWS = 8
E_VALUE_THRESHOLD = 20.0
MIN_MEAN_SCORE_DELTA = 0.05
MIN_OOS_WIN_RATE = 0.55
MAX_PORTFOLIO_SCORE = 8.8
E_LAMBDAS = (0.10, 0.25, 0.50, 0.75)
OOS_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version",
    "candidate_score", "champion_score", "score_delta", "normalized_delta",
    "candidate_max_hits", "champion_max_hits", "trusted_for_promotion",
    "source_verification", "registry_base_data_sha", "frozen_at_jst",
]


def now_jst() -> str:
    return dt.datetime.now(JST).isoformat(timespec="seconds")


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


def append_csv(path: Path, rows: Iterable[Dict[str, object]], fields: Sequence[str]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        if not exists:
            w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def parse_round(value: object) -> Optional[int]:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else None


def cfg_from_obj(obj: object) -> Optional[v2.ModelConfig]:
    if not isinstance(obj, dict):
        return None
    try:
        return v2.ModelConfig(
            name=str(obj["name"]),
            eta=float(obj["eta"]),
            decay=float(obj["decay"]),
            expert_uniform_mix=float(obj["expert_uniform_mix"]),
            final_uniform_mix=float(obj["final_uniform_mix"]),
            overlap_penalty=float(obj["overlap_penalty"]),
        )
    except Exception:
        return None


def research_score(ev: Dict[str, object]) -> float:
    windows = ev["windows"]
    return (
        float(windows["120"]["model"]["score"])
        + 0.5 * float(windows["60"]["model"]["score"])
        + 0.2 * float(windows["30"]["model"]["score"])
    )


def global_restarts(data_sha: str, generation: int, count: int) -> List[v2.ModelConfig]:
    if count <= 0:
        return []
    seed = int(hashlib.sha256(f"v4-global|{data_sha}|{generation}".encode()).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    out: List[v2.ModelConfig] = []
    for i in range(count):
        eta = float(math.exp(rng.uniform(math.log(0.8), math.log(6.0))))
        out.append(v2.ModelConfig(
            name=f"global-g{generation:05d}-c{i+1:02d}",
            eta=round(eta, 6),
            decay=round(float(rng.uniform(0.982, 0.9995)), 6),
            expert_uniform_mix=round(float(rng.uniform(0.08, 0.35)), 6),
            final_uniform_mix=round(float(rng.uniform(0.10, 0.42)), 6),
            overlap_penalty=round(float(rng.uniform(0.35, 1.10)), 6),
        ))
    return out


def make_research_configs(champion: v2.ModelConfig, parent: v2.ModelConfig, data_sha: str,
                          generation: int, challengers: int) -> List[v2.ModelConfig]:
    global_count = min(2, max(1, challengers // 3)) if challengers > 1 else 0
    local_count = max(1, challengers - global_count)
    locals_ = v3.make_mutants(parent, data_sha, generation, count=local_count)
    globals_ = global_restarts(data_sha, generation, global_count)
    configs: List[v2.ModelConfig] = [champion]
    if parent.version() != champion.version():
        configs.append(parent)
    seen = {c.version() for c in configs}
    for cfg in locals_ + globals_:
        if cfg.version() not in seen:
            seen.add(cfg.version())
            configs.append(cfg)
    return configs


def source_info(path: Path, latest_round: int) -> Tuple[str, bool]:
    report = load_json(path, {})
    verification = str(report.get("verification", report.get("status", "unknown")))
    try:
        source_round = int((report.get("latest") or {}).get("round"))
    except Exception:
        source_round = -1
    trusted = (
        source_round == latest_round
        and report.get("status") == "ok"
        and verification == "verified_two_result_sources"
    )
    return verification, bool(trusted)


def score_tickets(tickets: Sequence[Sequence[int]], actual_set: set[int]) -> Dict[str, float]:
    normalized = [tuple(sorted(int(n) for n in t)) for t in tickets]
    m = v2._portfolio_metrics(normalized, actual_set)
    m["score"] = v3.row_score(m)
    return m


def e_key(candidate_version: str, champion_version: str) -> str:
    return f"{candidate_version}::vs::{champion_version}"


def update_evidence(state: Dict[str, object], candidate_version: str, champion_version: str,
                    config: Dict[str, object], delta: float, normalized_delta: float,
                    trusted: bool, round_no: int) -> Dict[str, object]:
    evidence = state.setdefault("evidence", {})
    assert isinstance(evidence, dict)
    key = e_key(candidate_version, champion_version)
    rec = evidence.get(key)
    if not isinstance(rec, dict):
        rec = {
            "candidate_version": candidate_version,
            "champion_version": champion_version,
            "config": config,
            "all_draws": 0,
            "trusted_draws": 0,
            "sum_delta": 0.0,
            "wins": 0,
            "e_components": {str(x): 1.0 for x in E_LAMBDAS},
            "e_value": 1.0,
            "last_round": None,
        }
    rec["all_draws"] = int(rec.get("all_draws", 0)) + 1
    rec["last_round"] = round_no
    if trusted:
        rec["trusted_draws"] = int(rec.get("trusted_draws", 0)) + 1
        rec["sum_delta"] = float(rec.get("sum_delta", 0.0)) + float(delta)
        if delta > 0:
            rec["wins"] = int(rec.get("wins", 0)) + 1
        comps = rec.get("e_components")
        if not isinstance(comps, dict):
            comps = {str(x): 1.0 for x in E_LAMBDAS}
        for lam in E_LAMBDAS:
            old = float(comps.get(str(lam), 1.0))
            factor = max(1e-12, 1.0 + lam * float(normalized_delta))
            comps[str(lam)] = old * factor
        rec["e_components"] = comps
        rec["e_value"] = float(np.mean([float(comps[str(x)]) for x in E_LAMBDAS]))
    evidence[key] = rec
    return rec


def grade_registry(registry: Dict[str, object], latest_round: int, draw_date: str,
                   actual_set: set[int], verification: str, trusted: bool,
                   oos_state: Dict[str, object], result_path: Path) -> bool:
    if int(registry.get("target_round", -1)) != latest_round:
        return False
    graded = oos_state.setdefault("graded_rounds", [])
    if latest_round in graded:
        return False
    champion_version = str(registry.get("champion_version", ""))
    champion_tickets = registry.get("champion_tickets") or []
    if not champion_version or not champion_tickets:
        return False
    champ_metrics = score_tickets(champion_tickets, actual_set)
    rows: List[Dict[str, object]] = []
    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        candidate_version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        cfg = item.get("config") or {}
        if not candidate_version or not tickets:
            continue
        cand_metrics = score_tickets(tickets, actual_set)
        delta = float(cand_metrics["score"] - champ_metrics["score"])
        normalized = max(-1.0, min(1.0, delta / MAX_PORTFOLIO_SCORE))
        update_evidence(oos_state, candidate_version, champion_version, cfg, delta,
                        normalized, trusted, latest_round)
        rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": candidate_version,
            "champion_version": champion_version,
            "candidate_score": f"{cand_metrics['score']:.6f}",
            "champion_score": f"{champ_metrics['score']:.6f}",
            "score_delta": f"{delta:.6f}",
            "normalized_delta": f"{normalized:.8f}",
            "candidate_max_hits": f"{cand_metrics['max_hits']:.0f}",
            "champion_max_hits": f"{champ_metrics['max_hits']:.0f}",
            "trusted_for_promotion": str(bool(trusted)).lower(),
            "source_verification": verification,
            "registry_base_data_sha": registry.get("base_data_sha", ""),
            "frozen_at_jst": registry.get("frozen_at_jst", ""),
        })
    append_csv(result_path, rows, OOS_FIELDS)
    graded.append(latest_round)
    oos_state["last_graded_round"] = latest_round
    return bool(rows)


def promotion_candidates(oos_state: Dict[str, object], champion_version: str) -> List[Tuple[float, Dict[str, object]]]:
    evidence = oos_state.get("evidence")
    if not isinstance(evidence, dict):
        return []
    eligible: List[Tuple[float, Dict[str, object]]] = []
    for rec in evidence.values():
        if not isinstance(rec, dict) or rec.get("champion_version") != champion_version:
            continue
        draws = int(rec.get("trusted_draws", 0))
        if draws < MIN_TRUSTED_OOS_DRAWS:
            continue
        mean_delta = float(rec.get("sum_delta", 0.0)) / max(1, draws)
        win_rate = float(rec.get("wins", 0)) / max(1, draws)
        e_value = float(rec.get("e_value", 1.0))
        if e_value >= E_VALUE_THRESHOLD and mean_delta >= MIN_MEAN_SCORE_DELTA and win_rate >= MIN_OOS_WIN_RATE:
            rank = math.log(max(e_value, 1.0)) + mean_delta + 0.25 * win_rate
            eligible.append((rank, rec))
    return sorted(eligible, key=lambda x: x[0], reverse=True)


def promote_if_eligible(champion: v2.ModelConfig, champion_file: Path,
                        oos_state: Dict[str, object], latest_round_text: str,
                        latest_date: str, data_sha: str, git_sha: str,
                        source_trusted: bool) -> Tuple[v2.ModelConfig, Optional[Dict[str, object]]]:
    if not source_trusted:
        return champion, None
    eligible = promotion_candidates(oos_state, champion.version())
    if not eligible:
        return champion, None
    rec = eligible[0][1]
    cfg = cfg_from_obj(rec.get("config"))
    if cfg is None or cfg.version() != rec.get("candidate_version"):
        return champion, None
    evidence = {
        "method": "v4_oos_eprocess",
        "trusted_oos_draws": int(rec.get("trusted_draws", 0)),
        "mean_score_delta": float(rec.get("sum_delta", 0.0)) / max(1, int(rec.get("trusted_draws", 0))),
        "win_rate": float(rec.get("wins", 0)) / max(1, int(rec.get("trusted_draws", 0))),
        "e_value": float(rec.get("e_value", 1.0)),
        "threshold": E_VALUE_THRESHOLD,
    }
    write_json(champion_file, {
        "model_version": cfg.version(),
        "config": asdict(cfg),
        "selected_at_data_round": latest_round_text,
        "selected_at_data_date": latest_date,
        "selected_at_generation": None,
        "selection_method": "future_oos_only",
        "promotion_evidence": evidence,
        "last_evaluated_data_sha256": data_sha,
        "data_sha256": data_sha,
        "git_sha": git_sha,
    })
    return cfg, {"from": champion.version(), "to": cfg.version(), **evidence}


def update_candidate_pool(pool_path: Path, evaluations: Sequence[Dict[str, object]],
                          champion_version: str, generation: int, data_sha: str,
                          protected_versions: Sequence[str]) -> Dict[str, object]:
    pool = load_json(pool_path, {"agent_version": AGENT_VERSION, "candidates": []})
    existing = {
        str(x.get("version")): x
        for x in (pool.get("candidates") or [])
        if isinstance(x, dict) and x.get("version")
    }
    for ev in evaluations:
        version = str(ev["version"])
        if version == champion_version:
            continue
        score = research_score(ev)
        old = existing.get(version, {})
        existing[version] = {
            "version": version,
            "config": ev["config"],
            "best_research_score": max(float(old.get("best_research_score", -1e9)), score),
            "latest_research_score": score,
            "first_seen_generation": int(old.get("first_seen_generation", generation)),
            "last_seen_generation": generation,
            "last_data_sha": data_sha,
        }
    protected = set(protected_versions)
    ranked = sorted(existing.values(), key=lambda r: float(r.get("best_research_score", -1e9)), reverse=True)
    kept: List[Dict[str, object]] = []
    for rec in ranked:
        if len(kept) < POOL_LIMIT or rec.get("version") in protected:
            kept.append(rec)
    pool = {
        "agent_version": AGENT_VERSION,
        "updated_at_jst": now_jst(),
        "generation": generation,
        "data_sha256": data_sha,
        "limit": POOL_LIMIT,
        "candidates": kept,
    }
    write_json(pool_path, pool)
    return pool


def shadow_survivors(previous_registry: Dict[str, object], oos_state: Dict[str, object],
                     champion_version: str) -> List[Dict[str, object]]:
    items: List[Tuple[Tuple[float, float, float], Dict[str, object]]] = []
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    for item in previous_registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        cfg = item.get("config")
        if not version or not isinstance(cfg, dict):
            continue
        rec = evidence.get(e_key(version, champion_version), {}) if isinstance(evidence, dict) else {}
        if not isinstance(rec, dict):
            rec = {}
        draws = int(rec.get("trusted_draws", 0))
        mean_delta = float(rec.get("sum_delta", 0.0)) / max(1, draws) if draws else 0.0
        e_value = float(rec.get("e_value", 1.0))
        if draws >= 12 and mean_delta < 0:
            continue
        items.append(((e_value, mean_delta, -float(draws)), {"version": version, "config": cfg}))
    items.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in items[:3]]


def select_shadow_configs(pool: Dict[str, object], previous_registry: Dict[str, object],
                          oos_state: Dict[str, object], champion_version: str) -> List[v2.ModelConfig]:
    chosen: List[v2.ModelConfig] = []
    seen = {champion_version}
    for item in shadow_survivors(previous_registry, oos_state, champion_version):
        cfg = cfg_from_obj(item.get("config"))
        if cfg is not None and cfg.version() not in seen:
            chosen.append(cfg)
            seen.add(cfg.version())
    for rec in pool.get("candidates", []) or []:
        if len(chosen) >= SHADOW_SLOTS:
            break
        if not isinstance(rec, dict):
            continue
        cfg = cfg_from_obj(rec.get("config"))
        if cfg is not None and cfg.version() not in seen:
            chosen.append(cfg)
            seen.add(cfg.version())
    return chosen[:SHADOW_SLOTS]


def deterministic_tickets(ev: Dict[str, object], target_round: int, champion: bool = False) -> List[List[int]]:
    cfg = v2.ModelConfig(**ev["config"])
    q = np.asarray(ev["final_q"], dtype=float)
    if champion:
        seed = target_round
    else:
        h = int(hashlib.sha256(str(ev["version"]).encode()).hexdigest()[:8], 16)
        seed = target_round * 100000 + (h % 100000)
    tickets = make_ticket_portfolio(q, 5, seed=seed, pool_size=2500, overlap_penalty=cfg.overlap_penalty)
    return [[int(n) for n in t] for t in tickets]


def freeze_registry(path: Path, target_round: int, base_data_sha: str,
                    champion: v2.ModelConfig, champion_eval: Dict[str, object],
                    shadow_configs: Sequence[v2.ModelConfig],
                    eval_by_version: Dict[str, Dict[str, object]], x: np.ndarray,
                    min_train: int, pool_size: int, source_verification: str) -> Dict[str, object]:
    candidates: List[Dict[str, object]] = []
    for cfg in shadow_configs:
        ev = eval_by_version.get(cfg.version())
        if ev is None:
            ev = v3.evaluate_config(x, cfg, min_train=min_train, pool_size=pool_size)
            eval_by_version[cfg.version()] = ev
        candidates.append({
            "version": cfg.version(),
            "config": asdict(cfg),
            "research_score": research_score(ev),
            "tickets": deterministic_tickets(ev, target_round, champion=False),
        })
    registry = {
        "agent_version": AGENT_VERSION,
        "target_round": target_round,
        "base_data_sha": base_data_sha,
        "frozen_at_jst": now_jst(),
        "source_verification_at_freeze": source_verification,
        "champion_version": champion.version(),
        "champion_config": asdict(champion),
        "champion_tickets": deterministic_tickets(champion_eval, target_round, champion=True),
        "candidates": candidates,
    }
    write_json(path, registry)
    return registry


def write_research_outputs(out_dir: Path, ev: Dict[str, object], target_round: int,
                           generation: int) -> None:
    cfg = v2.ModelConfig(**ev["config"])
    q = np.asarray(ev["final_q"], dtype=float)
    seed = 4_000_000 + target_round * 1000 + generation
    tickets = make_ticket_portfolio(q, 5, seed=seed, pool_size=2500, overlap_penalty=cfg.overlap_penalty)
    csv_rows = ["ticket,numbers,sum,odd_count"]
    text = [
        "LOTO7 v4 継続研究予測",
        "=" * 60,
        f"対象回: 第{target_round}回",
        f"研究世代: {generation}",
        f"研究モデル: {ev['version']}",
        f"生成日時(JST): {now_jst()}",
        "",
    ]
    for i, t in enumerate(tickets, 1):
        ns = " ".join(f"{n:02d}" for n in t)
        csv_rows.append(f'{i},"{ns}",{sum(t)},{sum(n % 2 for n in t)}')
        text.append(f"{i}. {ns}")
    text += ["", "※研究予測は連続更新されます。Production Championの昇格には使用せず、昇格は凍結済みshadowの未来OOS結果だけで判定します。"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "research_candidate_tickets.csv").write_text("\n".join(csv_rows) + "\n", encoding="utf-8-sig")
    (out_dir / "latest_research_prediction.txt").write_text("\n".join(text) + "\n", encoding="utf-8")


def ensure_production_outputs(x: np.ndarray, clean, champion: v2.ModelConfig,
                              out_dir: Path, min_train: int, data_sha: str,
                              git_sha: str, generation: int, force: bool,
                              promotion: Optional[Dict[str, object]]) -> Dict[str, object]:
    state_path = out_dir / "agent_state.json"
    old = load_json(state_path, {})
    cache_ok = (
        not force
        and old.get("model_version") == champion.version()
        and old.get("data_sha256") == data_sha
        and (out_dir / "candidate_tickets.csv").exists()
    )
    if cache_ok:
        old["agent_version"] = AGENT_VERSION
        old["research_generation"] = generation
        old["production_promotion_method"] = "future_oos_only"
        old["promotion_this_run"] = promotion
        write_json(state_path, old)
        return {"cached": True, "state": old}

    outputs = v2.build_current_outputs(x, clean, champion, out_dir, 5, min_train)
    bt = outputs["bt"]
    ranking = outputs["ranking"]
    q = outputs["q"]
    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else None
    state = {
        "agent_version": AGENT_VERSION,
        "model_version": champion.version(),
        "model_config": asdict(champion),
        "git_sha": git_sha,
        "data_sha256": data_sha,
        "rows": int(len(clean)),
        "latest_draw_date": latest_date,
        "latest_round": latest_round_text,
        "target_round": f"第{outputs['target_round']}回",
        "research_generation": generation,
        "production_promotion_method": "future_oos_only",
        "promotion_this_run": promotion,
        "walk_forward_draws": bt.draws_tested,
        "mean_top7_hits": bt.mean_hits,
        "random_theoretical_mean_hits": RANDOM_HIT_MEAN,
        "z_vs_random": bt.z_vs_random,
        "approx_two_sided_p": bt.approx_two_sided_p,
        "signal_claim": "not_confirmed" if bt.approx_two_sided_p >= 0.05 else "requires_independent_validation",
        "expert_weights": {k: float(bt.final_weights[i]) for i, k in enumerate(bt.keys)},
        "top15": [
            {"number": int(n), "relative_score": float(q[n - 1]),
             "score_index_vs_uniform": float(q[n - 1] / (1.0 / N_NUMBERS))}
            for n in ranking[:15]
        ],
        "seed": outputs["seed"],
    }
    write_json(state_path, state)
    return {"cached": False, "state": state, "outputs": outputs}


def main() -> int:
    ap = argparse.ArgumentParser(description="LOTO7 AI Agent v4 continuous research with future-OOS production governance")
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--candidate-pool", type=Path, default=Path("loto7_agent_output/candidate_pool.json"))
    ap.add_argument("--shadow-registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    ap.add_argument("--oos-state", type=Path, default=Path("loto7_agent_output/oos_candidate_state.json"))
    ap.add_argument("--oos-results", type=Path, default=Path("loto7_agent_output/shadow_oos_results.csv"))
    ap.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--challengers", type=int, default=6)
    ap.add_argument("--portfolio-backtest-pool", type=int, default=650)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flexible(args.csv)
    x, clean = make_history(df)
    data_sha = fingerprint_file(args.csv)
    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    latest_round = parse_round(latest_round_text) or int(len(clean))
    target_round = latest_round + 1
    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    actual_set = set((np.flatnonzero(x[-1]) + 1).tolist())
    git_sha = os.environ.get("GITHUB_SHA", "local")
    verification, source_trusted = source_info(args.source_report, latest_round)

    state = load_json(args.research_state, {
        "agent_version": AGENT_VERSION,
        "generation": 0,
        "current_data_sha": "",
        "research_parent_config": None,
        "total_research_evaluations": 0,
        "total_promotions": 0,
    })
    generation = int(state.get("generation", 0)) + 1
    new_data = str(state.get("current_data_sha", "")) != data_sha

    champion_before = v2.load_champion(args.champion_file)
    registry = load_json(args.shadow_registry, {})
    oos_state = load_json(args.oos_state, {"agent_version": AGENT_VERSION, "graded_rounds": [], "evidence": {}})
    graded = False
    if new_data and registry:
        graded = grade_registry(registry, latest_round, latest_date, actual_set, verification,
                                source_trusted, oos_state, args.oos_results)

    champion, promotion = promote_if_eligible(
        champion_before, args.champion_file, oos_state, latest_round_text,
        latest_date, data_sha, git_sha, source_trusted and graded,
    )
    if promotion:
        state["total_promotions"] = int(state.get("total_promotions", 0)) + 1

    parent = champion
    parsed_parent = cfg_from_obj(state.get("research_parent_config"))
    if parsed_parent is not None:
        parent = parsed_parent
    if promotion:
        parent = champion

    configs = make_research_configs(champion, parent, data_sha, generation, args.challengers)
    evaluations = [
        v3.evaluate_config(x, cfg, min_train=args.min_train, pool_size=args.portfolio_backtest_pool)
        for cfg in configs
    ]
    eval_by_version = {str(ev["version"]): ev for ev in evaluations}
    champion_eval = eval_by_version[champion.version()]
    research_winner = max(evaluations, key=research_score)

    protected_versions = [str(item.get("version")) for item in (registry.get("candidates") or []) if isinstance(item, dict)]
    pool = update_candidate_pool(args.candidate_pool, evaluations, champion.version(),
                                 generation, data_sha, protected_versions)

    freeze_needed = (
        int(registry.get("target_round", -1)) != target_round
        or str(registry.get("base_data_sha", "")) != data_sha
        or str(registry.get("champion_version", "")) != champion.version()
    )
    if freeze_needed:
        shadow_configs = select_shadow_configs(pool, registry, oos_state, champion.version())
        registry = freeze_registry(
            args.shadow_registry, target_round, data_sha, champion, champion_eval,
            shadow_configs, eval_by_version, x, args.min_train,
            args.portfolio_backtest_pool, verification,
        )

    write_research_outputs(args.out_dir, research_winner, target_round, generation)
    production = ensure_production_outputs(
        x, clean, champion, args.out_dir, args.min_train, data_sha, git_sha,
        generation, force=new_data or bool(promotion), promotion=promotion,
    )

    write_json(args.out_dir / "v4_research_evaluation.json", {
        "agent_version": AGENT_VERSION,
        "created_at_jst": now_jst(),
        "generation": generation,
        "data_sha256": data_sha,
        "new_data": new_data,
        "source_verification": verification,
        "source_trusted_for_promotion": source_trusted,
        "champion_before": champion_before.version(),
        "champion_after": champion.version(),
        "promotion": promotion,
        "promotion_policy": {
            "historical_research_can_promote": False,
            "minimum_trusted_oos_draws": MIN_TRUSTED_OOS_DRAWS,
            "e_value_threshold": E_VALUE_THRESHOLD,
            "minimum_mean_score_delta": MIN_MEAN_SCORE_DELTA,
            "minimum_oos_win_rate": MIN_OOS_WIN_RATE,
        },
        "research_parent": parent.version(),
        "research_winner": research_winner["version"],
        "research_winner_score": research_score(research_winner),
        "shadow_target_round": registry.get("target_round"),
        "shadow_candidate_count": len(registry.get("candidates", []) or []),
        "oos_graded_this_run": graded,
        "production_outputs_cached": bool(production.get("cached")),
        "evaluations": [
            {"version": ev["version"], "config": ev["config"],
             "research_score": research_score(ev), "windows": ev["windows"]}
            for ev in evaluations
        ],
    })

    state.update({
        "agent_version": AGENT_VERSION,
        "generation": generation,
        "current_data_sha": data_sha,
        "last_run_jst": now_jst(),
        "research_parent_config": research_winner["config"],
        "research_winner": research_winner["version"],
        "champion_version": champion.version(),
        "total_research_evaluations": int(state.get("total_research_evaluations", 0)) + max(0, len(evaluations) - 1),
        "last_data_change_generation": generation if new_data else int(state.get("last_data_change_generation", generation)),
        "last_promotion": promotion,
        "source_verification": verification,
        "source_trusted_for_promotion": source_trusted,
    })
    write_json(args.research_state, state)
    write_json(args.oos_state, oos_state)
    write_json(args.out_dir / "run_events.json", {
        "created_at_jst": now_jst(),
        "generation": generation,
        "new_data": new_data,
        "oos_graded": graded,
        "promotion": bool(promotion),
        "force_checkpoint": bool(new_data or graded or promotion or freeze_needed),
    })

    print(f"[V4] generation={generation} new_data={new_data} research_winner={research_winner['version']}")
    print(f"[OOS] graded={graded} trusted_source={source_trusted} target_round={target_round}")
    print(f"[PRODUCTION] champion={champion.version()} promoted={bool(promotion)} historical_research_promotion=DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
