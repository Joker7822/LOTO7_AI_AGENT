#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only combination agent for five disjoint ranked-35 tickets.

The approved Champion defines the SAME 35 candidate numbers for both arms.
This separate agent uses only earlier draws to estimate shrunk pair interaction
strengths and greedily swaps numbers BETWEEN tickets, preserving 5x7, no repeats,
and unchanged excluded labels. Never used to overwrite issued predictions.

A fair independent 7/37 draw is exchangeable: every valid five-disjoint-ticket
partition has identical ex-ante prize probabilities. Historical pair affinity
does not establish predictive advantage. Retrospective results are exploratory.
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
from typing import Mapping, Sequence

import numpy as np

import balanced_uniform_portfolio as geometry
import loto7_v2_runner as v2
import loto7_v3_runner as v3
from audit_ledger import grade_ticket
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, read_csv_flexible
from production_ticket_geometry35 import ranked_portfolio_from_scores

VERSION = "research-ranked35-pairwise-combination-agent-v1"
TICKET_FIELDS = (
    "round", "draw_date", "arm", "ticket", "numbers", "main_hits",
    "bonus_hits", "grade", "public_prize_yen", "prefix_sha256",
)
ROUND_FIELDS = (
    "round", "draw_date", "history_rows", "prefix_sha256", "rank_top7",
    "rank_top35", "excluded_two", "baseline_tickets", "agent_tickets",
    "actual_main", "agent_swaps", "agent_objective_gain",
    "baseline_max_hits", "agent_max_hits", "baseline_score", "agent_score",
    "baseline_ge3", "agent_ge3", "baseline_ge4", "agent_ge4",
    "baseline_winners", "agent_winners", "baseline_payout_yen",
    "agent_payout_yen", "baseline_payout_complete", "agent_payout_complete",
    "delta_score", "delta_max_hits", "delta_payout_yen",
)


@dataclass(frozen=True)
class AgentConfig:
    lookback: int = 160
    half_life: float = 60.0
    prior_equivalent_draws: float = 300.0
    max_swaps: int = 18
    min_improvement: float = 1e-12


def _validate_ranking(ranking: Sequence[int]) -> None:
    if len(ranking) != 37 or any(type(n) is not int for n in ranking):
        raise ValueError("ranking requires exactly 37 integer labels")
    if sorted(ranking) != list(range(1, 38)):
        raise ValueError("ranking must contain every number 1..37 once")


def fit_pairwise_edges(history: np.ndarray, cfg: AgentConfig) -> tuple[np.ndarray, dict]:
    """Learn empirical deviations from the known fair-draw pair frequency.

    The prior is centered exactly on P(i,j both drawn) = (7/37)*(6/36).
    Shrinkage accounts for effective exponentially decayed sample size; no
    target-row observations or any model output are accessed here.
    """
    h = np.asarray(history)
    if (h.ndim != 2 or h.shape[1] != 37 or len(h) < 100
            or not np.all((h == 0) | (h == 1))
            or not np.all(h.sum(axis=1) == 7)):
        raise ValueError("combination agent requires at least 100 valid past draws")
    if (cfg.lookback < 100 or cfg.half_life <= 0
            or cfg.prior_equivalent_draws <= 0 or cfg.max_swaps < 0):
        raise ValueError("invalid combination agent training configuration")
    past = h[-cfg.lookback:].astype(float, copy=False)
    ages = np.arange(len(past) - 1, -1, -1, dtype=float)
    weight = np.power(0.5, ages / cfg.half_life)
    n_eff = float(weight.sum() ** 2 / np.sum(weight ** 2))
    posterior_weight = n_eff / (n_eff + cfg.prior_equivalent_draws)
    observed_pair = past.T @ (past * weight[:, None]) / weight.sum()
    fair_pair = (7 * 6) / (37 * 36)
    edge = (observed_pair - fair_pair) * posterior_weight
    edge = 0.5 * (edge + edge.T)
    np.fill_diagonal(edge, 0.0)
    if edge.shape != (37, 37) or not np.all(np.isfinite(edge)):
        raise RuntimeError("non-finite combination agent pair edges")
    return edge, {
        "lookback_used": len(past),
        "effective_sample_size": n_eff,
        "posterior_data_weight": posterior_weight,
        "fair_draw_pair_probability": fair_pair,
        "pair_edge_frobenius_norm": float(np.linalg.norm(edge)),
    }


def pair_objective(groups: np.ndarray, edge: np.ndarray) -> float:
    total = 0.0
    for group in groups:
        square = edge[np.ix_(group, group)]
        total += float(np.triu(square, 1).sum())
    return total


def optimize_partition(
    ranking: Sequence[int], edges: np.ndarray, cfg: AgentConfig,
) -> tuple[list[tuple[int, ...]], dict]:
    """Find bounded positive-gain cross-group swaps with stable tie handling.

    This improves *past-data affinity only*, never proof of future wins.
    """
    _validate_ranking(ranking)
    e = np.asarray(edges, dtype=float)
    if e.shape != (37, 37) or not np.all(np.isfinite(e)):
        raise ValueError("pair matrix must contain finite 37x37 scores")
    if not np.allclose(e, e.T, atol=1e-12, rtol=0):
        raise ValueError("pair matrix must be symmetric")
    if not np.allclose(np.diag(e), 0, atol=1e-12, rtol=0):
        raise ValueError("pair matrix diagonal must be zero")
    if cfg.max_swaps < 0 or cfg.min_improvement < 0:
        raise ValueError("invalid optimizer limits")
    # Positions are rank slots; groups are seven-slot blocks.
    assigned = np.asarray(ranking[:35], dtype=int) - 1
    original = assigned.copy()
    group_ids = np.arange(35) // 7
    pi, pj = np.triu_indices(35, k=1)
    mask = group_ids[pi] != group_ids[pj]
    pi, pj = pi[mask], pj[mask]
    gi, gj = group_ids[pi], group_ids[pj]
    before = pair_objective(original.reshape(5,7), e)
    moves = []
    for _ in range(cfg.max_swaps):
        group_sums = e[:, assigned.reshape(5, 7)].sum(axis=2)
        ai, aj = assigned[pi], assigned[pj]
        # When swapping ai from group gi and aj from group gj:
        # delta = sum over the two affected group-pair edges only.
        deltas = (
            group_sums[aj, gi] - group_sums[ai, gi]
            + group_sums[ai, gj] - group_sums[aj, gj]
            - 2.0 * e[ai, aj]
        )
        best = int(np.argmax(deltas))
        delta = float(deltas[best])
        if delta <= cfg.min_improvement:
            break
        i, j = int(pi[best]), int(pj[best])
        number_i, number_j = int(assigned[i])+1, int(assigned[j])+1
        assigned[i], assigned[j] = assigned[j], assigned[i]
        moves.append({
            "from_group": i // 7 + 1, "to_group": j // 7 + 1,
            "swapped_number_a": number_i, "swapped_number_b": number_j,
            "training_objective_delta": delta,
        })
    after = pair_objective(assigned.reshape(5, 7), e)
    if after + 1e-9 < before:
        raise AssertionError("combination agent decreased its training objective")
    output = [
        tuple(sorted(int(n)+1 for n in group))
        for group in assigned.reshape(5, 7)
    ]
    geometry.validate_portfolio(output)
    if sorted(n for row in output for n in row) != sorted(ranking[:35]):
        raise AssertionError("combination agent changed the selected 35 numbers")
    return output, {
        "training_objective_before": before,
        "training_objective_after": after,
        "training_objective_gain": after-before,
        "swap_count": len(moves),
        "moves": moves,
    }


def candidate_from_history(
    history: np.ndarray, ranking: Sequence[int], cfg: AgentConfig,
) -> tuple[list[tuple[int, ...]], dict]:
    edges, learned = fit_pairwise_edges(history, cfg)
    tickets, optimized = optimize_partition(ranking, edges, cfg)
    return tickets, {**learned, **optimized}


def _numstr(nums: Sequence[int]) -> str:
    return " ".join(f"{int(n):02d}" for n in nums)


def _payout(raw: Mapping[str, object], grade: str) -> int | None:
    if grade == "はずれ":
        return 0
    m = re.fullmatch(r"\s*([0-9,]+)円\s*", str(raw.get(f"{grade}当選金額", "") or ""))
    return int(m.group(1).replace(",", "")) if m else None


def _write_csv(path: Path, data: list[dict], fields: tuple[str,...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def _champion(path: Path) -> v2.ModelConfig:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        cfg = v2.ModelConfig(**obj["config"])
        if obj["model_version"] != cfg.version():
            raise ValueError("mismatched Champion identity")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("valid approved Champion snapshot is required") from exc
    return cfg


def _validate_source(csv_path: Path, source_path: Path,
                     latest_round: int, latest_date: str) -> None:
    try:
        obj = json.loads(source_path.read_text(encoding="utf-8"))
        proven = obj["verification_provenance"]
        latest = obj["latest"]
        ok = (obj["status"] == "ok"
              and obj["verification"] == "verified_two_result_sources"
              and int(latest["round"]) == latest_round
              and latest["date"] == latest_date
              and proven["draw_csv_sha256"] == fingerprint_file(csv_path))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("verified source provenance not available") from exc
    if not ok:
        raise RuntimeError("verified source CSV SHA/round mismatch")


def _paired_signflip(deltas: list[float], seed: int, n: int = 4096) -> dict[str,float]:
    if not deltas:
        return {"mean_delta": 0.0, "one_sided_p": 1.0, "count": 0}
    a = np.asarray(deltas, dtype=float)
    mean = float(a.mean())
    if mean <= 0:
        return {"mean_delta": mean, "one_sided_p": 1.0, "count": len(a)}
    rng = np.random.default_rng(seed)
    hits = 0
    for offset in range(0, n, 512):
        batch = min(n-offset, 512)
        flips = rng.choice(np.array([-1.0,1.0]), size=(batch,len(a)))
        hits += int(np.sum((flips*a).mean(axis=1) >= mean))
    return {"mean_delta": mean, "one_sided_p": (hits+1)/(n+1), "count": len(a)}


def _summary(round_rows: list[dict], ticket_rows: list[dict],
             exact: dict, seed: int) -> dict:
    scores = [float(row["delta_score"]) for row in round_rows]
    maxes = [float(row["delta_max_hits"]) for row in round_rows]
    base = [float(row["baseline_score"]) for row in round_rows]
    candidate = [float(row["agent_score"]) for row in round_rows]
    prizes = {arm: Counter(r["grade"] for r in ticket_rows if r["arm"] == arm)
              for arm in ("baseline", "agent")}
    return {
        "evaluated_rounds": len(round_rows),
        "first_round": int(round_rows[0]["round"]) if round_rows else None,
        "last_round": int(round_rows[-1]["round"]) if round_rows else None,
        "issued_ticket_count_per_arm": len(round_rows)*5,
        "mean_baseline_score": float(np.mean(base)) if base else None,
        "mean_agent_score": float(np.mean(candidate)) if candidate else None,
        "mean_exact_fair_disjoint_score": exact["score"],
        "mean_baseline_max_hits": float(np.mean([r["baseline_max_hits"] for r in round_rows])) if round_rows else None,
        "mean_agent_max_hits": float(np.mean([r["agent_max_hits"] for r in round_rows])) if round_rows else None,
        "mean_baseline_ge3_rate": float(np.mean([r["baseline_ge3"] for r in round_rows])) if round_rows else None,
        "mean_agent_ge3_rate": float(np.mean([r["agent_ge3"] for r in round_rows])) if round_rows else None,
        "mean_baseline_ge4_rate": float(np.mean([r["baseline_ge4"] for r in round_rows])) if round_rows else None,
        "mean_agent_ge4_rate": float(np.mean([r["agent_ge4"] for r in round_rows])) if round_rows else None,
        "paired_score": _paired_signflip(scores, seed),
        "paired_max_hits": _paired_signflip(maxes, seed+1),
        "rounds_agent_better": sum(d > 0 for d in scores),
        "rounds_agent_worse": sum(d < 0 for d in scores),
        "rounds_tied": sum(d == 0 for d in scores),
        "average_training_affinity_gain": float(np.mean(
            [r["agent_objective_gain"] for r in round_rows])) if round_rows else None,
        "average_swaps": float(np.mean([r["agent_swaps"] for r in round_rows])) if round_rows else None,
        "reference_purchase_yen_per_arm": 1500*len(round_rows),
        "baseline_reference_payout_yen_known": sum(int(r["baseline_payout_yen"]) for r in round_rows),
        "agent_reference_payout_yen_known": sum(int(r["agent_payout_yen"]) for r in round_rows),
        "unknown_baseline_payout_rounds": sum(not r["baseline_payout_complete"] for r in round_rows),
        "unknown_agent_payout_rounds": sum(not r["agent_payout_complete"] for r in round_rows),
        "grade_counts": {arm: dict(counts) for arm, counts in prizes.items()},
    }


def run(
    *, csv_path: Path, champion_file: Path, out_dir: Path,
    source_report: Path | None = None,
    config: AgentConfig = AgentConfig(),
) -> dict:
    champ = _champion(champion_file)
    x, clean = make_history(read_csv_flexible(csv_path))
    if len(x) <= 100 or x.shape[1] != 37:
        raise ValueError("not enough complete historical draws")
    if "回別" not in clean.columns:
        raise ValueError("draw round column is required")
    round_ids = []
    for value in clean["回別"]:
        m = re.search(r"\d+", str(value))
        if m is None:
            raise ValueError("missing draw id")
        round_ids.append(int(m.group()))
    if round_ids != list(range(1, len(x)+1)):
        raise ValueError("draw ids must be complete from round 1 without gaps")
    sha = fingerprint_file(csv_path)
    latest_date = clean.iloc[-1]["抽せん日"].date().isoformat()
    if source_report is not None:
        _validate_source(csv_path, source_report, len(x), latest_date)

    expert_keys = list(expert_probabilities(x[:100]))
    champion_logw = np.zeros(len(expert_keys), dtype=float)
    ticket_rows: list[dict] = []
    round_rows: list[dict] = []
    prefix = hashlib.sha256()
    # The completed first hundred rounds are known at the first tested forecast.
    for j in range(100):
        prefix.update(
            (f"{j+1}|{clean.iloc[j]['抽せん日'].date().isoformat()}|"
             f"{_numstr((np.flatnonzero(x[j])+1).tolist())}\n").encode("utf-8")
        )
    for t in range(100, len(x)):
        hist = x[:t]  # Target row is deliberately inaccessible to fit/predict.
        q = v2._score_distribution(hist, expert_keys, champion_logw, champ)
        baseline, ranking = ranked_portfolio_from_scores(q)
        agent, agent_meta = candidate_from_history(hist, ranking, config)
        # Both arms use the exact SAME 35 labels, only partitions differ.
        if sorted(n for part in agent for n in part) != sorted(ranking[:35]):
            raise AssertionError("combination agent changed ranked35 selection")

        actual_idx = np.flatnonzero(x[t])
        actual = tuple(int(i) + 1 for i in actual_idx)
        actual_set = set(actual)
        raw = clean.iloc[t]
        bonus = tuple(int(n) for n in re.findall(
            r"\d+", str(raw.get("ボーナス数字", "") or "")
        ))[:2]
        date = raw["抽せん日"].date().isoformat()
        per_arm = {}
        for arm, tickets in (("baseline", baseline), ("agent", agent)):
            metric = v2._portfolio_metrics(tickets, actual_set)
            score = float(v3.row_score(metric))
            wins = 0
            payout = 0
            complete = True
            for index, ticket in enumerate(tickets, 1):
                hits, bonus_hits, grade = grade_ticket(ticket, actual, bonus)
                prize = _payout(raw, grade)
                if prize is None:
                    complete = False
                else:
                    payout += prize
                wins += grade != "はずれ"
                ticket_rows.append({
                    "round": t+1, "draw_date": date, "arm": arm,
                    "ticket": index, "numbers": _numstr(ticket),
                    "main_hits": hits, "bonus_hits": bonus_hits,
                    "grade": grade,
                    "public_prize_yen": prize if prize is not None else "unavailable",
                    "prefix_sha256": prefix.hexdigest(),
                })
            per_arm[arm] = {
                "metric": metric, "score": score, "wins": wins,
                "payout": payout, "payout_complete": complete,
            }
        b, a = per_arm["baseline"], per_arm["agent"]
        round_rows.append({
            "round": t+1, "draw_date": date, "history_rows": t,
            "prefix_sha256": prefix.hexdigest(),
            "rank_top7": _numstr(ranking[:7]),
            "rank_top35": _numstr(ranking[:35]),
            "excluded_two": _numstr(ranking[35:]),
            "baseline_tickets": "|".join(_numstr(p) for p in baseline),
            "agent_tickets": "|".join(_numstr(p) for p in agent),
            "actual_main": _numstr(sorted(actual)),
            "agent_swaps": agent_meta["swap_count"],
            "agent_objective_gain": agent_meta["training_objective_gain"],
            "baseline_max_hits": b["metric"]["max_hits"],
            "agent_max_hits": a["metric"]["max_hits"],
            "baseline_score": b["score"], "agent_score": a["score"],
            "baseline_ge3": b["metric"]["ge3"], "agent_ge3": a["metric"]["ge3"],
            "baseline_ge4": b["metric"]["ge4"], "agent_ge4": a["metric"]["ge4"],
            "baseline_winners": b["wins"], "agent_winners": a["wins"],
            "baseline_payout_yen": b["payout"], "agent_payout_yen": a["payout"],
            "baseline_payout_complete": b["payout_complete"],
            "agent_payout_complete": a["payout_complete"],
            "delta_score": a["score"]-b["score"],
            "delta_max_hits": a["metric"]["max_hits"]-b["metric"]["max_hits"],
            "delta_payout_yen": a["payout"]-b["payout"],
        })
        # Only after observing #t+1 can its draw affect future model state.
        champion_logw = v2._update_log_weights(
            hist, actual_idx, expert_keys, champion_logw, champ)
        prefix.update(
            (f"{t+1}|{date}|{_numstr(sorted(actual))}\n").encode("utf-8")
        )

    # Research-only next-round ranking/portfolio proposals. No issuer writes.
    incumbent_q = v2._score_distribution(x, expert_keys, champion_logw, champ)
    incumbent_tickets, latest_rank = ranked_portfolio_from_scores(incumbent_q)
    proposed_tickets, proposed_meta = candidate_from_history(x, latest_rank, config)
    exact = geometry.exact_disjoint_null()
    periods = {
        "all_101_latest": _summary(round_rows, ticket_rows, exact, 1001),
        "recent_120": _summary(round_rows[-120:],
                                [r for r in ticket_rows if int(r["round"]) > len(x)-120],
                                exact, 1002),
        "recent_60": _summary(round_rows[-60:],
                               [r for r in ticket_rows if int(r["round"]) > len(x)-60],
                               exact, 1003),
    }
    eras = [
        {
            "period": f"{lo}-{min(hi, len(x))}",
            "summary": _summary(
                [r for r in round_rows if lo <= int(r["round"]) <= hi],
                [r for r in ticket_rows if lo <= int(r["round"]) <= hi],
                exact, lo*1009,
            ),
        }
        for lo, hi in ((101,250),(251,400),(401,550),(551,10**9))
    ]
    checks = {
        "positive_full_mean_score":
            periods["all_101_latest"]["paired_score"]["mean_delta"] > 0,
        "positive_recent120_mean_score":
            periods["recent_120"]["paired_score"]["mean_delta"] > 0,
        "positive_recent60_mean_score":
            periods["recent_60"]["paired_score"]["mean_delta"] > 0,
        "no_material_era_regression": all(
            row["summary"]["paired_score"]["mean_delta"] >= -0.02
            for row in eras
        ),
        "full_score_signflip_one_sided_p_below_0_05_exploratory":
            periods["all_101_latest"]["paired_score"]["one_sided_p"] < 0.05,
    }
    result = {
        "report_version": VERSION,
        "evaluation_type": "research_only_prequential_prefix_pairwise_retraining_retrospective",
        "champion_version": champ.version(),
        "champion_config": asdict(champ),
        "data_sha256": sha,
        "source_rounds": len(x),
        "source_latest_draw_date": latest_date,
        "source_trust": (
            "verified_two_result_sources" if source_report is not None
            else "not_checked_synthetic_test"
        ),
        "first_evaluated_round": 101,
        "last_evaluated_round": len(x),
        "evaluated_rounds": len(round_rows),
        "agent_config": asdict(config),
        "exact_fair_disjoint_null": exact,
        "periods": periods,
        "eras": eras,
        "exploratory_checks": checks,
        "retrospective_checks_all_met": all(checks.values()),
        "research_next_round_preview": {
            "target_round": len(x)+1,
            "status": "unissued_research_only",
            "top35_ranked_numbers": latest_rank[:35],
            "excluded_bottom_two": latest_rank[35:],
            "existing_contiguous_tickets": [list(t) for t in incumbent_tickets],
            "agent_tickets": [list(t) for t in proposed_tickets],
            "agent_training_diagnostics": proposed_meta,
        },
        "production_ledger_modified": False,
        "champion_modified": False,
        "prospective_registry_modified": False,
        "promotion_authorized": False,
        "fair_draw_interpretation": (
            "Under a fair exchangeable seven-of-37 lottery every partition "
            "of the same 35 distinct labels into five seven-number tickets "
            "has the same exact first-prize and lower-tier event probabilities. "
            "Historical pairwise co-occurrence has no established predictive skill."
        ),
        "limitations": [
            "This agent was developed after observing historical data, so exploratory replay results are not future OOS evidence.",
            "The training objective always improves by construction and cannot be counted as held-out predictive success.",
            "No attempt is made to select a policy based on the target's actual winning numbers.",
            "The fair-draw prize probabilities are invariant under ticket re-partitioning.",
            "No candidate is registered into the formal frozen prospective OOS study.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "paired_rounds_101_to_latest.csv", round_rows, ROUND_FIELDS)
    _write_csv(out_dir / "paired_tickets_101_to_latest.csv", ticket_rows, TICKET_FIELDS)
    (out_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
        encoding="utf-8",
    )
    report = [
        "# Combination AI agent for ranked35 non-overlapping tickets — Research",
        "",
        f"- Through round: **#{len(x)} ({latest_date})** | Champion: `{champ.version()}`",
        f"- Strict chronological prequential rounds: **101–{len(x)}**, draws **{len(round_rows)}**",
        "- Ranking and top35 fixed between arms; only number-to-ticket assignment differs.",
        "- Agent: historical pair-frequency interaction, exponential recency weighting, strong shrinkage to fair null, bounded cross-ticket local swaps.",
        "- Pair optimization objective on training history is not a statistical performance claim.",
        "- All ranked35 five-ticket portfolios have identical *fair-draw* theoretical prize probabilities.",
        "",
        "| Period | Draws | Baseline score | Agent score | Δ score | Paired one-sided p (exploratory) | Agent 3+ | Baseline 3+ | Mean swaps |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, part in periods.items():
        report.append(
            f"| {name} | {part['evaluated_rounds']} | "
            f"{part['mean_baseline_score']:.4f} | {part['mean_agent_score']:.4f} | "
            f"{part['paired_score']['mean_delta']:+.4f} | "
            f"{part['paired_score']['one_sided_p']:.6f} | "
            f"{part['mean_agent_ge3_rate']*100:.2f}% | "
            f"{part['mean_baseline_ge3_rate']*100:.2f}% | "
            f"{part['average_swaps']:.2f} |"
        )
    report += [
        "",
        f"- Exact geometry-matched fair-draw mean score: **{exact['score']:.6f}**",
        f"- Exact geometry-matched fair-draw 3+ rate: **{100*exact['ge3']:.4f}%**",
        f"- All exploratory checks met: **{all(checks.values())}**",
        f"- Research preview target: **#{len(x)+1}**",
        f"- Agent preview: **{json.dumps(result['research_next_round_preview']['agent_tickets'])}**",
        "- No auto-promotions, model changes, issued prediction replacement, or prospective freeze.",
        "",
    ]
    (out_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("[COMBINATION-AGENT] "+json.dumps({
        "source_rounds": len(x), "data_sha": sha,
        "candidate": VERSION, "periods": periods,
        "checks": checks, "preview": result["research_next_round_preview"],
        "production_ledger_modified": False,
    }, ensure_ascii=False, sort_keys=True))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Research-only ranked35 combination agent")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--champion", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--source-validation", type=Path,
                    default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--out-dir", type=Path, default=Path("research/combination_agent35_output"))
    args = ap.parse_args()
    run(csv_path=args.csv, champion_file=args.champion,
        source_report=args.source_validation, out_dir=args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
