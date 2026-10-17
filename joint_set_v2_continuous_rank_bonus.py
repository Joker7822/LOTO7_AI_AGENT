#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

import precision_random_baseline as prb
from joint_set_identity_ablation import (
    apply_label_permutation,
    empirical_upper_tail_p,
    label_permutation,
    permute_tickets,
)
from joint_set_v2_model import (
    ForecastBundle,
    N_NUMBERS,
    _sets_to_binary,
    candidate_configs,
    expected_utility_portfolio,
    forecast,
    portfolio_metrics,
    sample_joint_sets,
    utility_from_max_hits,
)
from joint_set_v2_research import (
    bootstrap_ci,
    build_prequential_signal,
    read_precision_rows,
    select_config,
)
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "joint-set-v2-continuous-rank-bonus-v1"
DEFAULT_WEIGHTS = (0.0, 0.02, 0.04, 0.08, 0.12)


def write_json(path: Path, obj: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _stored_v2_scores(path: Path) -> Dict[int, float]:
    out: Dict[int, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["round_index"])] = float(row["portfolio_score"])
    return out


def rank_values(bundle: ForecastBundle) -> np.ndarray:
    """Continuous [0,1] rank percentile from raw v2 number ranking.

    Highest-ranked number receives 1.0 and lowest 0.0. Only ordering is used;
    calibrated probability magnitude and the v2 probability model are unchanged.
    """
    raw = np.asarray(bundle.raw_inclusion_p, dtype=float)
    if raw.shape != (N_NUMBERS,):
        raise ValueError("raw inclusion probabilities must have length 37")
    order = np.argsort(raw)[::-1]
    values = np.zeros(N_NUMBERS, dtype=float)
    for rank, idx in enumerate(order):
        values[int(idx)] = 1.0 - float(rank) / float(N_NUMBERS - 1)
    return values


def _candidate_rank_scores(candidate_sets: np.ndarray, values: np.ndarray) -> np.ndarray:
    arr = np.asarray(candidate_sets, dtype=int)
    v = np.asarray(values, dtype=float)
    return np.asarray([float(np.mean(v[row - 1])) for row in arr], dtype=float)


def _objective(
    hits: np.ndarray,
    selected: Sequence[int],
    rank_scores: np.ndarray,
    weight: float,
) -> float:
    if not selected:
        return 0.0
    max_hits = np.max(hits[:, list(selected)], axis=1)
    scenario_value = float(np.mean(utility_from_max_hits(max_hits)))
    rank_value = float(np.mean(rank_scores[list(selected)]))
    return scenario_value + float(weight) * rank_value


def _optimize_weight(
    candidate_sets: np.ndarray,
    hits: np.ndarray,
    rank_scores: np.ndarray,
    weight: float,
    n_tickets: int = 5,
    local_passes: int = 2,
) -> Tuple[List[Tuple[int, ...]], Dict[str, float]]:
    if len(candidate_sets) < int(n_tickets):
        raise RuntimeError("too few candidate tickets")
    selected: List[int] = []
    current = np.zeros(hits.shape[0], dtype=np.int8)
    for _ in range(int(n_tickets)):
        best_idx = -1
        best_value = -1e100
        for j in range(len(candidate_sets)):
            if j in selected:
                continue
            new_max = np.maximum(current, hits[:, j])
            scenario_value = float(np.mean(utility_from_max_hits(new_max)))
            candidate_selection = selected + [j]
            rank_value = float(np.mean(rank_scores[candidate_selection]))
            value = scenario_value + float(weight) * rank_value
            if value > best_value:
                best_value = value
                best_idx = j
        selected.append(best_idx)
        current = np.maximum(current, hits[:, best_idx])

    for _ in range(max(0, int(local_passes))):
        improved = False
        for pos in range(len(selected)):
            keep = selected[:pos] + selected[pos + 1:]
            base = np.max(hits[:, keep], axis=1) if keep else np.zeros(hits.shape[0], dtype=np.int8)
            old_idx = selected[pos]
            old_scenario = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, old_idx]))))
            old_rank = float(np.mean(rank_scores[keep + [old_idx]]))
            best_idx = old_idx
            best_value = old_scenario + float(weight) * old_rank
            for j in range(len(candidate_sets)):
                if j in keep:
                    continue
                scenario_value = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, j]))))
                rank_value = float(np.mean(rank_scores[keep + [j]]))
                value = scenario_value + float(weight) * rank_value
                if value > best_value + 1e-12:
                    best_idx = j
                    best_value = value
            if best_idx != old_idx:
                selected[pos] = best_idx
                improved = True
        if not improved:
            break

    final_max = np.max(hits[:, selected], axis=1)
    tickets = [tuple(int(v) for v in candidate_sets[j].tolist()) for j in selected]
    return tickets, {
        "combined_objective": _objective(hits, selected, rank_scores, weight),
        "expected_utility": float(np.mean(utility_from_max_hits(final_max))),
        "expected_max_hits": float(np.mean(final_max)),
        "scenario_ge3": float(np.mean(final_max >= 3)),
        "scenario_ge4": float(np.mean(final_max >= 4)),
        "scenario_ge5": float(np.mean(final_max >= 5)),
        "rank_score": float(np.mean(rank_scores[selected])),
        "scenario_count": float(hits.shape[0]),
        "candidate_count": float(len(candidate_sets)),
        "rank_weight": float(weight),
    }


def build_weight_portfolios(
    bundle: ForecastBundle,
    weights: Sequence[float],
    seed: int,
    scenarios: int = 256,
    candidate_count: int = 64,
    n_tickets: int = 5,
) -> Dict[float, Dict[str, object]]:
    """Build all requested weights from identical scenarios and candidate pool.

    Weight 0 intentionally reproduces expected_utility_portfolio exactly for the
    same seed/scenario/candidate budget.
    """
    scenario_sets = sample_joint_sets(bundle, int(scenarios), seed=int(seed) + 11)
    candidate_draws = sample_joint_sets(
        bundle, max(int(candidate_count) * 8, 512), seed=int(seed) + 29
    )
    unique, counts = np.unique(candidate_draws, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    candidate_sets = unique[order[:min(int(candidate_count), len(unique))]]
    if len(candidate_sets) < int(n_tickets):
        raise RuntimeError("joint sampler produced too few unique candidate tickets")
    scen_bin = _sets_to_binary(scenario_sets)
    cand_bin = _sets_to_binary(candidate_sets)
    hits = scen_bin @ cand_bin.T
    values = rank_values(bundle)
    ranks = _candidate_rank_scores(candidate_sets, values)
    out: Dict[float, Dict[str, object]] = {}
    for weight in weights:
        w = float(weight)
        tickets, diagnostics = _optimize_weight(
            candidate_sets, hits, ranks, w, n_tickets=n_tickets
        )
        out[w] = {"tickets": tickets, "diagnostics": diagnostics}
    return out


def robust_weight_score(deltas: Sequence[float]) -> float:
    values = np.asarray(list(deltas), dtype=float)
    if len(values) < 20:
        return -1e9
    chunks = [x for x in np.array_split(values, 4) if len(x)]
    worst = min(float(x.mean()) for x in chunks)
    return float(values.mean() + 0.25 * worst - 0.10 * values.std())


def select_weight(
    train_scores: Mapping[float, Sequence[float]],
    weights: Sequence[float],
) -> Tuple[float, Dict[str, float]]:
    if 0.0 not in train_scores:
        raise ValueError("baseline weight 0.0 is required")
    base = np.asarray(train_scores[0.0], dtype=float)
    diagnostics: Dict[str, float] = {"0": 0.0}
    ranked: List[Tuple[float, float]] = [(0.0, 0.0)]
    for weight in weights:
        w = float(weight)
        if w == 0.0:
            continue
        values = np.asarray(train_scores[w], dtype=float)
        if len(values) != len(base):
            raise ValueError("all weights must have equal training length")
        score = robust_weight_score(values - base)
        diagnostics[f"{w:g}"] = float(score)
        ranked.append((float(score), w))
    # Prefer the smaller weight on exact ties; baseline wins all non-positive alternatives.
    ranked.sort(key=lambda z: (z[0], -z[1]), reverse=True)
    best_score, best_weight = ranked[0]
    if best_score <= 0.0:
        return 0.0, diagnostics
    return float(best_weight), diagnostics


def _permutation_seed(data_sha: str, replicate: int) -> int:
    payload = f"continuous-rank-holdout|{data_sha}|{int(replicate)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & 0x7FFFFFFF


def holdout_identity_permutation(
    holdout: Sequence[Dict[str, object]],
    data_sha: str,
    reps: int = 4096,
) -> Dict[str, float]:
    if not holdout:
        raise ValueError("holdout must not be empty")
    observed = float(np.mean([float(r["selected_score"]) for r in holdout]))
    null = np.empty(int(reps), dtype=float)
    for replicate in range(int(reps)):
        mapping = label_permutation(_permutation_seed(data_sha, replicate))
        scores: List[float] = []
        for row in holdout:
            tickets = permute_tickets(row["selected_tickets"], mapping)
            actual = set(int(v) for v in row["actual"])
            scores.append(float(portfolio_metrics(tickets, actual)["score"]))
        null[replicate] = float(np.mean(scores))
    return {
        "reps": int(reps),
        "observed": observed,
        "permuted_mean": float(null.mean()),
        "identity_edge": float(observed - null.mean()),
        "permuted_p95": float(np.quantile(null, 0.95)),
        "permuted_p99": float(np.quantile(null, 0.99)),
        "upper_tail_p": empirical_upper_tail_p(null, observed),
    }


def _write_holdout_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fields = [
        "round_index", "selected_config", "rank_weight", "rank_score",
        "selected_score", "unrestricted_score", "random_score",
        "delta_vs_unrestricted", "delta_vs_random", "max_hits", "mean_hits", "ge3", "ge4",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def render_report(summary: Mapping[str, object]) -> str:
    h = summary["holdout"]
    p = summary["identity_permutation"]
    lines = [
        "# Joint Set v2 — Continuous Rank Bonus Outer Time Split",
        "",
        f"- evaluation draws: **{summary['evaluated_rounds']}**",
        f"- train / holdout: **{summary['train_rounds']} / {summary['holdout_rounds']}**",
        f"- predeclared weights: **{summary['weights']}**",
        f"- selected rank weight from train only: **{summary['selected_weight']:.4f}**",
        "- holdout result used for weight selection: **NO**",
        "- Production promotion eligible: **NO**",
        "",
        "## Holdout (last 20 draws, frozen weight)",
        f"- selected score: **{h['mean_score']:.4f}**",
        f"- unrestricted score: **{h['unrestricted_mean_score']:.4f}**",
        f"- random score: **{h['random_mean_score']:.4f}**",
        f"- delta vs unrestricted: **{h['delta_vs_unrestricted']['mean']:+.4f}** "
        f"(95% CI {h['delta_vs_unrestricted']['low95']:+.4f}〜{h['delta_vs_unrestricted']['high95']:+.4f})",
        f"- delta vs random: **{h['delta_vs_random']['mean']:+.4f}** "
        f"(95% CI {h['delta_vs_random']['low95']:+.4f}〜{h['delta_vs_random']['high95']:+.4f})",
        f"- round win rate vs unrestricted: **{h['round_win_rate_vs_unrestricted']*100:.2f}%**",
        f"- mean continuous rank score: **{h['mean_rank_score']:.4f}**",
        "",
        "## Holdout paired number-identity permutation",
        f"- permutations: **{p['reps']}**",
        f"- observed score: **{p['observed']:.4f}**",
        f"- permuted mean: **{p['permuted_mean']:.4f}**",
        f"- identity edge: **{p['identity_edge']:+.4f}**",
        f"- upper-tail p: **{p['upper_tail_p']:.6f}**",
        f"- null p95/p99: **{p['permuted_p95']:.4f} / {p['permuted_p99']:.4f}**",
        "",
        "> rank weight is chosen once from the first 40 evaluation draws and frozen for the final 20.",
        "> This is a historical outer split, not pristine independent Future OOS evidence; the research concept was developed after prior analysis of this dataset family.",
        "",
    ]
    return "\n".join(lines)


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    min_train: int = 100,
    last_n: int = 60,
    train_n: int = 40,
    selection_window: int = 120,
    validation_scenarios: int = 256,
    validation_candidates: int = 64,
    random_reps: int = 4096,
    permutation_reps: int = 4096,
    weights: Sequence[float] = DEFAULT_WEIGHTS,
) -> Dict[str, object]:
    if int(train_n) <= 0 or int(train_n) >= int(last_n):
        raise ValueError("train_n must be between 1 and last_n-1")
    normalized_weights = tuple(float(w) for w in weights)
    if not normalized_weights or 0.0 not in normalized_weights:
        raise ValueError("weights must include 0.0")

    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    configs = candidate_configs()
    preq = {cfg.version(): build_prequential_signal(x, cfg, min_train) for cfg in configs}
    prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_rows = read_precision_rows(out_dir / "precision_random_baseline.csv")
    stored = _stored_v2_scores(out_dir / "joint_set_v2_true_nested.csv")

    eval_start = max(min_train + 30, len(x) - int(last_n))
    train_scores: Dict[float, List[float]] = {w: [] for w in normalized_weights}
    train_means_source: Dict[float, List[float]] = {w: [] for w in normalized_weights}
    holdout_rows: List[Dict[str, object]] = []
    selected_weight: float | None = None
    selection_diagnostics: Dict[str, float] | None = None

    for eval_pos, t in enumerate(range(eval_start, len(x))):
        prior_count = t - min_train
        cfg, _ = select_config(configs, preq, prior_count, selection_window)
        bundle = forecast(x[:t], cfg, preq[cfg.version()][:prior_count])
        seed = 123_000_000 + t * 1009
        requested_weights: Sequence[float]
        if eval_pos < int(train_n):
            requested_weights = normalized_weights
        else:
            if selected_weight is None:
                selected_weight, selection_diagnostics = select_weight(train_scores, normalized_weights)
            requested_weights = (0.0,) if selected_weight == 0.0 else (0.0, selected_weight)

        portfolios = build_weight_portfolios(
            bundle, requested_weights, seed=seed, scenarios=validation_scenarios,
            candidate_count=validation_candidates,
        )
        actual_idx = np.flatnonzero(x[t])
        actual = tuple(int(i + 1) for i in actual_idx.tolist())
        actual_set = set(actual)
        outcomes = {
            w: portfolio_metrics(payload["tickets"], actual_set)
            for w, payload in portfolios.items()
        }
        base_score = float(outcomes[0.0]["score"])
        round_index = t + 1
        if round_index not in stored:
            raise RuntimeError(f"stored v2 strict replay missing round {round_index}")
        if abs(base_score - stored[round_index]) > 1e-10:
            raise RuntimeError(
                f"weight-0 reconstruction mismatch round={round_index}: "
                f"{base_score} != {stored[round_index]}"
            )

        if eval_pos < int(train_n):
            for w in normalized_weights:
                score = float(outcomes[w]["score"])
                train_scores[w].append(score)
                train_means_source[w].append(score)
            if eval_pos == int(train_n) - 1:
                selected_weight, selection_diagnostics = select_weight(train_scores, normalized_weights)
            continue

        assert selected_weight is not None
        chosen = outcomes[selected_weight]
        chosen_payload = portfolios[selected_weight]
        rnd = random_rows.get(round_index)
        if rnd is None:
            raise RuntimeError(f"random baseline missing round {round_index}")
        chosen_score = float(chosen["score"])
        holdout_rows.append({
            "round_index": round_index,
            "selected_config": cfg.version(),
            "rank_weight": float(selected_weight),
            "rank_score": float(chosen_payload["diagnostics"]["rank_score"]),
            "selected_score": chosen_score,
            "unrestricted_score": base_score,
            "random_score": float(rnd["random_score"]),
            "delta_vs_unrestricted": chosen_score - base_score,
            "delta_vs_random": chosen_score - float(rnd["random_score"]),
            "max_hits": float(chosen["max_hits"]),
            "mean_hits": float(chosen["mean_hits"]),
            "ge3": float(chosen["ge3"]),
            "ge4": float(chosen["ge4"]),
            "selected_tickets": [tuple(int(v) for v in ticket) for ticket in chosen_payload["tickets"]],
            "actual": actual,
        })

    if selected_weight is None or selection_diagnostics is None:
        raise RuntimeError("weight selection did not occur")
    holdout_expected = int(last_n) - int(train_n)
    if len(holdout_rows) != holdout_expected:
        raise RuntimeError(f"holdout length mismatch: {len(holdout_rows)} != {holdout_expected}")

    d_unrestricted = [float(r["delta_vs_unrestricted"]) for r in holdout_rows]
    d_random = [float(r["delta_vs_random"]) for r in holdout_rows]
    identity = holdout_identity_permutation(holdout_rows, data_sha, reps=permutation_reps)
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "evaluation_type": "outer_time_split_continuous_rank_bonus_v2",
        "data_sha256": data_sha,
        "evaluated_rounds": int(last_n),
        "train_rounds": int(train_n),
        "holdout_rounds": holdout_expected,
        "weights": [float(w) for w in normalized_weights],
        "selected_weight": float(selected_weight),
        "selection_diagnostics": selection_diagnostics,
        "train_mean_scores": {
            f"{w:g}": float(np.mean(train_means_source[w])) for w in normalized_weights
        },
        "weight_zero_reconstruction_verified": True,
        "holdout": {
            "mean_score": float(np.mean([float(r["selected_score"]) for r in holdout_rows])),
            "unrestricted_mean_score": float(np.mean([float(r["unrestricted_score"]) for r in holdout_rows])),
            "random_mean_score": float(np.mean([float(r["random_score"]) for r in holdout_rows])),
            "delta_vs_unrestricted": bootstrap_ci(d_unrestricted, seed=812731),
            "delta_vs_random": bootstrap_ci(d_random, seed=812749),
            "round_win_rate_vs_unrestricted": float(np.mean([x > 0 for x in d_unrestricted])),
            "mean_rank_score": float(np.mean([float(r["rank_score"]) for r in holdout_rows])),
        },
        "identity_permutation": identity,
        "independent_evidence": False,
        "historical_outer_holdout": True,
        "promotion_eligible": False,
        "leakage_control": (
            "The rank weight is selected once using only the first 40 evaluation outcomes. "
            "The final 20 outcomes are not used to select or change the weight. v2 config selection remains prior-only at every target."
        ),
        "interpretation": (
            "Research-only outer time-split diagnostic. The holdout is structurally untouched by weight selection, "
            "but it is not pristine Future OOS evidence because the research concept was developed after prior analysis of this dataset family."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "joint_set_v2_continuous_rank_bonus_summary.json", summary)
    _write_holdout_rows(out_dir / "joint_set_v2_continuous_rank_bonus_holdout.csv", holdout_rows)
    (out_dir / "joint_set_v2_continuous_rank_bonus_report.md").write_text(
        render_report(summary), encoding="utf-8"
    )
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Research-only v2 continuous rank bonus outer time split")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--train-n", type=int, default=40)
    ap.add_argument("--selection-window", type=int, default=120)
    ap.add_argument("--validation-scenarios", type=int, default=256)
    ap.add_argument("--validation-candidates", type=int, default=64)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--permutation-reps", type=int, default=4096)
    args = ap.parse_args()
    summary = run(
        args.csv, args.out_dir, args.min_train, args.last_n, args.train_n,
        args.selection_window, args.validation_scenarios, args.validation_candidates,
        args.random_reps, args.permutation_reps,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
