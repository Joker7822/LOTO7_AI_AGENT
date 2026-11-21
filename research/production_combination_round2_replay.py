#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only historical replay of Production Champion-ranked disjoint35.

Every target is scored using exclusively preceding draw rows. This script
never modifies canonical Production predictions, Champion, or Future-OOS data.

Rounds 2-20: insufficient observations for expert_probabilities (uniform tie).
Rounds 21-100: equal-weight experts, untrained cold-start *not* Production AI.
Rounds 101+: fixed approved Champion config, prequential online Hedge updates.
The model definition was selected later than much of this historical sample;
this retrospective replay is NOT independently registered future OOS evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
from audit_ledger import grade_ticket
from loto7_evolving_agent import (
    N_NUMBERS, PICKS, RANDOM_HIT_MEAN, expert_probabilities, final_score,
    fingerprint_file, make_history, read_csv_flexible, walk_forward_evolve,
)
from production_ticket_geometry35 import ranked_portfolio_from_scores
from combination_agent35_core import AgentConfig, candidate_from_history

VERSION = "production-combination-agent-historical-round2-v1"
PHASE_LABELS = {
    "uniform_cold_start": "2..20: 20 draws not yet available (no AI signal)",
    "untrained_expert_cold_start": "21..100: expert scores but no Hedge learning",
    "approved_champion_online": "101+: fixed Champion, strictly preceding draws",
}
TICKET_FIELDS = (
    "round", "draw_date", "training_rows", "phase", "arm", "ticket",
    "ranking_positions", "predicted_numbers", "actual_main_numbers",
    "actual_bonus_numbers", "main_hits", "bonus_hits", "grade",
    "public_prize_amount", "source_prefix_sha256", "rank_sha256",
)
ROUND_FIELDS = (
    "round", "draw_date", "training_rows", "phase", "rank_1_to_7",
    "rank_1_to_35", "excluded_rank_36_37", "source_prefix_sha256", "rank_sha256", "top7_hits",
    "max_hits", "mean_ticket_hits", "ge3", "ge4", "portfolio_score",
    "matched_ensemble32_score", "score_delta_vs_matched32",
    "winning_tickets", "public_payout_yen", "public_payout_complete",
    "baseline_score", "baseline_max_hits", "baseline_ge3", "baseline_ge4",
    "baseline_winning_tickets", "baseline_payout_yen", "baseline_payout_complete",
    "score_delta_vs_rank_order", "combo_swaps", "combo_training_gain",
    "combination_phase", "baseline_tickets", "combo_tickets",
)


def _write_csv(path: Path, rows: Iterable[Mapping[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _numbers(items: Iterable[int]) -> str:
    return " ".join(f"{int(number):02d}" for number in sorted(items))


def _prize_payout(row: Mapping[str, object], grade: str) -> int | None:
    if grade == "はずれ":
        return 0
    value = str(row.get(f"{grade}当選金額", "") or "")
    # Only explicit public amounts are usable. Never infer missing prizes.
    matches = re.fullmatch(r"\s*([\d,]+)\s*円\s*", value)
    return int(matches.group(1).replace(",", "")) if matches else None


def exact_disjoint_score_null() -> dict[str, float]:
    """Exact score moments for five disjoint blocks of seven and two omitted.

    Fair 7-of-37 null: C(2, omitted) * product C(7, hits_in_block).
    Independent of how a non-anticipating model labels/groups its tickets.
    """
    n = math.comb(N_NUMBERS, PICKS)
    mass = 0
    score_sum = 0.0
    score_sumsq = 0.0
    max_sum = 0.0
    ge3_sum = 0.0
    ge4_sum = 0.0
    for hits in itertools.product(range(PICKS + 1), repeat=5):
        omitted = PICKS - sum(hits)
        if not 0 <= omitted <= 2:
            continue
        weight = math.comb(2, omitted)
        for hit in hits:
            weight *= math.comb(7, hit)
        maximum = max(hits)
        ge3 = int(maximum >= 3)
        ge4 = int(maximum >= 4)
        mean_hit = sum(hits) / 5.0
        score = maximum + 0.35 * ge3 + 0.75 * ge4 + 0.10 * mean_hit
        mass += weight
        score_sum += weight * score
        score_sumsq += weight * score * score
        max_sum += weight * maximum
        ge3_sum += weight * ge3
        ge4_sum += weight * ge4
    if mass != n:
        raise AssertionError("exact disjoint fair-draw null lost probability mass")
    expected = score_sum / mass
    return {
        "universe_size": n,
        "score_mean": expected,
        "score_variance": max(0.0, score_sumsq / mass - expected * expected),
        "max_hits_mean": max_sum / mass,
        "ge3_probability": ge3_sum / mass,
        "ge4_probability": ge4_sum / mass,
        "top7_hits_mean": RANDOM_HIT_MEAN,
        "top7_hits_variance": (PICKS * (PICKS / N_NUMBERS)
                               * (1.0 - PICKS / N_NUMBERS)
                               * ((N_NUMBERS - PICKS) / (N_NUMBERS - 1))),
        "any_first_prize_probability": 5 / n,
    }


def _test_stat(values: list[float], null_mean: float, null_variance: float) -> dict[str, float | int | str]:
    if not values:
        return {"count": 0, "mean": 0.0, "delta": 0.0, "approx_two_sided_p": 1.0,
                "method": "no_data"}
    mean = float(np.mean(values))
    se = math.sqrt(null_variance / len(values))
    z = (mean - null_mean) / se if se > 0 else 0.0
    return {
        "count": len(values), "mean": mean, "null_mean": null_mean,
        "delta": mean - null_mean, "z": z,
        "approx_two_sided_p": math.erfc(abs(z) / math.sqrt(2.0)),
        "method": "two_sided_normal_approx_under_independent_fair_draws_exploratory",
    }


def _phase_summary(round_rows: list[dict[str, object]], exact: dict[str, float]) -> dict[str, object]:
    scores = [float(row["portfolio_score"]) for row in round_rows]
    baseline_scores = [float(row["baseline_score"]) for row in round_rows]
    top_hits = [float(row["top7_hits"]) for row in round_rows]
    matches = [float(row["matched_ensemble32_score"]) for row in round_rows]
    deltas = [a-b for a,b in zip(scores, matches)]
    return {
        "round_count": len(round_rows),
        "baseline_mean_score": float(np.mean(baseline_scores)) if round_rows else 0.0,
        "combination_minus_rank_order_score": float(np.mean(
            [float(r["score_delta_vs_rank_order"]) for r in round_rows])) if round_rows else 0.0,
        "baseline_ge3_rate": float(np.mean([int(r["baseline_ge3"]) for r in round_rows])) if round_rows else 0.0,
        "baseline_payout_yen": sum(int(r["baseline_payout_yen"]) for r in round_rows),
        "baseline_payout_complete": all(bool(r["baseline_payout_complete"]) for r in round_rows),
        "mean_agent_swaps": float(np.mean([int(r["combo_swaps"]) for r in round_rows])) if round_rows else 0.0,
        "ticket_count": len(round_rows)*5,
        "first_round": int(round_rows[0]["round"]) if round_rows else None,
        "last_round": int(round_rows[-1]["round"]) if round_rows else None,
        "top7": _test_stat(top_hits, exact["top7_hits_mean"], exact["top7_hits_variance"]),
        "portfolio_score": _test_stat(scores, exact["score_mean"], exact["score_variance"]),
        "average_max_hits": float(np.mean([int(r["max_hits"]) for r in round_rows])) if round_rows else None,
        "exact_null_average_max_hits": exact["max_hits_mean"],
        "rounds_with_ge3": sum(int(r["ge3"]) for r in round_rows),
        "ge3_rate": float(np.mean([int(r["ge3"]) for r in round_rows])) if round_rows else None,
        "exact_null_ge3_rate": exact["ge3_probability"],
        "rounds_with_ge4": sum(int(r["ge4"]) for r in round_rows),
        "ge4_rate": float(np.mean([int(r["ge4"]) for r in round_rows])) if round_rows else None,
        "exact_null_ge4_rate": exact["ge4_probability"],
        "mean_matched_ensemble32_score": float(np.mean(matches)) if matches else None,
        "mean_delta_vs_matched_ensemble32": float(np.mean(deltas)) if deltas else None,
        "rounds_outperforming_matched_ensemble32": sum(delta > 0 for delta in deltas),
        "rounds_with_any_prize": sum(int(r["winning_tickets"]) > 0 for r in round_rows),
        "public_prize_amount_known_all_rounds": all(bool(r["public_payout_complete"]) for r in round_rows),
        "reference_purchase_cost_yen": 5 * 300 * len(round_rows),
        "public_payout_sum_yen_when_known": sum(int(r["public_payout_yen"]) for r in round_rows),
        "missing_payout_rounds": sum(not bool(r["public_payout_complete"]) for r in round_rows),
    }


def _matched_scores(actual_set: set[int], round_number: int, reps: int) -> float:
    """Pre-seeded geometry-matched fair controls; seed never reads drawn numbers."""
    rng = np.random.default_rng(42_000_000 + int(round_number)*104729)
    scores = []
    for _ in range(reps):
        shuffled = rng.permutation(37) + 1
        tickets = [tuple(int(v) for v in shuffled[i:i+7]) for i in range(0, 35, 7)]
        metrics = v2._portfolio_metrics(tickets, actual_set)
        scores.append(float(v3.row_score(metrics)))
    return float(np.mean(scores))


def _read_champion(path: Path) -> v2.ModelConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        config = v2.ModelConfig(**payload["config"])
        if payload["model_version"] != config.version():
            raise ValueError("approved Champion ID does not match its configuration")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("research replay requires a valid explicit approved Champion snapshot") from exc
    return config


def _verify_parity(history: np.ndarray, config: v2.ModelConfig, snapshots: dict[int, np.ndarray],
                   min_train: int) -> None:
    """Compare incremental scoring to the slow official Champion implementation."""
    for t, predicted in sorted(snapshots.items()):
        bt = walk_forward_evolve(
            history[:t], min_train=min_train, eta=config.eta,
            decay=config.decay, expert_uniform_mix=config.expert_uniform_mix,
        )
        reference = final_score(history[:t], bt, uniform_mix=config.final_uniform_mix)
        if not np.allclose(predicted, reference, atol=1e-12, rtol=0):
            raise AssertionError(f"Champion parity mismatch for target round {t+1}")


def run(*, csv_path: Path, champion_file: Path, out_dir: Path,
        min_train: int = 100, matched_reps: int = 32,
        verify_parity: bool = True) -> dict[str, object]:
    if min_train != 100:
        raise ValueError("this reproducible replay uses the approved Champion min_train=100 policy")
    if matched_reps < 1:
        raise ValueError("matched_reps must be positive")
    config = _read_champion(champion_file)
    history, clean = make_history(read_csv_flexible(csv_path))
    if len(history) <= min_train or len(history) < 2:
        raise RuntimeError("not enough draws to replay fixed Champion from round 2")
    # Fail closed if the input is a truncated or non-contiguous history.
    numbers = []
    for i, row in clean.iterrows():
        digits = re.search(r"\d+", str(row.get("回別", "")))
        if not digits:
            raise RuntimeError("missing draw-round identifier")
        numbers.append(int(digits.group()))
    if numbers != list(range(1, len(numbers) + 1)):
        raise RuntimeError("history must contain contiguous chronological rounds starting with 1")

    data_sha = fingerprint_file(csv_path)
    champion_version = config.version()
    round_rows: list[dict[str, object]] = []
    ticket_rows: list[dict[str, object]] = []
    keys: list[str] | None = None
    logw: np.ndarray | None = None
    parity_snapshots: dict[int, np.ndarray] = {}
    prefix_hash = hashlib.sha256()
    for t in range(1, len(history)):
        # The prefix hash itself must not include future rows, either.
        previous = clean.iloc[t - 1]
        prior_date = previous["抽せん日"].date().isoformat()
        prior_main = _numbers(np.flatnonzero(history[t - 1]) + 1)
        prior_bonus = str(previous.get("ボーナス数字", ""))
        prefix_hash.update(
            f"{t}|{prior_date}|{prior_main}|{prior_bonus}\n".encode("utf-8")
        )
        source_prefix_sha = prefix_hash.hexdigest()
        target_round = t + 1
        if t < 20:
            phase = "uniform_cold_start"
            q = np.full(N_NUMBERS, 1.0 / N_NUMBERS, dtype=float)
        else:
            if keys is None:
                # The first 20 results are used only after draw 20 has occurred.
                keys = list(expert_probabilities(history[:20]))
                logw = np.zeros(len(keys), dtype=float)
            assert logw is not None
            phase = ("untrained_expert_cold_start" if t < min_train
                     else "approved_champion_online")
            q = v2._score_distribution(history[:t], keys, logw, config)
            if t in {min_train + 1, min_train + 2, len(history)-1}:
                parity_snapshots[t] = q.copy()

        baseline_tickets, ranking = ranked_portfolio_from_scores(q)
        if t >= min_train:
            tickets, combo_diag = candidate_from_history(history[:t], ranking, AgentConfig())
            combo_phase = "trained_pairwise_combination"
        else:
            # Explicit cold-start; no learned pairwise model before round 101.
            tickets = baseline_tickets
            combo_diag = {"swap_count": 0, "training_objective_gain": 0.0}
            combo_phase = "not_trainable_fallback_rank_order"
        if len(tickets) != 5 or len(set(n for ticket in tickets for n in ticket)) != 35:
            raise AssertionError("ranked portfolio disjoint35 invariant failed")
        frozen_rank = ",".join(str(x) for x in ranking)
        rank_sha = hashlib.sha256(
            f"{champion_version}|{source_prefix_sha}|{target_round}|{frozen_rank}".encode("utf-8")
        ).hexdigest()
        # Target drawn numbers must not be accessed until predictions are frozen.
        actual_main = tuple(int(n) for n in (np.flatnonzero(history[t]) + 1).tolist())
        actual_set = set(actual_main)
        raw = clean.iloc[t]
        draw_date = raw["抽せん日"].date().isoformat()
        bonus = tuple(int(n) for n in re.findall(r"\d+", str(raw.get("ボーナス数字", ""))))[:2]
        metrics = v2._portfolio_metrics(tickets, actual_set)
        baseline_metrics = v2._portfolio_metrics(baseline_tickets, actual_set)
        baseline_score = float(v3.row_score(baseline_metrics))
        score = float(v3.row_score(metrics))
        matched_score = _matched_scores(actual_set, target_round, matched_reps)
        payout = 0
        complete = True
        wins = 0
        baseline_payout = 0
        baseline_complete = True
        baseline_wins = 0
        for arm, arm_tickets in (("combination", tickets), ("rank_order", baseline_tickets)):
            for i, ticket in enumerate(arm_tickets, 1):
                main_hits, bonus_hits, grade = grade_ticket(ticket, actual_main, bonus)
                amount = _prize_payout(raw, grade)
                if arm == "combination":
                    if amount is None:
                        complete = False
                    else:
                        payout += amount
                    wins += grade != "はずれ"
                else:
                    if amount is None:
                        baseline_complete = False
                    else:
                        baseline_payout += amount
                    baseline_wins += grade != "はずれ"
                ticket_rows.append({
                    "round": target_round, "draw_date": draw_date,
                    "training_rows": t, "phase": phase, "arm": arm, "ticket": i,
                    "ranking_positions": (
                        f"{(i-1)*7+1}-{i*7}" if arm == "rank_order"
                        else "reallocated" if t >= min_train else "cold_start_contiguous"
                    ),
                    "predicted_numbers": _numbers(ticket),
                    "actual_main_numbers": _numbers(actual_main),
                    "actual_bonus_numbers": _numbers(bonus),
                    "main_hits": main_hits, "bonus_hits": bonus_hits,
                    "grade": grade,
                    "public_prize_amount": f"{amount}円" if amount is not None else "確認できません",
                    "source_prefix_sha256": source_prefix_sha,
                    "rank_sha256": rank_sha,
                })
        round_rows.append({
            "round": target_round, "draw_date": draw_date,
            "training_rows": t, "phase": phase,
            "rank_1_to_7": _numbers(ranking[:7]),
            "rank_1_to_35": " ".join(f"{v:02d}" for v in ranking[:35]),
            "excluded_rank_36_37": " ".join(f"{v:02d}" for v in ranking[35:]),
            "source_prefix_sha256": source_prefix_sha,
            "rank_sha256": rank_sha, "top7_hits": len(set(ranking[:7]) & actual_set),
            "max_hits": int(metrics["max_hits"]), "mean_ticket_hits": float(metrics["mean_hits"]),
            "ge3": int(metrics["ge3"]), "ge4": int(metrics["ge4"]),
            "portfolio_score": score, "matched_ensemble32_score": matched_score,
            "score_delta_vs_matched32": score - matched_score,
            "winning_tickets": wins, "public_payout_yen": payout,
            "public_payout_complete": complete,
            "baseline_score": baseline_score,
            "baseline_max_hits": int(baseline_metrics["max_hits"]),
            "baseline_ge3": int(baseline_metrics["ge3"]),
            "baseline_ge4": int(baseline_metrics["ge4"]),
            "baseline_winning_tickets": baseline_wins,
            "baseline_payout_yen": baseline_payout,
            "baseline_payout_complete": baseline_complete,
            "score_delta_vs_rank_order": score - baseline_score,
            "combo_swaps": combo_diag["swap_count"],
            "combo_training_gain": combo_diag["training_objective_gain"],
            "combination_phase": combo_phase,
            "baseline_tickets": "|".join(_numbers(tick) for tick in baseline_tickets),
            "combo_tickets": "|".join(_numbers(tick) for tick in tickets),
        })
        # The newly observed draw updates ONLY subsequent targets (#102 onwards).
        if t >= min_train:
            assert keys is not None and logw is not None
            logw = v2._update_log_weights(history[:t], np.flatnonzero(history[t]),
                                          keys, logw, config)

    if verify_parity:
        _verify_parity(history, config, parity_snapshots, min_train)
    exact = exact_disjoint_score_null()
    groups = {
        "all_rounds_2_plus": round_rows,
        "uniform_cold_start_2_20": [r for r in round_rows if r["phase"] == "uniform_cold_start"],
        "untrained_expert_21_100": [r for r in round_rows if r["phase"] == "untrained_expert_cold_start"],
        "approved_champion_101_plus": [r for r in round_rows if r["phase"] == "approved_champion_online"],
    }
    summaries = {key: _phase_summary(rows, exact) for key, rows in groups.items()}
    grades = Counter(str(r["grade"]) for r in ticket_rows if r["arm"] == "combination")
    baseline_grades = Counter(str(r["grade"]) for r in ticket_rows if r["arm"] == "rank_order")
    summary: dict[str, Any] = {
        "report_version": VERSION,
        "evaluation_type": "research_only_retrospective_strict_prefix_walk_forward_not_future_oos",
        "model_version": champion_version,
        "model_config": asdict(config),
        "target_round_first": 2,
        "target_round_last": len(history),
        "data_sha256": data_sha,
        "source_rows": len(history),
        "matched_null_members_per_round": matched_reps,
        "exact_fair_draw_null": exact,
        "phases": PHASE_LABELS,
        "results": summaries,
        "prize_grade_counts_all": dict(sorted(grades.items())),
        "rank_order_grade_counts_all": dict(sorted(baseline_grades.items())),
        "evaluated_combination_tickets": len(round_rows)*5,
        "evaluated_baseline_tickets": len(round_rows)*5,
        "total_ticket_rows": len(ticket_rows),
        "combination_agent_version": "production-ai-ranked35-pairwise-combination-v1",
        "combination_agent_config": asdict(AgentConfig()),
        "pairwise_training_available_from_round": 101,
        "cold_start_fallback_rounds": 99,
        "next_target_retrained_preview": { },
        "champion_parity_verified": verify_parity,
        "champion_parity_target_rounds": sorted(t+1 for t in parity_snapshots) if verify_parity else [],
        "observed_outcomes_used_only_after_each_prediction": True,
        "research_only": True,
        "issued_predictions_changed": False,
        "promotion_authorized_by_replay": False,
        "champion_changed": False,
        "future_oos_evidence_changed": False,
        "limitations": [
            "Round 2-20 has no AI scores; rank ties are broken by ascending label.",
            "Round 21-100 uses untrained experts and cannot be counted as trained Champion skill.",
            "Combination AI is not trainable until 100 prior draws, so rounds 2-100 use unchanged rank-order layout.",
            "Same exact 35-number set used in both replay arms; the learned agent only reassigns 7-number blocks.",
            "Champion hyperparameters were approved after much of this sample: model choice can be retrospective.",
            "Approximate p-values are exploratory fair-draw null tests, not preregistered future OOS proof.",
            "The model's 35-number geometry changes lower-tier coverage, not the 1st prize odds.",
            "Prize payouts are hypothetical historical returns; no ticket purchase is asserted.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "rounds_2_to_latest.csv", round_rows, ROUND_FIELDS)
    _write_csv(out_dir / "tickets_2_to_latest.csv", ticket_rows, TICKET_FIELDS)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    def phase_md(name: str) -> str:
        result = summaries[name]
        t = result["top7"]
        score = result["portfolio_score"]
        return (
            f"| {name} | {result['round_count']} | "
            f"{t['mean']:.4f} | {t['approx_two_sided_p']:.5f} | "
            f"{result['average_max_hits']:.4f} | "
            f"{score['mean']:.4f} | {result['combination_minus_rank_order_score']:+.4f} | "
            f"{score['approx_two_sided_p']:.5f} | "
            f"{result['ge3_rate']*100:.2f}% | "
            f"{result['mean_delta_vs_matched_ensemble32']:+.4f} |"
        )
    cols = "| Sample | Draws | Top7 hits | Top7 p | Max hits | Combo score | Δ combo vs rank-order | Score p vs fair | GE3 | Δ vs matched32 |"
    md = [
        "# Production-ranked35 pairwise combination AI: retrospective replay from round 2",
        "",
        f"- Draws: **#2–#{len(history)}**; historical source SHA-256: `{data_sha}`",
        f"- Champion: **`{champion_version}`** (fixed configuration)",
        "- Actual draw for each round is consulted only AFTER the ranked ticket combinations are frozen in memory.",
        "- Five pairwise-disjoint 7-number tickets, preserving the same Champion top35; trained pairwise rearrangement from round 101 onward.",
        "- Round 2-100: fallback to rank-order arrangement, explicitly NOT trained combination AI.",
        "- Ranks 36-37 are excluded. This is a research replay, not replacement of frozen original Production predictions.",
        "- Exact matched null: analytical 5-disjoint-7 with 2 excluded, not five independent random tickets.",
        "- Additionally compare with 32 seeded geometry-matched random portfolios per target.",
        "- No model selection or tuning based on this replay. This is NOT independent future OOS validation.",
        "",
        cols, "|"+"|".join("---" for _ in cols.split("|")[1:-1])+"|",
    ] + [phase_md(k) for k in groups] + [
        "",
        f"- Exact fair-draw score null mean: **{exact['score_mean']:.6f}**, SD: **{math.sqrt(exact['score_variance']):.6f}**",
        f"- Exact fair-draw 3+ ticket event: **{exact['ge3_probability']*100:.3f}%**",
        f"- Combination prize grades: **{json.dumps(summary['prize_grade_counts_all'], ensure_ascii=False)}**",
        f"- Rank-order prize grades: **{json.dumps(summary['rank_order_grade_counts_all'], ensure_ascii=False)}**",
        f"- Combination payout / assumed cost: **{summaries['all_rounds_2_plus']['public_payout_sum_yen_when_known']} / {summaries['all_rounds_2_plus']['reference_purchase_cost_yen']} JPY**",
        f"- Rank-order payout: **{summaries['all_rounds_2_plus']['baseline_payout_yen']} JPY**",
        f"- Trained combination #101+ score difference vs rank-order: **{summaries['approved_champion_101_plus']['combination_minus_rank_order_score']:+.6f}**",
        f"- Payout completeness (both arms): **{summaries['all_rounds_2_plus']['public_prize_amount_known_all_rounds'] and summaries['all_rounds_2_plus']['baseline_payout_complete']}**",
        "- Initial rounds #2-20 are uniform; #21-100 are untrained startup. Do not count as verified trained-AI skill.",
        "- Reporting dates refer to historical draw dates. The replay was implemented in November 2026.",
        "",
    ]
    (out_dir / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print("[RANKED35-REPLAY] " + json.dumps({
        "report_version": VERSION,
        "csv_sha": data_sha,
        "last_round": len(history),
        "results": summaries,
        "grades": dict(grades),
        "parity_target_rounds": summary["champion_parity_target_rounds"],
        "baseline_grades": dict(baseline_grades),
    }, ensure_ascii=False, sort_keys=True))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay trained production combination AI from LOTO7 round 2 (research only)")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--champion", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--out-dir", type=Path, default=Path("research/production_combination_round2_replay"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--matched-reps", type=int, default=32)
    ap.add_argument("--skip-parity", action="store_true")
    args = ap.parse_args()
    run(csv_path=args.csv, champion_file=args.champion, out_dir=args.out_dir,
        min_train=args.min_train, matched_reps=args.matched_reps,
        verify_parity=not args.skip_parity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
