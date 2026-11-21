#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only retraining of the 37-number ranking signal.

Predeclared challenger: 50% official Champion probability vector and 50%
online exponentiated *log-score* expert ensemble. Both models learn only from
the draws occurring strictly before each ranked prediction. Neither this
script nor its workflow edits Production, Champion, or registered Future-OOS.

The training method and parameters were written after historical outcomes.
All backtests are retrospective diagnostics, NOT future OOS confirmation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

import balanced_uniform_portfolio as uniform_geometry
import loto7_v2_runner as v2
import loto7_v3_runner as v3
from audit_ledger import grade_ticket
from loto7_evolving_agent import (
    N_NUMBERS, PICKS, RANDOM_HIT_MEAN, expert_probabilities,
    fingerprint_file, make_history, read_csv_flexible,
)
from production_ticket_geometry35 import ranked_portfolio_from_scores

VERSION = "research-logscore-blended-ranking-v1"
MIN_TRAIN = 100
LOG_ETA = 3.0
LOG_DECAY = 0.995
LOG_EXPERT_UNIFORM_MIX = 0.25
BLEND_TO_LOGSCORE = 0.50
WINDOWS = (60, 120)
TICKET_FIELDS = (
    "round", "draw_date", "model", "ticket", "predicted_numbers",
    "actual_main_numbers", "main_hits", "bonus_hits", "grade",
)
ROUND_FIELDS = (
    "round", "draw_date", "training_rows", "champion_rank_top7",
    "candidate_rank_top7", "champion_rank_top35", "candidate_rank_top35",
    "champion_excluded_2", "candidate_excluded_2",
    "champion_top7_hits", "candidate_top7_hits",
    "champion_actual_mass", "candidate_actual_mass",
    "champion_mean_log_actual", "candidate_mean_log_actual",
    "champion_brier", "candidate_brier", "uniform_brier",
    "champion_portfolio_score", "candidate_portfolio_score",
    "champion_max_hits", "candidate_max_hits",
    "champion_ge3", "candidate_ge3",
    "champion_ge4", "candidate_ge4",
    "candidate_minus_champion_score", "candidate_minus_champion_log",
    "candidate_minus_champion_top7", "rank_positions_changed",
)


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _fmt(nums: Sequence[int]) -> str:
    return " ".join(f"{int(n):02d}" for n in nums)


def _stable_weights(logw: np.ndarray, uniform_mix: float) -> np.ndarray:
    if logw.ndim != 1 or len(logw) == 0 or not np.all(np.isfinite(logw)):
        raise ValueError("invalid log-score ensemble weight vector")
    raw = np.exp(logw - max(logw))
    raw /= raw.sum()
    return (1.0 - uniform_mix) * raw + uniform_mix / len(raw)


def _candidate_score(
    expert_probs: dict[str, np.ndarray],
    keys: list[str],
    log_score_weights: np.ndarray,
    incumbent_score: np.ndarray,
) -> np.ndarray:
    if set(expert_probs) != set(keys):
        raise RuntimeError("expert registry changed within fixed ranking retraining")
    w = _stable_weights(log_score_weights, LOG_EXPERT_UNIFORM_MIX)
    q_log = np.zeros(N_NUMBERS, dtype=float)
    for i, key in enumerate(keys):
        q_log += float(w[i]) * expert_probs[key]
    q_log = q_log / q_log.sum()
    # Preserve a fixed fair uniform floor. This is not fitted to past wins.
    q_log = 0.80 * q_log + 0.20 / N_NUMBERS
    q = (1.0 - BLEND_TO_LOGSCORE) * incumbent_score + BLEND_TO_LOGSCORE * q_log
    q /= q.sum()
    if q.shape != (37,) or not np.all(np.isfinite(q)) or np.any(q <= 0):
        raise RuntimeError("ranking probabilities are invalid")
    return q


def _update_log_score_weights(
    expert_probs: dict[str, np.ndarray],
    keys: list[str],
    previous: np.ndarray,
    observed: np.ndarray,
) -> np.ndarray:
    if len(observed) != PICKS or len(set(observed.tolist())) != PICKS:
        raise RuntimeError("observed draw must contain seven distinct winning numbers")
    centered_log = np.array([
        float(np.mean(np.log(np.maximum(expert_probs[key][observed], 1e-15))))
        + math.log(N_NUMBERS)
        for key in keys
    ], dtype=float)
    return np.clip(
        LOG_DECAY * previous + LOG_ETA * centered_log, -20.0, 20.0
    )


def _metrics(q: np.ndarray, tickets: list[tuple[int, ...]],
             ranking: list[int], observed: np.ndarray) -> dict[str, float]:
    winner = set((observed + 1).tolist())
    portfolio = v2._portfolio_metrics(tickets, winner)
    y = np.zeros(37, dtype=float)
    y[observed] = 1.0 / 7.0
    return {
        "top7_hits": float(len(set(ranking[:7]) & winner)),
        "actual_mass": float(q[observed].sum()),
        "mean_log_actual": float(np.log(q[observed]).mean()),
        "brier": float(np.sum((q - y) ** 2)),
        "uniform_brier": float(np.sum((np.full(37, 1.0 / 37) - y) ** 2)),
        "portfolio_score": float(v3.row_score(portfolio)),
        "max_hits": float(portfolio["max_hits"]),
        "ge3": float(portfolio["ge3"]),
        "ge4": float(portfolio["ge4"]),
    }


def _paired_signflip(delta: list[float], seed: int, reps: int = 4096) -> dict[str, float]:
    """Exploratory paired sign-flip, not an independent promotion p-value."""
    if not delta:
        return {"mean_delta": 0.0, "one_sided_p": 1.0, "n": 0}
    d = np.asarray(delta, dtype=float)
    obs = float(d.mean())
    if obs <= 0:
        return {"mean_delta": obs, "one_sided_p": 1.0, "n": len(d)}
    rng = np.random.default_rng(seed)
    exceed = 0
    remaining = reps
    while remaining:
        batch = min(remaining, 512)
        sample = rng.choice([-1.0, 1.0], size=(batch, len(d)))
        exceed += int(np.sum(np.mean(sample * d, axis=1) >= obs))
        remaining -= batch
    return {"mean_delta": obs, "one_sided_p": (exceed + 1.0) / (reps + 1.0),
            "n": len(d)}


def _summary(rows: list[dict[str, object]], seed: int) -> dict[str, object]:
    score = [float(r["candidate_minus_champion_score"]) for r in rows]
    log = [float(r["candidate_minus_champion_log"]) for r in rows]
    hit = [float(r["candidate_minus_champion_top7"]) for r in rows]
    return {
        "rounds": len(rows),
        "first_round": int(rows[0]["round"]) if rows else None,
        "last_round": int(rows[-1]["round"]) if rows else None,
        "candidate_mean_top7": float(np.mean([r["candidate_top7_hits"] for r in rows])) if rows else None,
        "champion_mean_top7": float(np.mean([r["champion_top7_hits"] for r in rows])) if rows else None,
        "candidate_mean_log_actual": float(np.mean([r["candidate_mean_log_actual"] for r in rows])) if rows else None,
        "champion_mean_log_actual": float(np.mean([r["champion_mean_log_actual"] for r in rows])) if rows else None,
        "candidate_mean_mass": float(np.mean([r["candidate_actual_mass"] for r in rows])) if rows else None,
        "champion_mean_mass": float(np.mean([r["champion_actual_mass"] for r in rows])) if rows else None,
        "candidate_mean_brier": float(np.mean([r["candidate_brier"] for r in rows])) if rows else None,
        "champion_mean_brier": float(np.mean([r["champion_brier"] for r in rows])) if rows else None,
        "candidate_mean_geometry_score": float(np.mean([r["candidate_portfolio_score"] for r in rows])) if rows else None,
        "champion_mean_geometry_score": float(np.mean([r["champion_portfolio_score"] for r in rows])) if rows else None,
        "candidate_ge3_rate": float(np.mean([r["candidate_ge3"] for r in rows])) if rows else None,
        "champion_ge3_rate": float(np.mean([r["champion_ge3"] for r in rows])) if rows else None,
        "top7_paired": _paired_signflip(hit, seed+1),
        "log_paired": _paired_signflip(log, seed+2),
        "portfolio_score_paired": _paired_signflip(score, seed+3),
        "changed_rank_positions_average": float(np.mean([r["rank_positions_changed"] for r in rows])) if rows else None,
    }


def _champion(path: Path) -> v2.ModelConfig:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        cfg = v2.ModelConfig(**obj["config"])
        if obj.get("model_version") != cfg.version():
            raise ValueError("Champion version/config mismatch")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("approved Champion snapshot not available or inconsistent") from exc
    return cfg


def _validate_history(x: np.ndarray, clean) -> None:
    if len(x) <= MIN_TRAIN or x.shape[1] != 37:
        raise ValueError("requires more than 100 complete historical LOTO7 draws")
    if not np.all(np.sum(x, axis=1) == PICKS):
        raise ValueError("each historic draw must contain seven main numbers")
    rounds = []
    for value in clean["回別"]:
        m = re.search(r"\d+", str(value))
        if not m:
            raise ValueError("missing round number")
        rounds.append(int(m.group()))
    if rounds != list(range(1, len(x) + 1)):
        raise ValueError("history must start at round 1 and have no gaps")


def run(*, csv_path: Path, champion_path: Path, out_dir: Path) -> dict[str, object]:
    champ_cfg = _champion(champion_path)
    x, clean = make_history(read_csv_flexible(csv_path))
    _validate_history(x, clean)
    sha = fingerprint_file(csv_path)
    keys = list(expert_probabilities(x[:MIN_TRAIN]))
    champion_logw = np.zeros(len(keys), dtype=float)
    alt_logw = np.zeros(len(keys), dtype=float)
    rounds: list[dict[str, object]] = []
    tickets: list[dict[str, object]] = []

    for t in range(MIN_TRAIN, len(x)):
        history = x[:t]
        experts = expert_probabilities(history)
        # Use the official baseline implementation for strict parity.
        incumbent = v2._score_distribution(history, keys, champion_logw, champ_cfg)
        challenger = _candidate_score(experts, keys, alt_logw, incumbent)
        champion_tickets, champion_rank = ranked_portfolio_from_scores(incumbent)
        candidate_tickets, candidate_rank = ranked_portfolio_from_scores(challenger)

        # Forecasting above must not inspect the target draw until this point.
        observed = np.flatnonzero(x[t])
        champ_m = _metrics(incumbent, champion_tickets, champion_rank, observed)
        cand_m = _metrics(challenger, candidate_tickets, candidate_rank, observed)
        actual_set = set((observed + 1).tolist())
        bonus_numbers = tuple(int(n) for n in re.findall(
            r"\d+", str(clean.iloc[t].get("ボーナス数字", ""))
        ))[:2]
        draw_date = clean.iloc[t]["抽せん日"].date().isoformat()
        rounds.append({
            "round": t + 1, "draw_date": draw_date, "training_rows": t,
            "champion_rank_top7": _fmt(champion_rank[:7]),
            "candidate_rank_top7": _fmt(candidate_rank[:7]),
            "champion_rank_top35": _fmt(champion_rank[:35]),
            "candidate_rank_top35": _fmt(candidate_rank[:35]),
            "champion_excluded_2": _fmt(champion_rank[35:]),
            "candidate_excluded_2": _fmt(candidate_rank[35:]),
            **{f"champion_{k}": v for k, v in champ_m.items()},
            **{f"candidate_{k}": v for k, v in cand_m.items() if k != "uniform_brier"},
            "uniform_brier": champ_m["uniform_brier"],
            "candidate_minus_champion_score":
                cand_m["portfolio_score"] - champ_m["portfolio_score"],
            "candidate_minus_champion_log":
                cand_m["mean_log_actual"] - champ_m["mean_log_actual"],
            "candidate_minus_champion_top7":
                cand_m["top7_hits"] - champ_m["top7_hits"],
            "rank_positions_changed": sum(
                ca != cb for ca, cb in zip(candidate_rank, champion_rank)
            ),
        })
        for model, port in (("champion", champion_tickets), ("candidate", candidate_tickets)):
            for i, ticket in enumerate(port, 1):
                hits, bonus_hits, grade = grade_ticket(ticket, tuple((observed + 1).tolist()),
                                                     bonus_numbers)
                tickets.append({
                    "round": t + 1, "draw_date": draw_date,
                    "model": model, "ticket": i, "predicted_numbers": _fmt(ticket),
                    "actual_main_numbers": _fmt(sorted(actual_set)),
                    "main_hits": hits, "bonus_hits": bonus_hits, "grade": grade,
                })
        champion_logw = v2._update_log_weights(
            history, observed, keys, champion_logw, champ_cfg
        )
        alt_logw = _update_log_score_weights(experts, keys, alt_logw, observed)

    # Train through the latest observed draw for an *unissued research preview*
    # of the next drawing. Does not create a frozen or trusted Future-OOS claim.
    experts = expert_probabilities(x)
    final_champion_q = v2._score_distribution(x, keys, champion_logw, champ_cfg)
    final_candidate_q = _candidate_score(experts, keys, alt_logw, final_champion_q)
    pred_tickets, candidate_rank = ranked_portfolio_from_scores(final_candidate_q)
    champ_tickets, champion_rank = ranked_portfolio_from_scores(final_champion_q)
    log_weights = _stable_weights(alt_logw, LOG_EXPERT_UNIFORM_MIX)
    latest_round = len(x)
    latest_date = clean.iloc[-1]["抽せん日"].date().isoformat()
    identifier_hash = hashlib.sha256(
        json.dumps({"version": VERSION, "champion": champ_cfg.version(),
                    "training_sha256": sha, "scores": [format(float(v), ".17g")
                                                       for v in final_candidate_q]},
                   sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    null = uniform_geometry.exact_disjoint_null()
    bands = {
        "all_101_latest": _summary(rounds, 40_000),
        "recent_120": _summary(rounds[-120:], 41_000),
        "recent_60": _summary(rounds[-60:], 42_000),
    }
    eras = []
    for lo, hi in ((101,250),(251,400),(401,550),(551,10**9)):
        sample = [r for r in rounds if lo <= int(r["round"]) <= hi]
        eras.append({"period": f"{lo}-{hi if hi < 10**9 else latest_round}",
                     "summary": _summary(sample, lo*1000)})
    grades = {
        model: dict(Counter(r["grade"] for r in tickets if r["model"] == model))
        for model in ("champion", "candidate")
    }
    # Historical replay alone NEVER authorizes Production promotion.
    checks = {
        "positive_full_top7_delta":
            bands["all_101_latest"]["top7_paired"]["mean_delta"] > 0,
        "positive_full_mean_log_delta":
            bands["all_101_latest"]["log_paired"]["mean_delta"] > 0,
        "positive_last120_mean_log_delta":
            bands["recent_120"]["log_paired"]["mean_delta"] > 0,
        "positive_last60_mean_log_delta":
            bands["recent_60"]["log_paired"]["mean_delta"] > 0,
        "no_era_log_regression": all(
            e["summary"]["log_paired"]["mean_delta"] >= 0 for e in eras
        ),
        "positive_full_portfolio_delta":
            bands["all_101_latest"]["portfolio_score_paired"]["mean_delta"] > 0,
    }
    report = {
        "version": VERSION,
        "evaluation": "research-only strict prefix replay; retrospective exploratory not future OOS",
        "source_rounds": latest_round, "target_round_first_evaluated": 101,
        "target_round_last_evaluated": latest_round,
        "evaluated_rounds": len(rounds), "evaluated_tickets_per_model": len(rounds)*5,
        "data_sha256": sha, "champion_version": champ_cfg.version(),
        "training": {
            "initial_train_draws": MIN_TRAIN,
            "training_through_round": latest_round,
            "training_through_date": latest_date,
            "method": "online-expert-mean-log-score-vs-uniform-with-exponential-decay",
            "predeclared_fixed_parameters": {
                "learning_rate": LOG_ETA, "decay": LOG_DECAY,
                "expert_uniform_mix": LOG_EXPERT_UNIFORM_MIX,
                "champion_blend": 1.0-BLEND_TO_LOGSCORE,
                "logscore_blend": BLEND_TO_LOGSCORE,
                "candidate_expert_uniform_floor": 0.20,
            },
            "expert_weights": {
                key: float(log_weights[i]) for i,key in enumerate(keys)
            },
        },
        "exact_geometry_matched_uniform_null": null,
        "periods": bands, "eras": eras, "grade_counts": grades,
        "checks": checks,
        "all_retrospective_quality_checks_met": all(checks.values()),
        "promotion_authorized": False,
        "model_automatically_adopted": False,
        "prospective_candidate_registered": False,
        "future_oos_evidence_changed": False,
        "production_changed": False,
        "rank_705_research_preview": {
            "status": "research_only_not_frozen",
            "target_round": latest_round+1,
            "candidate_version": f"{VERSION}+{champ_cfg.version()}",
            "rank_signature_sha256": identifier_hash,
            "ranking_1_to_37": candidate_rank,
            "excluded_numbers": candidate_rank[35:],
            "ranked_tickets": [list(ticket) for ticket in pred_tickets],
            "champion_ranking_1_to_37": champion_rank,
            "champion_tickets": [list(ticket) for ticket in champ_tickets],
            "scores_by_number": [
                {"number": i+1,
                 "candidate_score": float(final_candidate_q[i]),
                 "champion_score": float(final_champion_q[i])}
                for i in range(N_NUMBERS)
            ],
        },
        "limits": [
            "The new model was defined after historical results; retrospective p-values are exploratory.",
            "No future draw outcome was used before its prediction within the replay.",
            "A fair LOTO7 first-prize probability is not increased by ranking.",
            "Research only: no change to Champion or the canonical immutable Production ledger.",
            "A new separately registered and predeclared prospective test is required before any adoption.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "paired_rounds_101_to_latest.csv", rounds, ROUND_FIELDS)
    _write_csv(out_dir / "paired_tickets_101_to_latest.csv", tickets, TICKET_FIELDS)
    (out_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
        encoding="utf-8",
    )
    md = [
        "# 37-number AI prediction ranking retraining — research only",
        "",
        f"- Through: draw #{latest_round} ({latest_date})",
        f"- Baseline: `{champ_cfg.version()}` | candidate: `{VERSION}`",
        f"- Historical strictly preceding draws: {len(rounds)} test draws (101-{latest_round})",
        "- Score: Champion 50% + online mean-log-likelihood expert mixture 50%",
        "- All groups use **exactly the same top-35 disjoint geometry**.",
        "",
        "| Period | Draws | Top7 candidate / Champion | Δ Top7 | Δ log score | Δ geometry score | p(log) exploratory |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in bands.items():
        md.append(f"| {name} | {s['rounds']} | "
                  f"{s['candidate_mean_top7']:.4f} / {s['champion_mean_top7']:.4f} | "
                  f"{s['top7_paired']['mean_delta']:+.4f} | "
                  f"{s['log_paired']['mean_delta']:+.6f} | "
                  f"{s['portfolio_score_paired']['mean_delta']:+.4f} | "
                  f"{s['log_paired']['one_sided_p']:.6f} |")
    md += [
        "",
        f"- Geometry-matched exact fair null composite score: {null['score']:.6f}",
        f"- All retrospective checks passed: **{all(checks.values())}**",
        f"- New research preview next round: **#{latest_round+1}**",
        f"- Candidate ranking: **{_fmt(candidate_rank)}**",
        f"- Candidate excluded numbers: **{_fmt(candidate_rank[35:])}**",
        "- NOT prospectively verified; no Production/Champion change or OOS registration.",
        "",
    ]
    (out_dir / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print("[RETRAIN-RANK] " + json.dumps({
        "data_sha": sha, "source_rounds": latest_round,
        "version": VERSION, "periods": bands, "checks": checks,
        "research_next_rank": candidate_rank, "research_next_tickets": pred_tickets,
        "all_retrospective_quality_checks_met": all(checks.values()),
        "production_changed": False,
    }, ensure_ascii=False, sort_keys=True))
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Research-only re-train and compare ranking signals")
    p.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    p.add_argument("--champion", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    p.add_argument("--out-dir", type=Path, default=Path("research/logscore_rank_retraining"))
    a = p.parse_args()
    run(csv_path=a.csv, champion_path=a.champion, out_dir=a.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
