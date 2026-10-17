#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

import joint_set_research as v1_research
import joint_set_v2_research as v2_research
from joint_set_model import (
    candidate_configs as v1_candidate_configs,
    expected_utility_portfolio as v1_expected_utility_portfolio,
    forecast as v1_forecast,
    portfolio_metrics as v1_portfolio_metrics,
)
from joint_set_v2_model import (
    candidate_configs as v2_candidate_configs,
    expected_utility_portfolio as v2_expected_utility_portfolio,
    forecast as v2_forecast,
    portfolio_metrics as v2_portfolio_metrics,
)
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

N_NUMBERS = 37
PICKS = 7
REPORT_VERSION = "joint-set-identity-ablation-v1"


@dataclass(frozen=True)
class ObservedRound:
    round_index: int
    actual: Tuple[int, ...]
    top7: Tuple[int, ...]
    tickets: Tuple[Tuple[int, ...], ...]
    top7_hits: float
    portfolio_score: float


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def label_permutation(seed: int) -> np.ndarray:
    """Return a deterministic 1-based label mapping for numbers 1..37."""
    rng = np.random.default_rng(int(seed))
    labels = np.arange(1, N_NUMBERS + 1, dtype=int)
    rng.shuffle(labels)
    return labels


def apply_label_permutation(values: Sequence[int], mapping: np.ndarray) -> Tuple[int, ...]:
    arr = np.asarray(mapping, dtype=int)
    if arr.shape != (N_NUMBERS,):
        raise ValueError(f"mapping must have shape ({N_NUMBERS},)")
    if set(arr.tolist()) != set(range(1, N_NUMBERS + 1)):
        raise ValueError("mapping must be a permutation of 1..37")
    return tuple(int(arr[int(v) - 1]) for v in values)


def permute_tickets(
    tickets: Sequence[Sequence[int]], mapping: np.ndarray
) -> Tuple[Tuple[int, ...], ...]:
    return tuple(apply_label_permutation(ticket, mapping) for ticket in tickets)


def geometry_signature(tickets: Sequence[Sequence[int]]) -> Dict[str, object]:
    sets = [set(int(n) for n in ticket) for ticket in tickets]
    pair_overlaps: List[int] = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            pair_overlaps.append(len(sets[i] & sets[j]))
    return {
        "ticket_sizes": [len(s) for s in sets],
        "pair_overlaps": pair_overlaps,
        "distinct_numbers": len(set().union(*sets)) if sets else 0,
    }


def _seed(data_sha: str, model: str, replicate: int) -> int:
    payload = f"identity-ablation|{data_sha}|{model}|{int(replicate)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & 0x7FFFFFFF


def _top7_from_signal(signal: np.ndarray) -> Tuple[int, ...]:
    arr = np.asarray(signal, dtype=float)
    if arr.shape != (N_NUMBERS,):
        raise ValueError("signal must contain 37 numbers")
    # Match the research models' np.argsort(...)[-7:] tie-breaking exactly.
    idx = np.argsort(arr)[-PICKS:]
    return tuple(int(i + 1) for i in idx.tolist())


def _round_record(
    t: int,
    actual_idx: np.ndarray,
    top7: Sequence[int],
    tickets: Sequence[Sequence[int]],
    score_fn: Callable[[Sequence[Sequence[int]], set[int]], Dict[str, float]],
) -> ObservedRound:
    actual = tuple(int(i + 1) for i in actual_idx.tolist())
    aset = set(actual)
    top = tuple(int(n) for n in top7)
    frozen_tickets = tuple(tuple(int(n) for n in ticket) for ticket in tickets)
    pm = score_fn(frozen_tickets, aset)
    return ObservedRound(
        round_index=int(t + 1),
        actual=actual,
        top7=top,
        tickets=frozen_tickets,
        top7_hits=float(len(set(top) & aset)),
        portfolio_score=float(pm["score"]),
    )


def build_v1_rounds(
    csv_path: Path,
    out_dir: Path,
    metadata_path: Path,
    cutoff_hour_jst: int = 18,
) -> Tuple[List[ObservedRound], Dict[str, object], str]:
    stored = read_json(out_dir / "joint_set_true_nested_summary.json")
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    if stored.get("data_sha256") != data_sha:
        raise RuntimeError("v1 stored replay does not match current data SHA")

    min_train = int(stored["min_train"])
    last_n = int(stored["last_n"])
    selection_window = int(stored["selection_window"])
    scenarios = int(stored["validation_scenarios"])
    candidates = int(stored["validation_candidates"])

    metadata_design, _, _ = v1_research.prepare_metadata(clean, metadata_path, cutoff_hour_jst)
    configs = v1_candidate_configs()
    preq = {
        cfg.version(): v1_research.build_prequential_signal(x, cfg, min_train, metadata_design)
        for cfg in configs
    }
    eval_start = max(min_train + 30, len(x) - last_n)
    rounds: List[ObservedRound] = []
    for t in range(eval_start, len(x)):
        prior_count = t - min_train
        cfg, _ = v1_research.select_config(configs, preq, prior_count, selection_window)
        md_adj, md_diag = v1_research.metadata_for_target(x, metadata_design, t)
        bundle = v1_forecast(
            x[:t], cfg, preq[cfg.version()][:prior_count], md_adj, md_diag
        )
        tickets, _ = v1_expected_utility_portfolio(
            bundle,
            seed=93_000_000 + t * 1009,
            scenarios=scenarios,
            candidate_count=candidates,
        )
        rounds.append(
            _round_record(
                t, np.flatnonzero(x[t]), _top7_from_signal(bundle.q), tickets,
                v1_portfolio_metrics,
            )
        )
    _verify_reconstruction(rounds, stored, "v1")
    return rounds, stored, data_sha


def build_v2_rounds(
    csv_path: Path,
    out_dir: Path,
) -> Tuple[List[ObservedRound], Dict[str, object], str]:
    stored = read_json(out_dir / "joint_set_v2_true_nested_summary.json")
    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    if stored.get("data_sha256") != data_sha:
        raise RuntimeError("v2 stored replay does not match current data SHA")

    min_train = int(stored["min_train"])
    last_n = int(stored["last_n"])
    selection_window = int(stored["selection_window"])
    scenarios = int(stored["validation_scenarios"])
    candidates = int(stored["validation_candidates"])

    configs = v2_candidate_configs()
    preq = {
        cfg.version(): v2_research.build_prequential_signal(x, cfg, min_train)
        for cfg in configs
    }
    eval_start = max(min_train + 30, len(x) - last_n)
    rounds: List[ObservedRound] = []
    for t in range(eval_start, len(x)):
        prior_count = t - min_train
        cfg, _ = v2_research.select_config(configs, preq, prior_count, selection_window)
        bundle = v2_forecast(x[:t], cfg, preq[cfg.version()][:prior_count])
        tickets, _ = v2_expected_utility_portfolio(
            bundle,
            seed=123_000_000 + t * 1009,
            scenarios=scenarios,
            candidate_count=candidates,
        )
        rounds.append(
            _round_record(
                t, np.flatnonzero(x[t]), _top7_from_signal(bundle.inclusion_p), tickets,
                v2_portfolio_metrics,
            )
        )
    _verify_reconstruction(rounds, stored, "v2")
    return rounds, stored, data_sha


def _verify_reconstruction(
    rounds: Sequence[ObservedRound], stored: Mapping[str, object], model: str
) -> None:
    if not rounds:
        raise RuntimeError(f"{model} reconstruction produced no evaluated rounds")
    expected_rounds = int(stored["evaluated_rounds"])
    if len(rounds) != expected_rounds:
        raise RuntimeError(
            f"{model} evaluated round mismatch: rebuilt={len(rounds)} stored={expected_rounds}"
        )
    observed_top7 = float(np.mean([r.top7_hits for r in rounds]))
    observed_score = float(np.mean([r.portfolio_score for r in rounds]))
    expected_top7 = float(stored["signal"]["mean_top7_hits"])
    expected_score = float(stored["portfolio"]["mean_score"])
    if not np.isclose(observed_top7, expected_top7, rtol=0.0, atol=1e-12):
        raise RuntimeError(
            f"{model} Top7 reconstruction mismatch: rebuilt={observed_top7} stored={expected_top7}"
        )
    if not np.isclose(observed_score, expected_score, rtol=0.0, atol=1e-12):
        raise RuntimeError(
            f"{model} portfolio reconstruction mismatch: rebuilt={observed_score} stored={expected_score}"
        )


def empirical_upper_tail_p(null_values: np.ndarray, observed: float) -> float:
    values = np.asarray(null_values, dtype=float)
    if values.size == 0:
        raise ValueError("null_values must not be empty")
    return float((1 + np.count_nonzero(values >= float(observed))) / (len(values) + 1))


def _metric_summary(null_values: np.ndarray, observed: float) -> Dict[str, float]:
    arr = np.asarray(null_values, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return {
        "observed": float(observed),
        "permuted_mean": mean,
        "identity_edge": float(observed - mean),
        "permuted_median": float(np.median(arr)),
        "permuted_p95": float(np.quantile(arr, 0.95)),
        "permuted_p99": float(np.quantile(arr, 0.99)),
        "permuted_sd": sd,
        "identity_z": float((observed - mean) / sd) if sd > 1e-15 else 0.0,
        "empirical_upper_tail_p": empirical_upper_tail_p(arr, observed),
    }


def permutation_test(
    rounds: Sequence[ObservedRound],
    model: str,
    data_sha: str,
    permutations: int,
    score_fn: Callable[[Sequence[Sequence[int]], set[int]], Dict[str, float]],
) -> Dict[str, object]:
    if int(permutations) < 99:
        raise ValueError("permutations must be at least 99")
    if not rounds:
        raise ValueError("rounds must not be empty")

    observed_top7 = float(np.mean([r.top7_hits for r in rounds]))
    observed_score = float(np.mean([r.portfolio_score for r in rounds]))
    null_top7 = np.empty(int(permutations), dtype=float)
    null_score = np.empty(int(permutations), dtype=float)

    # A single global 1..37 relabeling is used across all evaluated rounds in
    # each replicate. This preserves cross-round ticket identity frequencies,
    # exact five-ticket overlap geometry, config selection, and optimization;
    # only alignment between predicted number identities and future outcomes is destroyed.
    for rep in range(int(permutations)):
        mapping = label_permutation(_seed(data_sha, model, rep))
        top_hits = 0.0
        scores = 0.0
        for row in rounds:
            aset = set(row.actual)
            perm_top = apply_label_permutation(row.top7, mapping)
            perm_tickets = permute_tickets(row.tickets, mapping)
            top_hits += float(len(set(perm_top) & aset))
            scores += float(score_fn(perm_tickets, aset)["score"])
        null_top7[rep] = top_hits / len(rounds)
        null_score[rep] = scores / len(rounds)

    return {
        "model": model,
        "evaluated_rounds": len(rounds),
        "permutations": int(permutations),
        "reconstruction_verified": True,
        "control": (
            "global 1..37 label permutation of the exact observed Top7 and five-ticket portfolios; "
            "portfolio geometry and cross-round ticket identity frequencies are preserved"
        ),
        "top7_hits": _metric_summary(null_top7, observed_top7),
        "portfolio_score": _metric_summary(null_score, observed_score),
    }


def render_report(summary: Mapping[str, object]) -> str:
    lines = [
        "# Joint Set Number-Identity Ablation",
        "",
        f"- evaluated draws/model: **{summary['evaluated_rounds']}**",
        f"- global label permutations/model: **{summary['permutations']}**",
        "- target result used before portfolio construction: **NO**",
        "- Production promotion eligible: **NO**",
        "",
        "## What this control removes",
        "",
        "各回で実際に生成された5口をそのまま固定し、1〜37の数字ラベルだけを全評価期間で同じ写像に置換します。",
        "これにより5口の重なり・分散・scenario最適化・config選択は維持したまま、将来当せん数字とのidentity alignmentだけを壊します。",
        "",
    ]
    for key, title in [("v1", "Joint Set v1"), ("v2", "Joint Set v2")]:
        model = summary["models"][key]
        top = model["top7_hits"]
        port = model["portfolio_score"]
        lines += [
            f"## {title}",
            "",
            f"- Top7 hits: observed **{top['observed']:.4f}** / permuted mean **{top['permuted_mean']:.4f}** / identity edge **{top['identity_edge']:+.4f}** / p **{top['empirical_upper_tail_p']:.6f}**",
            f"- portfolio score: observed **{port['observed']:.4f}** / permuted mean **{port['permuted_mean']:.4f}** / identity edge **{port['identity_edge']:+.4f}** / p **{port['empirical_upper_tail_p']:.6f}**",
            f"- portfolio permutation p95/p99: **{port['permuted_p95']:.4f} / {port['permuted_p99']:.4f}**",
            "",
        ]
    lines += [
        "> p値はResearch診断です。過去60回の再利用データであり、Future OOSの独立証拠ではありません。",
        "> この検定で優位でもProduction昇格条件は変わりません。",
        "",
    ]
    return "\n".join(lines)


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    metadata_path: Path = Path("loto7_agent_output/research_external_metadata.csv"),
    permutations: int = 4096,
    cutoff_hour_jst: int = 18,
) -> Dict[str, object]:
    v1_rounds, _, v1_sha = build_v1_rounds(csv_path, out_dir, metadata_path, cutoff_hour_jst)
    v2_rounds, _, v2_sha = build_v2_rounds(csv_path, out_dir)
    if v1_sha != v2_sha:
        raise RuntimeError("v1/v2 replays do not use the same data SHA")

    v1 = permutation_test(v1_rounds, "v1", v1_sha, permutations, v1_portfolio_metrics)
    v2 = permutation_test(v2_rounds, "v2", v2_sha, permutations, v2_portfolio_metrics)
    if int(v1["evaluated_rounds"]) != int(v2["evaluated_rounds"]):
        raise RuntimeError("v1/v2 evaluated round counts differ")

    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "evaluation_type": "paired_global_number_label_permutation_identity_ablation",
        "data_sha256": v1_sha,
        "evaluated_rounds": int(v1["evaluated_rounds"]),
        "permutations": int(permutations),
        "models": {"v1": v1, "v2": v2},
        "independent_evidence": False,
        "promotion_eligible": False,
        "interpretation": (
            "Research-only paired control that isolates number-identity alignment from portfolio geometry. "
            "Future OOS governance remains unchanged."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "joint_set_identity_ablation_summary.json", summary)
    (out_dir / "joint_set_identity_ablation_report.md").write_text(
        render_report(summary), encoding="utf-8"
    )
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Paired global number-label permutation test for Joint Set v1/v2"
    )
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument(
        "--metadata", type=Path,
        default=Path("loto7_agent_output/research_external_metadata.csv"),
    )
    ap.add_argument("--permutations", type=int, default=4096)
    ap.add_argument("--cutoff-hour-jst", type=int, default=18)
    args = ap.parse_args()
    summary = run(
        args.csv, args.out_dir, args.metadata, args.permutations, args.cutoff_hour_jst
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
