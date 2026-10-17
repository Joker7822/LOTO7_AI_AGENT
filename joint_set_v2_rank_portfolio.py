#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from joint_set_v2_model import (
    ForecastBundle,
    _sets_to_binary,
    bernoulli_signal_metrics,
    candidate_configs,
    forecast,
    portfolio_metrics,
    sample_joint_sets,
    utility_from_max_hits,
)
from joint_set_v2_research import (
    bootstrap_ci,
    build_prequential_signal,
    parse_round,
    read_precision_rows,
    select_config,
)
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
import precision_random_baseline as prb

REPORT_VERSION = "joint-set-v2-rank-aware-portfolio-v1"


@dataclass(frozen=True)
class RankPolicy:
    name: str
    min_top7_per_ticket: int = 0
    min_top10_per_ticket: int = 0


def candidate_policies() -> List[RankPolicy]:
    """Small predeclared exposure family. Never selected using the target result."""
    return [
        RankPolicy("unrestricted", 0, 0),
        RankPolicy("top10-ge2", 0, 2),
        RankPolicy("top7-ge2", 2, 2),
        RankPolicy("top7-ge2-top10-ge3", 2, 3),
        RankPolicy("top7-ge3", 3, 3),
    ]


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _rank_sets(bundle: ForecastBundle) -> Tuple[set[int], set[int]]:
    order = np.argsort(np.asarray(bundle.raw_inclusion_p, dtype=float))[::-1]
    top7 = set(int(i) + 1 for i in order[:7])
    top10 = set(int(i) + 1 for i in order[:10])
    return top7, top10


def _eligible_indices(
    candidate_sets: np.ndarray,
    policy: RankPolicy,
    top7: set[int],
    top10: set[int],
    limit: int,
) -> List[int]:
    eligible: List[int] = []
    for j, row in enumerate(candidate_sets):
        values = set(int(v) for v in row.tolist())
        if len(values & top7) < int(policy.min_top7_per_ticket):
            continue
        if len(values & top10) < int(policy.min_top10_per_ticket):
            continue
        eligible.append(j)
        if len(eligible) >= int(limit):
            break
    return eligible


def _optimize_from_hits(
    candidate_sets: np.ndarray,
    hits: np.ndarray,
    eligible: Sequence[int],
    scenario_count: int,
    n_tickets: int = 5,
    local_passes: int = 2,
) -> Tuple[List[Tuple[int, ...]], Dict[str, float]]:
    choices = [int(j) for j in eligible]
    if len(choices) < int(n_tickets):
        raise ValueError("too few eligible tickets for policy")
    selected: List[int] = []
    current = np.zeros(int(scenario_count), dtype=np.int8)
    for _ in range(int(n_tickets)):
        best_idx = -1
        best_value = -1e100
        for j in choices:
            if j in selected:
                continue
            value = float(np.mean(utility_from_max_hits(np.maximum(current, hits[:, j]))))
            if value > best_value:
                best_value = value
                best_idx = j
        selected.append(best_idx)
        current = np.maximum(current, hits[:, best_idx])

    for _ in range(max(0, int(local_passes))):
        improved = False
        for pos in range(len(selected)):
            keep = selected[:pos] + selected[pos + 1:]
            base = np.max(hits[:, keep], axis=1) if keep else np.zeros(int(scenario_count), dtype=np.int8)
            old = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, selected[pos]]))))
            best_idx, best_value = selected[pos], old
            for j in choices:
                if j in keep:
                    continue
                value = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, j]))))
                if value > best_value + 1e-12:
                    best_idx, best_value = j, value
            if best_idx != selected[pos]:
                selected[pos] = best_idx
                improved = True
        if not improved:
            break

    final_max = np.max(hits[:, selected], axis=1)
    tickets = [tuple(int(v) for v in candidate_sets[j].tolist()) for j in selected]
    return tickets, {
        "expected_utility": float(np.mean(utility_from_max_hits(final_max))),
        "expected_max_hits": float(np.mean(final_max)),
        "scenario_ge3": float(np.mean(final_max >= 3)),
        "scenario_ge4": float(np.mean(final_max >= 4)),
        "scenario_ge5": float(np.mean(final_max >= 5)),
        "scenario_count": float(scenario_count),
        "eligible_candidate_count": float(len(choices)),
    }


def build_policy_portfolios(
    bundle: ForecastBundle,
    policies: Sequence[RankPolicy],
    seed: int,
    scenarios: int = 256,
    candidate_count: int = 64,
    n_tickets: int = 5,
) -> Dict[str, Dict[str, object]]:
    """Construct all policies from the same scenarios/candidate draws.

    The unrestricted policy intentionally reproduces joint_set_v2_model.expected_utility_portfolio
    for the same seed/scenario/candidate budget. Restricted policies filter the full unique candidate
    pool before taking up to candidate_count candidates.
    """
    scenario_sets = sample_joint_sets(bundle, int(scenarios), seed=int(seed) + 11)
    candidate_draws = sample_joint_sets(
        bundle, max(int(candidate_count) * 8, 512), seed=int(seed) + 29
    )
    unique, counts = np.unique(candidate_draws, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    candidate_sets = unique[order]
    if len(candidate_sets) < int(n_tickets):
        raise RuntimeError("joint sampler produced too few unique candidate tickets")

    scen_bin = _sets_to_binary(scenario_sets)
    cand_bin = _sets_to_binary(candidate_sets)
    hits = scen_bin @ cand_bin.T
    top7, top10 = _rank_sets(bundle)
    out: Dict[str, Dict[str, object]] = {}
    for policy in policies:
        eligible = _eligible_indices(candidate_sets, policy, top7, top10, int(candidate_count))
        if len(eligible) < int(n_tickets):
            continue
        tickets, diag = _optimize_from_hits(
            candidate_sets, hits, eligible, len(scenario_sets), n_tickets=n_tickets
        )
        total_slots = max(1, int(n_tickets) * 7)
        top7_slots = sum(len(set(ticket) & top7) for ticket in tickets)
        top10_slots = sum(len(set(ticket) & top10) for ticket in tickets)
        diag.update({
            "top7_slot_rate": float(top7_slots / total_slots),
            "top10_slot_rate": float(top10_slots / total_slots),
            "top7_slots": float(top7_slots),
            "top10_slots": float(top10_slots),
        })
        out[policy.name] = {
            "policy": asdict(policy),
            "tickets": tickets,
            "diagnostics": diag,
        }
    if "unrestricted" not in out:
        raise RuntimeError("unrestricted policy unavailable")
    return out


def robust_policy_score(rows: Sequence[Dict[str, float]], window: int = 120) -> float:
    recent = list(rows[-max(30, int(window)):])
    if len(recent) < 30:
        return -1e9
    values = np.asarray([float(r["delta_vs_unrestricted"]) for r in recent], dtype=float)
    chunks = [x for x in np.array_split(values, 3) if len(x)]
    worst = min(float(x.mean()) for x in chunks)
    return float(values.mean() + 0.25 * worst - 0.10 * values.std())


def select_policy(
    policies: Sequence[RankPolicy],
    histories: Dict[str, List[Dict[str, float]]],
    available: Sequence[str],
    selection_window: int = 120,
) -> Tuple[RankPolicy, float]:
    allowed = set(str(x) for x in available)
    ranked: List[Tuple[float, str, RankPolicy]] = []
    for policy in policies:
        if policy.name not in allowed:
            continue
        score = 0.0 if policy.name == "unrestricted" else robust_policy_score(
            histories.get(policy.name, []), selection_window
        )
        ranked.append((float(score), policy.name, policy))
    if not ranked:
        raise RuntimeError("no available rank policy")
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ranked[0][2], float(ranked[0][0])


def _stored_v2_scores(path: Path) -> Dict[int, float]:
    out: Dict[int, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["round_index"])] = float(row["portfolio_score"])
    return out


def _write_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fields = [
        "round_index", "selected_config", "selected_policy", "selected_policy_prior_score",
        "signal_top7_hits", "base_score", "selected_score", "random_score",
        "delta_vs_unrestricted", "delta_vs_random", "max_hits", "mean_hits", "ge3", "ge4",
        "top7_slot_rate", "top10_slot_rate", "available_policy_count",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def render_report(summary: Dict[str, object]) -> str:
    p = summary["portfolio"]
    lines = [
        "# Joint Set v2 — Strict Nested Rank-Aware Portfolio",
        "",
        f"- evaluated rounds: **{summary['evaluated_rounds']}**",
        f"- predeclared policies: **{summary['predeclared_policy_count']}**",
        f"- policy selection window: **{summary['policy_selection_window']}** prior draws",
        "- target result used before policy selection: **NO**",
        "- Production promotion eligible: **NO**",
        "",
        "## Strict selected policy",
        f"- mean score: **{p['mean_score']:.4f}**",
        f"- unrestricted mean score: **{p['unrestricted_mean_score']:.4f}**",
        f"- random mean score: **{p['random_mean_score']:.4f}**",
        f"- delta vs unrestricted: **{p['delta_vs_unrestricted']['mean']:+.4f}** "
        f"(95% CI {p['delta_vs_unrestricted']['low95']:+.4f}〜{p['delta_vs_unrestricted']['high95']:+.4f})",
        f"- delta vs random: **{p['delta_vs_random']['mean']:+.4f}** "
        f"(95% CI {p['delta_vs_random']['low95']:+.4f}〜{p['delta_vs_random']['high95']:+.4f})",
        f"- round win rate vs unrestricted: **{p['round_win_rate_vs_unrestricted']*100:.2f}%**",
        f"- mean Top7 slot exposure: **{p['mean_top7_slot_rate']*100:.2f}%**",
        f"- mean Top10 slot exposure: **{p['mean_top10_slot_rate']*100:.2f}%**",
        "",
        "## Selected policy counts",
    ]
    for name, count in sorted(summary["selected_policy_counts"].items()):
        lines.append(f"- {name}: **{count}**")
    lines += [
        "",
        "> policyは各targetの結果を見る前に、過去のunrestrictedとの差だけで選択します。",
        "> Research-only。historical diagnosticであり、Future OOSやProduction昇格証拠ではありません。",
        "",
    ]
    return "\n".join(lines)


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    min_train: int = 100,
    last_n: int = 60,
    config_selection_window: int = 120,
    policy_selection_window: int = 120,
    validation_scenarios: int = 256,
    validation_candidates: int = 64,
    random_reps: int = 4096,
) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    configs = candidate_configs()
    policies = candidate_policies()
    preq = {cfg.version(): build_prequential_signal(x, cfg, min_train) for cfg in configs}
    prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_rows = read_precision_rows(out_dir / "precision_random_baseline.csv")
    stored = _stored_v2_scores(out_dir / "joint_set_v2_true_nested.csv")

    eval_start = max(min_train + 30, len(x) - int(last_n))
    policy_start = max(min_train + 30, eval_start - int(policy_selection_window))
    histories: Dict[str, List[Dict[str, float]]] = {p.name: [] for p in policies}
    rows: List[Dict[str, object]] = []
    all_eval_policy_scores: Dict[str, List[float]] = {p.name: [] for p in policies}

    for t in range(policy_start, len(x)):
        prior_count = t - min_train
        cfg, _ = select_config(configs, preq, prior_count, config_selection_window)
        bundle = forecast(x[:t], cfg, preq[cfg.version()][:prior_count])
        seed = 123_000_000 + t * 1009
        portfolios = build_policy_portfolios(
            bundle, policies, seed=seed, scenarios=validation_scenarios,
            candidate_count=validation_candidates,
        )
        available = list(portfolios)
        selected_policy, selected_prior_score = select_policy(
            policies, histories, available, policy_selection_window
        )
        actual_idx = np.flatnonzero(x[t])
        actual_set = set((actual_idx + 1).tolist())
        signal = bernoulli_signal_metrics(bundle.inclusion_p, actual_idx)

        outcomes: Dict[str, Dict[str, float]] = {}
        for name, payload in portfolios.items():
            metrics = portfolio_metrics(payload["tickets"], actual_set)
            outcomes[name] = metrics
        base_score = float(outcomes["unrestricted"]["score"])

        if t >= eval_start:
            round_index = t + 1
            if round_index not in stored:
                raise RuntimeError(f"stored v2 strict replay missing round {round_index}")
            if abs(base_score - stored[round_index]) > 1e-10:
                raise RuntimeError(
                    f"unrestricted reconstruction mismatch round={round_index}: "
                    f"{base_score} != {stored[round_index]}"
                )
            selected = outcomes[selected_policy.name]
            diag = portfolios[selected_policy.name]["diagnostics"]
            rnd = random_rows.get(round_index)
            if rnd is None:
                raise RuntimeError(f"random baseline missing round {round_index}")
            row = {
                "round_index": round_index,
                "selected_config": cfg.version(),
                "selected_policy": selected_policy.name,
                "selected_policy_prior_score": selected_prior_score,
                "signal_top7_hits": float(signal["top7_hits"]),
                "base_score": base_score,
                "selected_score": float(selected["score"]),
                "random_score": float(rnd["random_score"]),
                "delta_vs_unrestricted": float(selected["score"] - base_score),
                "delta_vs_random": float(selected["score"] - rnd["random_score"]),
                "max_hits": float(selected["max_hits"]),
                "mean_hits": float(selected["mean_hits"]),
                "ge3": float(selected["ge3"]),
                "ge4": float(selected["ge4"]),
                "top7_slot_rate": float(diag["top7_slot_rate"]),
                "top10_slot_rate": float(diag["top10_slot_rate"]),
                "available_policy_count": len(available),
            }
            rows.append(row)
            for name, metrics in outcomes.items():
                all_eval_policy_scores[name].append(float(metrics["score"]))

        # Update histories only after all choices for this target have been frozen/evaluated.
        for name, metrics in outcomes.items():
            histories[name].append({
                "delta_vs_unrestricted": float(metrics["score"] - base_score),
                "portfolio_score": float(metrics["score"]),
            })

    deltas_base = [float(r["delta_vs_unrestricted"]) for r in rows]
    deltas_random = [float(r["delta_vs_random"]) for r in rows]
    selected_counts = Counter(str(r["selected_policy"]) for r in rows)
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "evaluation_type": "strict_prior_only_rank_aware_portfolio_policy_selection",
        "data_sha256": data_sha,
        "evaluated_rounds": len(rows),
        "predeclared_policy_count": len(policies),
        "policies": [asdict(p) for p in policies],
        "policy_selection_window": int(policy_selection_window),
        "config_selection_window": int(config_selection_window),
        "selected_policy_counts": dict(selected_counts),
        "portfolio": {
            "mean_score": float(np.mean([float(r["selected_score"]) for r in rows])) if rows else 0.0,
            "unrestricted_mean_score": float(np.mean([float(r["base_score"]) for r in rows])) if rows else 0.0,
            "random_mean_score": float(np.mean([float(r["random_score"]) for r in rows])) if rows else 0.0,
            "delta_vs_unrestricted": bootstrap_ci(deltas_base, seed=7351901),
            "delta_vs_random": bootstrap_ci(deltas_random, seed=7351902),
            "round_win_rate_vs_unrestricted": float(np.mean([d > 0 for d in deltas_base])) if deltas_base else 0.0,
            "mean_top7_slot_rate": float(np.mean([float(r["top7_slot_rate"]) for r in rows])) if rows else 0.0,
            "mean_top10_slot_rate": float(np.mean([float(r["top10_slot_rate"]) for r in rows])) if rows else 0.0,
        },
        "policy_eval_means": {
            name: (float(np.mean(values)) if values else None)
            for name, values in all_eval_policy_scores.items()
        },
        "unrestricted_reconstruction_verified": True,
        "independent_evidence": False,
        "promotion_eligible": False,
        "leakage_control": (
            "At target t, v2 config selection and rank-policy selection use only outcomes before t. "
            "Current target rank exposure is derived only from the prior-only forecast bundle."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "joint_set_v2_rank_portfolio_summary.json", summary)
    _write_rows(out_dir / "joint_set_v2_rank_portfolio.csv", rows)
    (out_dir / "joint_set_v2_rank_portfolio_report.md").write_text(
        render_report(summary), encoding="utf-8"
    )

    # Current research-only candidate. This does not retroactively become Future OOS evidence.
    target_t = len(x)
    cfg, _ = select_config(configs, preq, target_t - min_train, config_selection_window)
    bundle = forecast(x, cfg, preq[cfg.version()])
    target_round = parse_round(clean["回別"].iloc[-1] if "回別" in clean.columns else len(clean), len(clean)) + 1
    portfolios = build_policy_portfolios(
        bundle, policies, seed=123_000_000 + target_t * 1009,
        scenarios=validation_scenarios, candidate_count=validation_candidates,
    )
    current_policy, current_policy_score = select_policy(
        policies, histories, list(portfolios), policy_selection_window
    )
    payload = portfolios[current_policy.name]
    current = {
        "report_version": "joint-set-v2-rank-aware-current-v1",
        "data_sha256": data_sha,
        "target_round": int(target_round),
        "selected_config": cfg.version(),
        "selected_policy": current_policy.name,
        "selected_policy_prior_score": float(current_policy_score),
        "policy": payload["policy"],
        "portfolio_diagnostics": payload["diagnostics"],
        "tickets": [[int(v) for v in ticket] for ticket in payload["tickets"]],
        "research_only": True,
        "promotion_eligible": False,
        "future_oos_evidence": False,
    }
    write_json(out_dir / "joint_set_v2_rank_portfolio_current.json", current)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict nested rank-aware portfolio research for Joint Set v2")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--config-selection-window", type=int, default=120)
    ap.add_argument("--policy-selection-window", type=int, default=120)
    ap.add_argument("--validation-scenarios", type=int, default=256)
    ap.add_argument("--validation-candidates", type=int, default=64)
    ap.add_argument("--random-reps", type=int, default=4096)
    args = ap.parse_args()
    summary = run(
        args.csv, args.out_dir, args.min_train, args.last_n,
        args.config_selection_window, args.policy_selection_window,
        args.validation_scenarios, args.validation_candidates, args.random_reps,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
