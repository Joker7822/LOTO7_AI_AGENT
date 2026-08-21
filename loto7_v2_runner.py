#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from loto7_evolving_agent import (
    N_NUMBERS,
    PICKS,
    RANDOM_HIT_MEAN,
    expert_probabilities,
    fingerprint_file,
    make_history,
    make_ticket_portfolio,
    read_csv_flexible,
    walk_forward_evolve,
)


@dataclass(frozen=True)
class ModelConfig:
    name: str
    eta: float
    decay: float
    expert_uniform_mix: float
    final_uniform_mix: float
    overlap_penalty: float

    def version(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False).encode("utf-8")
        return f"{self.name}-{hashlib.sha256(payload).hexdigest()[:10]}"


DEFAULT_CHAMPION = ModelConfig("baseline", 3.0, 0.995, 0.15, 0.20, 0.65)
CHALLENGERS = [
    ModelConfig("stable", 1.8, 0.997, 0.22, 0.28, 0.75),
    ModelConfig("balanced", 2.4, 0.993, 0.20, 0.24, 0.70),
    ModelConfig("adaptive", 4.0, 0.990, 0.15, 0.20, 0.65),
]


def _weights_from_log(logw: np.ndarray, uniform_mix: float) -> np.ndarray:
    raw = np.exp(logw - logw.max())
    raw /= raw.sum()
    return (1.0 - uniform_mix) * raw + uniform_mix / len(raw)


def _score_distribution(hist: np.ndarray, keys: List[str], logw: np.ndarray, config: ModelConfig) -> np.ndarray:
    ex = expert_probabilities(hist)
    w = _weights_from_log(logw, config.expert_uniform_mix)
    q = np.zeros(N_NUMBERS, dtype=float)
    for i, k in enumerate(keys):
        q += w[i] * ex[k]
    q /= q.sum()
    q = (1.0 - config.final_uniform_mix) * q + config.final_uniform_mix / N_NUMBERS
    return q / q.sum()


def _update_log_weights(hist: np.ndarray, actual: np.ndarray, keys: List[str], logw: np.ndarray, config: ModelConfig) -> np.ndarray:
    ex = expert_probabilities(hist)
    rewards = np.array([float(ex[k][actual].sum()) for k in keys], dtype=float)
    updated = config.decay * logw + config.eta * (rewards - PICKS / N_NUMBERS)
    return np.clip(updated, -20.0, 20.0)


def _random_portfolio(rng: np.random.Generator, n_tickets: int = 5) -> List[Tuple[int, ...]]:
    universe = np.arange(1, N_NUMBERS + 1)
    return [tuple(sorted(int(x) for x in rng.choice(universe, size=PICKS, replace=False))) for _ in range(n_tickets)]


def _portfolio_metrics(portfolio: List[Tuple[int, ...]], actual_set: set[int]) -> Dict[str, float]:
    hits = [len(set(t) & actual_set) for t in portfolio]
    return {"max_hits": float(max(hits)), "mean_hits": float(np.mean(hits)), "ge3": float(any(h >= 3 for h in hits)), "ge4": float(any(h >= 4 for h in hits))}


def _aggregate(rows: List[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {"max_hits":0.0,"mean_hits":0.0,"ge3_rate":0.0,"ge4_rate":0.0,"score":0.0}
    max_hits = float(np.mean([r["max_hits"] for r in rows]))
    mean_hits = float(np.mean([r["mean_hits"] for r in rows]))
    ge3 = float(np.mean([r["ge3"] for r in rows]))
    ge4 = float(np.mean([r["ge4"] for r in rows]))
    score = max_hits + 0.35 * ge3 + 0.75 * ge4 + 0.10 * mean_hits
    return {"max_hits":max_hits,"mean_hits":mean_hits,"ge3_rate":ge3,"ge4_rate":ge4,"score":score}


def evaluate_config(x: np.ndarray, config: ModelConfig, min_train: int = 100, max_window: int = 120, pool_size: int = 900) -> Dict[str, object]:
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    eval_start = max(min_train, len(x) - max_window)
    model_rows: List[Dict[str, float]] = []
    random_rows: List[Dict[str, float]] = []
    for t in range(min_train, len(x)):
        if t >= eval_start:
            q = _score_distribution(x[:t], keys, logw, config)
            portfolio = make_ticket_portfolio(q, n_tickets=5, seed=100000+t, pool_size=pool_size, overlap_penalty=config.overlap_penalty)
            actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
            model_rows.append(_portfolio_metrics(portfolio, actual_set))
            reps = []
            for rep in range(12):
                rng = np.random.default_rng(700000 + t * 31 + rep)
                reps.append(_portfolio_metrics(_random_portfolio(rng), actual_set))
            random_rows.append({k: float(np.mean([r[k] for r in reps])) for k in ("max_hits","mean_hits","ge3","ge4")})
        actual = np.flatnonzero(x[t])
        logw = _update_log_weights(x[:t], actual, keys, logw, config)
    windows: Dict[str, object] = {}
    for window in (60,120):
        n = min(window, len(model_rows))
        m = _aggregate(model_rows[-n:]); r = _aggregate(random_rows[-n:])
        windows[str(window)] = {"draws":n,"model":m,"random":r,"score_delta":m["score"]-r["score"],"max_hits_delta":m["max_hits"]-r["max_hits"]}
    final_weights = _weights_from_log(logw, config.expert_uniform_mix)
    q = _score_distribution(x, keys, logw, config)
    return {"config":asdict(config),"version":config.version(),"windows":windows,"expert_keys":keys,"final_weights":{k:float(final_weights[i]) for i,k in enumerate(keys)},"final_q":q}


def load_champion(path: Path) -> ModelConfig:
    if not path.exists(): return DEFAULT_CHAMPION
    try:
        obj=json.loads(path.read_text(encoding="utf-8")); cfg=obj.get("config",obj)
        return ModelConfig(name=str(cfg["name"]),eta=float(cfg["eta"]),decay=float(cfg["decay"]),expert_uniform_mix=float(cfg["expert_uniform_mix"]),final_uniform_mix=float(cfg["final_uniform_mix"]),overlap_penalty=float(cfg["overlap_penalty"]))
    except Exception:
        return DEFAULT_CHAMPION


def promotion_decision(champion_eval: Dict[str, object], challenger_eval: Dict[str, object]) -> Tuple[bool, str]:
    cw=champion_eval["windows"]; nw=challenger_eval["windows"]; deltas=[]
    for w in ("60","120"):
        if int(nw[w]["draws"]) < 40: return False, f"window {w} has fewer than 40 draws"
        delta=float(nw[w]["model"]["score"])-float(cw[w]["model"]["score"])
        max_delta=float(nw[w]["model"]["max_hits"])-float(cw[w]["model"]["max_hits"])
        deltas.append(delta)
        if delta <= 0.01: return False, f"window {w} score improvement <= 0.01"
        if max_delta < -0.01: return False, f"window {w} max-hit metric regressed"
    if float(np.mean(deltas)) < 0.02: return False, "mean multi-window improvement < 0.02"
    return True, "challenger beat champion on both independent windows"


def choose_model(x: np.ndarray, champion_path: Path, min_train: int, pool_size: int) -> Tuple[ModelConfig, Dict[str, object]]:
    champion=load_champion(champion_path)
    configs=[champion]+[c for c in CHALLENGERS if c.version()!=champion.version()]
    evaluations=[evaluate_config(x,c,min_train=min_train,pool_size=pool_size) for c in configs]
    champ_eval=evaluations[0]; eligible=[]; decisions=[]
    for ev in evaluations[1:]:
        ok,reason=promotion_decision(champ_eval,ev); decisions.append({"challenger":ev["version"],"eligible":ok,"reason":reason})
        if ok: eligible.append(ev)
    promoted=False; selected_eval=champ_eval
    if eligible:
        selected_eval=max(eligible,key=lambda ev:float(ev["windows"]["120"]["model"]["score"])+float(ev["windows"]["60"]["model"]["score"])); promoted=True
    selected=ModelConfig(**selected_eval["config"])
    report={"champion_before":champ_eval["version"],"selected_version":selected_eval["version"],"promoted":promoted,"promotion_checks":decisions,"evaluations":[{k:v for k,v in ev.items() if k!="final_q"} for ev in evaluations]}
    return selected, report


def build_current_outputs(x: np.ndarray, clean: pd.DataFrame, cfg: ModelConfig, out_dir: Path, tickets: int, min_train: int) -> Dict[str, object]:
    bt=walk_forward_evolve(x,min_train=min_train,eta=cfg.eta,decay=cfg.decay,expert_uniform_mix=cfg.expert_uniform_mix)
    ex=expert_probabilities(x); q=np.zeros(N_NUMBERS,dtype=float)
    for i,k in enumerate(bt.keys): q += bt.final_weights[i]*ex[k]
    q/=q.sum(); q=(1.0-cfg.final_uniform_mix)*q+cfg.final_uniform_mix/N_NUMBERS; q/=q.sum()
    latest_round_text=str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    digits="".join(ch for ch in latest_round_text if ch.isdigit()); target_round=int(digits)+1 if digits else len(clean)+1
    seed=target_round; portfolio=make_ticket_portfolio(q,tickets,seed=seed,overlap_penalty=cfg.overlap_penalty)
    out_dir.mkdir(parents=True,exist_ok=True); ranking=np.argsort(q)[::-1]+1
    pd.DataFrame({"rank":np.arange(1,N_NUMBERS+1),"number":ranking,"relative_score":[float(q[n-1]) for n in ranking],"score_index_vs_uniform":[float(q[n-1]/(1.0/N_NUMBERS)) for n in ranking]}).to_csv(out_dir/"prediction_ranking.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame([{"ticket":i,"numbers":" ".join(f"{n:02d}" for n in t),"sum":sum(t),"odd_count":sum(n%2 for n in t)} for i,t in enumerate(portfolio,1)]).to_csv(out_dir/"candidate_tickets.csv",index=False,encoding="utf-8-sig")
    bt.expert_summary.to_csv(out_dir/"expert_backtest.csv",index=False,encoding="utf-8-sig")
    return {"q":q,"portfolio":portfolio,"target_round":target_round,"seed":seed,"bt":bt,"ranking":ranking}


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",type=Path,required=True); ap.add_argument("--out-dir",type=Path,default=Path("loto7_agent_output")); ap.add_argument("--champion-file",type=Path,default=Path("loto7_agent_output/model_champion.json")); ap.add_argument("--tickets",type=int,default=5); ap.add_argument("--min-train",type=int,default=100); ap.add_argument("--portfolio-backtest-pool",type=int,default=900); args=ap.parse_args()
    if args.tickets != 5: raise SystemExit("v2 production runner requires exactly --tickets 5")
    df=read_csv_flexible(args.csv); x,clean=make_history(df)
    selected,evaluation=choose_model(x,args.champion_file,args.min_train,args.portfolio_backtest_pool)
    outputs=build_current_outputs(x,clean,selected,args.out_dir,args.tickets,args.min_train)
    latest_date=clean["抽せん日"].iloc[-1].date().isoformat(); latest_round=str(clean["回別"].iloc[-1]) if "回別" in clean.columns else None
    model_version=selected.version(); git_sha=os.environ.get("GITHUB_SHA","local"); data_sha=fingerprint_file(args.csv)
    champion_obj={"model_version":model_version,"config":asdict(selected),"selected_at_data_round":latest_round,"selected_at_data_date":latest_date,"data_sha256":data_sha,"git_sha":git_sha}
    args.champion_file.parent.mkdir(parents=True,exist_ok=True); args.champion_file.write_text(json.dumps(champion_obj,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.out_dir/"model_evaluation.json").write_text(json.dumps(evaluation,ensure_ascii=False,indent=2),encoding="utf-8")
    bt=outputs["bt"]; ranking=outputs["ranking"]; q=outputs["q"]
    state={"model_version":model_version,"model_config":asdict(selected),"git_sha":git_sha,"data_sha256":data_sha,"rows":int(len(clean)),"latest_draw_date":latest_date,"latest_round":latest_round,"target_round":f"第{outputs['target_round']}回","walk_forward_draws":bt.draws_tested,"mean_top7_hits":bt.mean_hits,"random_theoretical_mean_hits":RANDOM_HIT_MEAN,"z_vs_random":bt.z_vs_random,"approx_two_sided_p":bt.approx_two_sided_p,"signal_claim":"not_confirmed" if bt.approx_two_sided_p>=0.05 else "requires_independent_validation","expert_weights":{k:float(bt.final_weights[i]) for i,k in enumerate(bt.keys)},"top15":[{"number":int(n),"relative_score":float(q[n-1]),"score_index_vs_uniform":float(q[n-1]/(1/N_NUMBERS))} for n in ranking[:15]],"seed":outputs["seed"],"portfolio_backtest":evaluation}
    (args.out_dir/"agent_state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"[MODEL] selected={model_version} promoted={evaluation['promoted']}")
    selected_eval=next(ev for ev in evaluation["evaluations"] if ev["version"]==model_version)
    for w in ("60","120"):
        m=selected_eval["windows"][w]["model"]; r=selected_eval["windows"][w]["random"]
        print(f"[BACKTEST {w}] max_hits={m['max_hits']:.3f} random={r['max_hits']:.3f} ge3={m['ge3_rate']:.3f} random={r['ge3_rate']:.3f}")
    print("[PREDICTIONS]")
    for i,t in enumerate(outputs["portfolio"],1): print(f"{i}. {' '.join(f'{n:02d}' for n in t)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
