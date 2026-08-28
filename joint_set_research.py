#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import precision_random_baseline as prb
import research_metadata as rm
from joint_set_model import (
    JointSetConfig,
    candidate_configs,
    expected_utility_portfolio,
    forecast,
    portfolio_metrics,
    signal_metrics,
    signal_quality,
)
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "joint-set-true-nested-v1"
FIELDS = [
    "round_index", "selected_config", "selected_config_score", "gate",
    "regime_stable", "regime_shift", "regime_volatile", "metadata_active",
    "signal_top7_hits", "signal_actual_mass", "signal_log_edge", "signal_brier_edge",
    "portfolio_max_hits", "portfolio_mean_hits", "portfolio_ge3", "portfolio_ge4", "portfolio_score",
    "random_max_hits", "random_mean_hits", "random_ge3", "random_ge4", "random_score",
    "score_delta_vs_random",
]


def parse_round(value: object, fallback: int) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else int(fallback)


def file_sha(path: Path) -> str:
    if not path.exists():
        return "missing"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def read_precision_rows(path: Path) -> Dict[int, Dict[str, float]]:
    out: Dict[int, Dict[str, float]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            idx = int(row["round_index"])
            out[idx] = {
                "random_max_hits": float(row["mean_max_hits"]),
                "random_mean_hits": float(row["mean_ticket_hits"]),
                "random_ge3": float(row["ge3_rate"]),
                "random_ge4": float(row["ge4_rate"]),
                "random_score": float(row["mean_score"]),
            }
    return out


def robust_prior_score(rows: Sequence[Dict[str, float]], window: int = 120) -> float:
    recent = list(rows[-max(30, int(window)):])
    if len(recent) < 30:
        return -1e9
    values = np.array([signal_quality(r) for r in recent], dtype=float)
    segments = [x for x in np.array_split(values, 3) if len(x)]
    worst = min(float(x.mean()) for x in segments)
    return float(values.mean() + 0.25 * worst - 0.08 * values.std())


def select_config(
    configs: Sequence[JointSetConfig],
    prequential: Dict[str, List[Dict[str, float]]],
    prior_count: int,
    selection_window: int,
) -> Tuple[JointSetConfig, float]:
    ranked: List[Tuple[float, str, JointSetConfig]] = []
    for cfg in configs:
        rows = prequential[cfg.version()][:max(0, int(prior_count))]
        score = robust_prior_score(rows, selection_window)
        ranked.append((score, cfg.version(), cfg))
    ranked.sort(key=lambda z: (z[0], z[1]), reverse=True)
    return ranked[0][2], float(ranked[0][0])


def bootstrap_ci(values: Sequence[float], seed: int = 914731, reps: int = 5000) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": 0.0, "low95": 0.0, "high95": 0.0}
    rng = np.random.default_rng(seed)
    means = np.empty(int(reps), dtype=float)
    for i in range(len(means)):
        means[i] = float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
    return {
        "mean": float(arr.mean()),
        "low95": float(np.quantile(means, 0.025)),
        "high95": float(np.quantile(means, 0.975)),
    }


def prepare_metadata(
    clean,
    metadata_path: Path,
    cutoff_hour_jst: int,
) -> Tuple[np.ndarray, List[str], Dict[str, object]]:
    rm.write_template(metadata_path)
    records, issues = rm.read_records(metadata_path)
    rounds = [parse_round(v, i + 1) for i, v in enumerate(clean.get("回別", range(1, len(clean) + 1)))]
    dates = [d.date().isoformat() for d in clean["抽せん日"]]
    latest_round = rounds[-1]
    latest_date = clean["抽せん日"].iloc[-1].date()
    rounds_plus = rounds + [latest_round + 1]
    dates_plus = dates + [(latest_date + __import__("datetime").timedelta(days=7)).isoformat()]
    design, names, _ = rm.design_matrix(records, rounds_plus, dates_plus, cutoff_hour_jst)
    summary = rm.validate_metadata(metadata_path, rounds_plus, dates_plus, cutoff_hour_jst)
    summary["issues"] = issues
    return design, names, summary


def metadata_for_target(
    x: np.ndarray,
    metadata_design: np.ndarray,
    t: int,
) -> Tuple[np.ndarray, Dict[str, float]]:
    if metadata_design.shape[1] == 0:
        return np.zeros(37, dtype=float), {"active": 0.0, "coverage": 0.0, "norm": 0.0}
    return rm.ridge_number_adjustment(
        x[:t], metadata_design[:t], metadata_design[t], ridge=24.0, min_rows=40
    )


def build_prequential_signal(
    x: np.ndarray,
    cfg: JointSetConfig,
    min_train: int,
    metadata_design: np.ndarray,
) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for t in range(min_train, len(x)):
        md_adj, md_diag = metadata_for_target(x, metadata_design, t)
        bundle = forecast(x[:t], cfg, rows, md_adj, md_diag)
        actual_idx = np.flatnonzero(x[t])
        row = signal_metrics(bundle.q, actual_idx)
        row.update({
            "gate": float(bundle.gate),
            "regime_stable": float(bundle.regime[0]),
            "regime_shift": float(bundle.regime[1]),
            "regime_volatile": float(bundle.regime[2]),
            "metadata_active": float(bundle.metadata_diagnostics.get("active", 0.0)),
        })
        rows.append(row)
    return rows


def summarize(
    rows: Sequence[Dict[str, object]],
    data_sha: str,
    metadata_sha: str,
    configs: Sequence[JointSetConfig],
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
    metadata_summary: Dict[str, object],
) -> Dict[str, object]:
    deltas = [float(r["score_delta_vs_random"]) for r in rows]
    selected = Counter(str(r["selected_config"]) for r in rows)
    return {
        "report_version": REPORT_VERSION,
        "evaluation_type": "strict_prior_only_prequential_config_selection_joint_set",
        "data_sha256": data_sha,
        "metadata_sha256": metadata_sha,
        "min_train": int(min_train),
        "last_n": int(last_n),
        "evaluated_rounds": len(rows),
        "selection_window": int(selection_window),
        "predeclared_config_count": len(configs),
        "config_versions": [c.version() for c in configs],
        "validation_scenarios": int(validation_scenarios),
        "validation_candidates": int(validation_candidates),
        "components": {
            "dynamic_marginal": True,
            "low_rank_pair_interaction": True,
            "hidden_regime_filter": True,
            "dynamic_uniform_gate": True,
            "leakage_safe_external_metadata": True,
            "expected_utility_portfolio": True,
        },
        "metadata": metadata_summary,
        "selected_config_counts": dict(selected),
        "signal": {
            "mean_top7_hits": float(np.mean([float(r["signal_top7_hits"]) for r in rows])) if rows else 0.0,
            "mean_actual_mass": float(np.mean([float(r["signal_actual_mass"]) for r in rows])) if rows else 0.0,
            "mean_log_edge_vs_uniform": float(np.mean([float(r["signal_log_edge"]) for r in rows])) if rows else 0.0,
            "mean_brier_edge_vs_uniform": float(np.mean([float(r["signal_brier_edge"]) for r in rows])) if rows else 0.0,
            "mean_gate": float(np.mean([float(r["gate"]) for r in rows])) if rows else 0.0,
        },
        "portfolio": {
            "mean_max_hits": float(np.mean([float(r["portfolio_max_hits"]) for r in rows])) if rows else 0.0,
            "random_mean_max_hits": float(np.mean([float(r["random_max_hits"]) for r in rows])) if rows else 0.0,
            "ge3_round_rate": float(np.mean([float(r["portfolio_ge3"]) for r in rows])) if rows else 0.0,
            "random_ge3_rate": float(np.mean([float(r["random_ge3"]) for r in rows])) if rows else 0.0,
            "ge4_round_rate": float(np.mean([float(r["portfolio_ge4"]) for r in rows])) if rows else 0.0,
            "random_ge4_rate": float(np.mean([float(r["random_ge4"]) for r in rows])) if rows else 0.0,
            "mean_score": float(np.mean([float(r["portfolio_score"]) for r in rows])) if rows else 0.0,
            "random_mean_score": float(np.mean([float(r["random_score"]) for r in rows])) if rows else 0.0,
            "score_delta_vs_random": bootstrap_ci(deltas),
            "round_win_rate_vs_random": float(np.mean([d > 0 for d in deltas])) if deltas else 0.0,
        },
        "independent_evidence": False,
        "promotion_eligible": False,
        "leakage_control": (
            "At target t, config selection, gate calibration, pair/regime estimation, metadata regression, and portfolio construction use only draws before t. "
            "Metadata must additionally have available_at_jst before the conservative target cutoff."
        ),
        "interpretation": "Research-only structural challenger. Production can change only through frozen Future OOS governance.",
    }


def render_report(summary: Dict[str, object]) -> str:
    s = summary["signal"]
    p = summary["portfolio"]
    ci = p["score_delta_vs_random"]
    md = summary["metadata"]
    return "\n".join([
        "# Joint Set Research v1 — Strict True Nested",
        "",
        f"- evaluated rounds: **{summary['evaluated_rounds']}**",
        f"- predeclared configs: **{summary['predeclared_config_count']}**",
        f"- selection window: **{summary['selection_window']}** prior draws",
        f"- validation scenarios/round: **{summary['validation_scenarios']}**",
        "- target result used before selection: **NO**",
        "- Production promotion eligible: **NO**",
        "",
        "## Signal + Dynamic Uniform Gate",
        f"- mean Top7 hits: **{s['mean_top7_hits']:.4f}**",
        f"- mean actual mass: **{s['mean_actual_mass']:.6f}**",
        f"- mean log edge vs uniform: **{s['mean_log_edge_vs_uniform']:+.6f}**",
        f"- mean Brier edge vs uniform: **{s['mean_brier_edge_vs_uniform']:+.6f}**",
        f"- mean model gate: **{s['mean_gate']:.3f}**",
        "",
        "## Expected-Utility Five-Ticket Portfolio",
        f"- mean max hits: **{p['mean_max_hits']:.4f}** / random **{p['random_mean_max_hits']:.4f}**",
        f"- >=3 round rate: **{p['ge3_round_rate']*100:.2f}%** / random **{p['random_ge3_rate']*100:.2f}%**",
        f"- >=4 round rate: **{p['ge4_round_rate']*100:.2f}%** / random **{p['random_ge4_rate']*100:.2f}%**",
        f"- score: **{p['mean_score']:.4f}** / random **{p['random_mean_score']:.4f}**",
        f"- score delta: **{ci['mean']:+.4f}** (bootstrap 95% CI {ci['low95']:+.4f}〜{ci['high95']:+.4f})",
        "",
        "## External metadata",
        f"- trusted records: **{md.get('trusted_records', 0)}**",
        f"- usable feature names: **{len(md.get('feature_names', []))}**",
        "- post-draw/same-round leakage guard: **ON**",
        "",
        "> Joint marginal + low-rank pair structure + regime filter + confidence gate + scenario portfolio optimizationを同一のstrict prior-only評価で測定します。",
        "> 過去診断であり、昇格証拠ではありません。",
        "",
    ])


def render_current_prediction(
    target_round: int,
    target_date: str,
    cfg: JointSetConfig,
    bundle,
    tickets: Sequence[Sequence[int]],
    diagnostics: Dict[str, float],
) -> str:
    lines = [
        "LOTO7 Joint Set Research予測（Research-only）",
        "=" * 64,
        f"対象回: 第{target_round}回",
        f"対象予定日: {target_date}",
        f"選択config: {cfg.version()}",
        f"Dynamic Uniform Gate: {bundle.gate:.4f}",
        f"Regime posterior: stable={bundle.regime[0]:.3f} shift={bundle.regime[1]:.3f} volatile={bundle.regime[2]:.3f}",
        f"Scenario expected max hits: {diagnostics['expected_max_hits']:.4f}",
        "",
    ]
    lines += [f"{i}. {' '.join(f'{int(n):02d}' for n in ticket)}" for i, ticket in enumerate(tickets, 1)]
    lines += ["", "※ Research-only。Production / Formal Challenger / Future OOS凍結を変更しません。"]
    return "\n".join(lines) + "\n"


def is_fresh(
    path: Path,
    data_sha: str,
    metadata_sha: str,
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
) -> bool:
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        old.get("report_version") == REPORT_VERSION
        and old.get("data_sha256") == data_sha
        and old.get("metadata_sha256") == metadata_sha
        and int(old.get("min_train", -1)) == int(min_train)
        and int(old.get("last_n", -1)) == int(last_n)
        and int(old.get("selection_window", -1)) == int(selection_window)
        and int(old.get("validation_scenarios", -1)) == int(validation_scenarios)
        and int(old.get("validation_candidates", -1)) == int(validation_candidates)
    )


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    metadata_path: Path = Path("loto7_agent_output/research_external_metadata.csv"),
    min_train: int = 100,
    last_n: int = 60,
    selection_window: int = 120,
    validation_scenarios: int = 512,
    validation_candidates: int = 96,
    current_scenarios: int = 4096,
    current_candidates: int = 192,
    random_reps: int = 4096,
    cutoff_hour_jst: int = 18,
    if_stale: bool = True,
) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    rm.write_template(metadata_path)
    metadata_sha = file_sha(metadata_path)
    summary_path = out_dir / "joint_set_true_nested_summary.json"
    if if_stale and is_fresh(
        summary_path, data_sha, metadata_sha, min_train, last_n, selection_window,
        validation_scenarios, validation_candidates,
    ):
        return json.loads(summary_path.read_text(encoding="utf-8"))

    metadata_design, metadata_names, metadata_summary = prepare_metadata(clean, metadata_path, cutoff_hour_jst)
    metadata_summary["feature_names"] = metadata_names
    write_json(out_dir / "research_metadata_summary.json", metadata_summary)

    configs = candidate_configs()
    preq = {
        cfg.version(): build_prequential_signal(x, cfg, min_train, metadata_design)
        for cfg in configs
    }

    prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_rows = read_precision_rows(out_dir / "precision_random_baseline.csv")
    eval_start = max(min_train + 30, len(x) - int(last_n))
    rows: List[Dict[str, object]] = []

    for t in range(eval_start, len(x)):
        prior_count = t - min_train
        cfg, cfg_score = select_config(configs, preq, prior_count, selection_window)
        calibration = preq[cfg.version()][:prior_count]
        md_adj, md_diag = metadata_for_target(x, metadata_design, t)
        bundle = forecast(x[:t], cfg, calibration, md_adj, md_diag)
        actual_idx = np.flatnonzero(x[t])
        sig = signal_metrics(bundle.q, actual_idx)
        tickets, _ = expected_utility_portfolio(
            bundle,
            seed=93_000_000 + t * 1009,
            scenarios=validation_scenarios,
            candidate_count=validation_candidates,
        )
        pm = portfolio_metrics(tickets, set((actual_idx + 1).tolist()))
        rnd = random_rows.get(t + 1)
        if rnd is None:
            raise RuntimeError(f"precision random baseline missing round_index={t+1}")
        rows.append({
            "round_index": t + 1,
            "selected_config": cfg.version(),
            "selected_config_score": cfg_score,
            "gate": bundle.gate,
            "regime_stable": float(bundle.regime[0]),
            "regime_shift": float(bundle.regime[1]),
            "regime_volatile": float(bundle.regime[2]),
            "metadata_active": float(bundle.metadata_diagnostics.get("active", 0.0)),
            "signal_top7_hits": sig["top7_hits"],
            "signal_actual_mass": sig["actual_mass"],
            "signal_log_edge": sig["log_edge"],
            "signal_brier_edge": sig["brier_edge"],
            "portfolio_max_hits": pm["max_hits"],
            "portfolio_mean_hits": pm["mean_hits"],
            "portfolio_ge3": pm["ge3"],
            "portfolio_ge4": pm["ge4"],
            "portfolio_score": pm["score"],
            **rnd,
            "score_delta_vs_random": float(pm["score"] - rnd["random_score"]),
        })

    summary = summarize(
        rows, data_sha, metadata_sha, configs, min_train, last_n, selection_window,
        validation_scenarios, validation_candidates, metadata_summary,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(summary_path, summary)
    write_rows(out_dir / "joint_set_true_nested.csv", rows)
    (out_dir / "joint_set_true_nested_report.md").write_text(render_report(summary), encoding="utf-8")

    target_t = len(x)
    cfg, cfg_score = select_config(configs, preq, target_t - min_train, selection_window)
    md_adj, md_diag = metadata_for_target(x, metadata_design, target_t)
    bundle = forecast(x, cfg, preq[cfg.version()], md_adj, md_diag)
    latest_round = parse_round(clean["回別"].iloc[-1] if "回別" in clean.columns else len(clean), len(clean))
    target_round = latest_round + 1
    target_date = (clean["抽せん日"].iloc[-1].date() + __import__("datetime").timedelta(days=7)).isoformat()
    tickets, diagnostics = expected_utility_portfolio(
        bundle,
        seed=97_000_000 + target_round * 1009,
        scenarios=current_scenarios,
        candidate_count=current_candidates,
    )
    current = {
        "report_version": "joint-set-current-research-v1",
        "data_sha256": data_sha,
        "metadata_sha256": metadata_sha,
        "target_round": target_round,
        "target_date": target_date,
        "selected_config": cfg.version(),
        "selected_config_prior_score": cfg_score,
        "gate": bundle.gate,
        "gate_diagnostics": bundle.gate_diagnostics,
        "regime": {
            "stable": float(bundle.regime[0]), "shift": float(bundle.regime[1]), "volatile": float(bundle.regime[2]),
        },
        "metadata": bundle.metadata_diagnostics,
        "portfolio_diagnostics": diagnostics,
        "tickets": [[int(n) for n in ticket] for ticket in tickets],
        "research_only": True,
        "promotion_eligible": False,
    }
    write_json(out_dir / "joint_set_current_research.json", current)
    with (out_dir / "joint_set_candidate_tickets.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticket", "numbers", "sum", "odd_count"])
        w.writeheader()
        for i, ticket in enumerate(tickets, 1):
            w.writerow({
                "ticket": i,
                "numbers": " ".join(f"{int(n):02d}" for n in ticket),
                "sum": sum(ticket),
                "odd_count": sum(int(n) % 2 for n in ticket),
            })
    (out_dir / "joint_set_latest_prediction.txt").write_text(
        render_current_prediction(target_round, target_date, cfg, bundle, tickets, diagnostics), encoding="utf-8"
    )
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Research-only Joint Set model with strict prior-only True Nested evaluation")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--metadata", type=Path, default=Path("loto7_agent_output/research_external_metadata.csv"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--selection-window", type=int, default=120)
    ap.add_argument("--validation-scenarios", type=int, default=512)
    ap.add_argument("--validation-candidates", type=int, default=96)
    ap.add_argument("--current-scenarios", type=int, default=4096)
    ap.add_argument("--current-candidates", type=int, default=192)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--cutoff-hour-jst", type=int, default=18)
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()
    summary = run(
        args.csv, args.out_dir, args.metadata, args.min_train, args.last_n,
        args.selection_window, args.validation_scenarios, args.validation_candidates,
        args.current_scenarios, args.current_candidates, args.random_reps,
        args.cutoff_hour_jst, args.if_stale,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
