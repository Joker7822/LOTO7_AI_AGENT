#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
import loto7_v4_runner as v4
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

REPORT_VERSION = "research-feedback-v1"
WINDOW_WEIGHTS = {"full": 0.35, "120": 0.35, "60": 0.20, "30": 0.10}
MIN_OBJECTIVE_IMPROVEMENT = 0.002
MAX_FULL_MAX_HITS_REGRESSION = 0.01
MAX_RECENT120_SCORE_REGRESSION = 0.02
ROUND_FIELDS = [
    "round_index", "model_version", "model_score", "random_score",
    "score_delta_vs_random", "model_max_hits", "model_mean_hits",
    "model_ge3", "model_ge4", "random_max_hits", "random_mean_hits",
    "random_ge3", "random_ge4",
]


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


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROUND_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in ROUND_FIELDS})


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


def aggregate(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {
            "max_hits": 0.0, "mean_hits": 0.0, "ge3": 0.0, "ge4": 0.0,
            "score": 0.0, "random_max_hits": 0.0, "random_mean_hits": 0.0,
            "random_ge3": 0.0, "random_ge4": 0.0, "random_score": 0.0,
            "score_delta_vs_random": 0.0, "max_hits_delta_vs_random": 0.0,
        }
    keys = [
        "max_hits", "mean_hits", "ge3", "ge4", "score",
        "random_max_hits", "random_mean_hits", "random_ge3", "random_ge4", "random_score",
    ]
    out = {k: float(np.mean([float(r[k]) for r in rows])) for k in keys}
    out["score_delta_vs_random"] = out["score"] - out["random_score"]
    out["max_hits_delta_vs_random"] = out["max_hits"] - out["random_max_hits"]
    return out


def random_metrics(actual_set: set[int], t: int, reps: int) -> Dict[str, float]:
    samples = []
    for rep in range(max(1, int(reps))):
        rng = np.random.default_rng(12_000_000 + t * 1009 + rep)
        samples.append(v2._portfolio_metrics(v2._random_portfolio(rng), actual_set))
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in samples])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in samples])),
        "ge3": float(np.mean([r["ge3"] for r in samples])),
        "ge4": float(np.mean([r["ge4"] for r in samples])),
        "score": float(np.mean([v3.row_score(r) for r in samples])),
    }


def simulate_model(x: np.ndarray, config: v2.ModelConfig, min_train: int,
                   pool_size: int, random_reps: int) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """Replay every eligible historical draw using only rows strictly before that draw.

    The config itself may have been discovered using historical research, so this is research
    feedback, not independent evidence. Production promotion must never consume this result.
    """
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    seed_offset = int(hashlib.sha256(config.version().encode()).hexdigest()[:8], 16) % 100000
    numeric_rows: List[Dict[str, float]] = []
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
        model_score = float(v3.row_score(m))
        rnd = random_metrics(actual_set, t, random_reps)
        rec = {
            "max_hits": float(m["max_hits"]),
            "mean_hits": float(m["mean_hits"]),
            "ge3": float(m["ge3"]),
            "ge4": float(m["ge4"]),
            "score": model_score,
            "random_max_hits": rnd["max_hits"],
            "random_mean_hits": rnd["mean_hits"],
            "random_ge3": rnd["ge3"],
            "random_ge4": rnd["ge4"],
            "random_score": rnd["score"],
        }
        numeric_rows.append(rec)
        csv_rows.append({
            "round_index": t + 1,
            "model_version": config.version(),
            "model_score": f"{model_score:.6f}",
            "random_score": f"{rnd['score']:.6f}",
            "score_delta_vs_random": f"{model_score-rnd['score']:.6f}",
            "model_max_hits": f"{m['max_hits']:.0f}",
            "model_mean_hits": f"{m['mean_hits']:.6f}",
            "model_ge3": f"{m['ge3']:.0f}",
            "model_ge4": f"{m['ge4']:.0f}",
            "random_max_hits": f"{rnd['max_hits']:.6f}",
            "random_mean_hits": f"{rnd['mean_hits']:.6f}",
            "random_ge3": f"{rnd['ge3']:.6f}",
            "random_ge4": f"{rnd['ge4']:.6f}",
        })
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, config)

    windows: Dict[str, Dict[str, float]] = {"full": aggregate(numeric_rows)}
    for n in (120, 60, 30):
        windows[str(n)] = aggregate(numeric_rows[-min(n, len(numeric_rows)):])
    objective = float(sum(
        WINDOW_WEIGHTS[name] * float(windows[name]["score_delta_vs_random"])
        for name in WINDOW_WEIGHTS
    ))
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "evaluation_type": "retrospective_full_history_research_feedback",
        "model_version": config.version(),
        "config": asdict(config),
        "evaluated_rounds": len(numeric_rows),
        "min_train": int(min_train),
        "pool_size": int(pool_size),
        "random_reps": int(random_reps),
        "windows": windows,
        "feedback_objective": objective,
        "independent_evidence": False,
        "promotion_eligible": False,
    }
    return summary, csv_rows


def cache_key(data_sha: str, config: v2.ModelConfig, min_train: int,
              pool_size: int, random_reps: int) -> str:
    raw = f"{REPORT_VERSION}|{data_sha}|{config.version()}|{min_train}|{pool_size}|{random_reps}"
    return hashlib.sha256(raw.encode()).hexdigest()


def evaluate_cached(x: np.ndarray, config: v2.ModelConfig, data_sha: str,
                    cache: Dict[str, object], min_train: int, pool_size: int,
                    random_reps: int) -> Tuple[Dict[str, object], List[Dict[str, object]], bool]:
    entries = cache.setdefault("entries", {})
    assert isinstance(entries, dict)
    key = cache_key(data_sha, config, min_train, pool_size, random_reps)
    old = entries.get(key)
    if isinstance(old, dict):
        return old, [], True
    summary, rows = simulate_model(x, config, min_train, pool_size, random_reps)
    summary["data_sha256"] = data_sha
    entries[key] = summary
    cache["report_version"] = REPORT_VERSION
    return summary, rows, False


def decide_accept(candidate: Dict[str, object], incumbent: Dict[str, object]) -> Tuple[bool, Dict[str, object]]:
    cobj = float(candidate.get("feedback_objective", 0.0))
    iobj = float(incumbent.get("feedback_objective", 0.0))
    cw = candidate["windows"]
    iw = incumbent["windows"]
    gain = cobj - iobj
    checks = {
        "objective_improves": gain > MIN_OBJECTIVE_IMPROVEMENT,
        "full_max_hits_not_regressed": (
            float(cw["full"]["max_hits"]) >= float(iw["full"]["max_hits"]) - MAX_FULL_MAX_HITS_REGRESSION
        ),
        "recent120_score_not_regressed": (
            float(cw["120"]["score"]) >= float(iw["120"]["score"]) - MAX_RECENT120_SCORE_REGRESSION
        ),
    }
    return all(checks.values()), {
        "candidate_objective": cobj,
        "incumbent_objective": iobj,
        "objective_gain": gain,
        "checks": checks,
    }


def find_candidate_config(evaluation: Dict[str, object]) -> Optional[v2.ModelConfig]:
    version = str(evaluation.get("research_winner", ""))
    for item in evaluation.get("evaluations", []) or []:
        if isinstance(item, dict) and str(item.get("version", "")) == version:
            return cfg_from_obj(item.get("config"))
    return None


def render_report(record: Dict[str, object]) -> str:
    cand = record.get("candidate_summary") or {}
    inc = record.get("incumbent_summary") or {}
    decision = record.get("decision") or {}
    selected = record.get("accepted_parent_version", "")
    lines = [
        "# Research Winner Full-History Replay Feedback",
        "",
        f"- generation: **{record.get('generation')}**",
        f"- provisional winner: **{record.get('candidate_version')}**",
        f"- incumbent research parent: **{record.get('incumbent_version')}**",
        f"- accepted research parent: **{selected}**",
        f"- candidate accepted: **{'YES' if record.get('candidate_accepted') else 'NO'}**",
        f"- replay cache used: **{'YES' if record.get('candidate_cache_hit') else 'NO'}**",
        "- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**",
        "",
        "| 指標 | Candidate | Incumbent |",
        "|---|---:|---:|",
    ]
    if isinstance(cand, dict) and isinstance(inc, dict) and cand and inc:
        for label, key in (("feedback objective", "feedback_objective"),):
            lines.append(f"| {label} | {float(cand.get(key,0.0)):.4f} | {float(inc.get(key,0.0)):.4f} |")
        for name in ("full", "120", "60", "30"):
            cwin = (cand.get("windows") or {}).get(name, {})
            iwin = (inc.get("windows") or {}).get(name, {})
            lines.append(
                f"| {name} score Δ vs random | {float(cwin.get('score_delta_vs_random',0.0)):+.4f} | "
                f"{float(iwin.get('score_delta_vs_random',0.0)):+.4f} |"
            )
        lines += [
            "",
            f"- objective gain: **{float(decision.get('objective_gain',0.0)):+.4f}**",
            f"- checks: `{json.dumps(decision.get('checks', {}), ensure_ascii=False, sort_keys=True)}`",
        ]
    lines += [
        "",
        "> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。",
        "",
    ]
    return "\n".join(lines)


def apply_parent_to_research_state(state: Dict[str, object], candidate: v2.ModelConfig,
                                   accepted: v2.ModelConfig, feedback: Dict[str, object]) -> None:
    state["provisional_research_winner"] = candidate.version()
    state["research_parent_config"] = asdict(accepted)
    state["research_winner"] = accepted.version()
    state["research_feedback_last"] = feedback
    state["research_feedback_replays"] = int(state.get("research_feedback_replays", 0)) + int(bool(feedback.get("replayed")))
    state["research_feedback_accepts"] = int(state.get("research_feedback_accepts", 0)) + int(bool(feedback.get("candidate_accepted")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay each new v4 Research Winner over all historical rounds and feed results into the next research parent")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--evaluation", type=Path, default=Path("loto7_agent_output/v4_research_evaluation.json"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--pool-size", type=int, default=350)
    ap.add_argument("--random-reps", type=int, default=8)
    args = ap.parse_args()

    state = load_json(args.research_state, {})
    evaluation = load_json(args.evaluation, {})
    feedback_state = load_json(args.feedback_state, {
        "report_version": REPORT_VERSION,
        "accepted_parent_config": None,
        "last_candidate_version": "",
        "data_sha256": "",
        "replay_count": 0,
        "accept_count": 0,
    })
    candidate = find_candidate_config(evaluation)
    if candidate is None:
        raise SystemExit("research winner config not found in v4_research_evaluation.json")

    df = read_csv_flexible(args.csv)
    x, clean = make_history(df)
    data_sha = fingerprint_file(args.csv)
    generation = int(state.get("generation", evaluation.get("generation", 0)))

    incumbent = cfg_from_obj(feedback_state.get("accepted_parent_config"))
    if incumbent is None:
        incumbent = v2.load_champion(args.champion_file)

    data_changed = str(feedback_state.get("data_sha256", "")) != data_sha
    candidate_changed = str(feedback_state.get("last_candidate_version", "")) != candidate.version()
    replay_needed = data_changed or candidate_changed or not feedback_state.get("accepted_parent_config")

    if not replay_needed:
        feedback = {
            "replayed": False,
            "candidate_accepted": False,
            "candidate_version": candidate.version(),
            "accepted_parent_version": incumbent.version(),
            "reason": "same candidate and same data; cached accepted research parent retained",
        }
        apply_parent_to_research_state(state, candidate, incumbent, feedback)
        write_json(args.research_state, state)
        print(f"[REPLAY-FEEDBACK] skipped candidate={candidate.version()} parent={incumbent.version()}")
        return 0

    cache_path = args.out_dir / "research_feedback_cache.json"
    cache = load_json(cache_path, {"report_version": REPORT_VERSION, "entries": {}})
    incumbent_summary, _, incumbent_cache_hit = evaluate_cached(
        x, incumbent, data_sha, cache, args.min_train, args.pool_size, args.random_reps
    )
    if candidate.version() == incumbent.version():
        candidate_summary = incumbent_summary
        candidate_rows: List[Dict[str, object]] = []
        candidate_cache_hit = True
        accepted_candidate = False
        decision = {
            "candidate_objective": float(candidate_summary.get("feedback_objective", 0.0)),
            "incumbent_objective": float(incumbent_summary.get("feedback_objective", 0.0)),
            "objective_gain": 0.0,
            "checks": {"same_model": True},
        }
        selected = incumbent
    else:
        candidate_summary, candidate_rows, candidate_cache_hit = evaluate_cached(
            x, candidate, data_sha, cache, args.min_train, args.pool_size, args.random_reps
        )
        accepted_candidate, decision = decide_accept(candidate_summary, incumbent_summary)
        selected = candidate if accepted_candidate else incumbent

    write_json(cache_path, cache)
    if candidate_rows:
        write_csv(args.out_dir / "research_feedback_candidate_rounds.csv", candidate_rows)

    record: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "generation": generation,
        "data_sha256": data_sha,
        "replayed": True,
        "candidate_version": candidate.version(),
        "candidate_config": asdict(candidate),
        "incumbent_version": incumbent.version(),
        "incumbent_config": asdict(incumbent),
        "candidate_cache_hit": candidate_cache_hit,
        "incumbent_cache_hit": incumbent_cache_hit,
        "candidate_summary": candidate_summary,
        "incumbent_summary": incumbent_summary,
        "decision": decision,
        "candidate_accepted": bool(accepted_candidate),
        "accepted_parent_version": selected.version(),
        "accepted_parent_config": asdict(selected),
        "independent_evidence": False,
        "production_promotion_eligible": False,
    }
    write_json(args.out_dir / "research_feedback_summary.json", record)
    (args.out_dir / "research_feedback_report.md").write_text(render_report(record), encoding="utf-8")
    append_jsonl(args.out_dir / "research_feedback_history.jsonl", record)

    feedback_state.update({
        "report_version": REPORT_VERSION,
        "data_sha256": data_sha,
        "last_candidate_version": candidate.version(),
        "last_candidate_config": asdict(candidate),
        "accepted_parent_version": selected.version(),
        "accepted_parent_config": asdict(selected),
        "accepted_parent_summary": candidate_summary if selected.version() == candidate.version() else incumbent_summary,
        "last_decision": decision,
        "last_generation": generation,
        "replay_count": int(feedback_state.get("replay_count", 0)) + 1,
        "accept_count": int(feedback_state.get("accept_count", 0)) + int(bool(accepted_candidate)),
    })
    write_json(args.feedback_state, feedback_state)

    feedback = {
        "replayed": True,
        "candidate_accepted": bool(accepted_candidate),
        "candidate_version": candidate.version(),
        "accepted_parent_version": selected.version(),
        "objective_gain": float(decision.get("objective_gain", 0.0)),
    }
    apply_parent_to_research_state(state, candidate, selected, feedback)
    write_json(args.research_state, state)

    evaluation["provisional_research_winner"] = candidate.version()
    evaluation["research_parent_after_replay_feedback"] = selected.version()
    evaluation["research_replay_feedback"] = feedback
    write_json(args.evaluation, evaluation)

    if selected.version() != candidate.version():
        accepted_eval = v3.evaluate_config(x, selected, min_train=args.min_train, pool_size=650)
        latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
        digits = "".join(ch for ch in latest_round_text if ch.isdigit())
        target_round = int(digits) + 1 if digits else len(clean) + 1
        v4.write_research_outputs(args.out_dir, accepted_eval, target_round, generation)

    events_path = args.out_dir / "run_events.json"
    events = load_json(events_path, {})
    events["research_feedback_replayed"] = True
    events["research_feedback_candidate_accepted"] = bool(accepted_candidate)
    events["research_feedback_parent"] = selected.version()
    events["force_checkpoint"] = True
    write_json(events_path, events)

    print(
        f"[REPLAY-FEEDBACK] candidate={candidate.version()} accepted={accepted_candidate} "
        f"parent={selected.version()} gain={float(decision.get('objective_gain',0.0)):+.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
