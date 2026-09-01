#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import separated_optimizer as so
import signal_meta_model as meta
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, read_csv_flexible

CALIBRATION_VERSION = "champion-ranking-calibration-v1"
REPORT_VERSION = "champion-ranking-calibration-replay-v1"
CALIBRATION_WINDOW = 120
MIN_CALIBRATION_HISTORY = 60
BRIER_WEIGHT = 8.0
UNIFORM_Q = np.full(37, 1.0 / 37.0, dtype=float)


@dataclass(frozen=True)
class CalibrationConfig:
    name: str
    temperature: float
    uniform_mix: float

    def version(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return f"{self.name}-{hashlib.sha256(raw.encode()).hexdigest()[:10]}"

    def strength(self) -> float:
        return abs(math.log(float(self.temperature))) + float(self.uniform_mix)


PREDECLARED_CONFIGS: Tuple[CalibrationConfig, ...] = (
    CalibrationConfig("identity", 1.0, 0.0),
    CalibrationConfig("temp-1p25", 1.25, 0.0),
    CalibrationConfig("temp-1p50", 1.50, 0.0),
    CalibrationConfig("temp-2p00", 2.00, 0.0),
    CalibrationConfig("temp-3p00", 3.00, 0.0),
    CalibrationConfig("temp-5p00", 5.00, 0.0),
    CalibrationConfig("shrink-0p25", 1.0, 0.25),
    CalibrationConfig("shrink-0p50", 1.0, 0.50),
    CalibrationConfig("shrink-0p70", 1.0, 0.70),
    CalibrationConfig("shrink-0p85", 1.0, 0.85),
    CalibrationConfig("shrink-0p93", 1.0, 0.93),
    CalibrationConfig("shrink-0p97", 1.0, 0.97),
    CalibrationConfig("hybrid-1p50-0p25", 1.50, 0.25),
    CalibrationConfig("hybrid-1p50-0p50", 1.50, 0.50),
    CalibrationConfig("hybrid-2p00-0p25", 2.00, 0.25),
    CalibrationConfig("hybrid-2p00-0p50", 2.00, 0.50),
)


def calibrate_q(q: np.ndarray, cfg: CalibrationConfig) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    if q.shape != (37,):
        raise ValueError("q must have shape (37,)")
    if not np.all(np.isfinite(q)) or np.any(q <= 0.0):
        raise ValueError("q must be finite and strictly positive")
    if cfg.temperature <= 0.0:
        raise ValueError("temperature must be positive")
    if not (0.0 <= cfg.uniform_mix < 1.0):
        raise ValueError("uniform_mix must be in [0, 1)")
    q = q / q.sum()
    logits = np.log(q) / float(cfg.temperature)
    logits -= float(np.max(logits))
    qt = np.exp(logits)
    qt /= qt.sum()
    out = (1.0 - float(cfg.uniform_mix)) * qt + float(cfg.uniform_mix) * UNIFORM_Q
    return out / out.sum()


def rank_order(q: np.ndarray) -> np.ndarray:
    return np.argsort(-np.asarray(q, dtype=float), kind="mergesort")


def rank_preserved(base_q: np.ndarray, calibrated_q: np.ndarray) -> bool:
    return bool(np.array_equal(rank_order(base_q), rank_order(calibrated_q)))


def selector_score(rows: Sequence[Dict[str, float]]) -> float:
    if not rows:
        return float("-inf")
    agg = so.aggregate_signal(rows)
    return float(agg["log_edge_vs_uniform"] + BRIER_WEIGHT * agg["brier_edge_vs_uniform"])


def _champion_qs(x: np.ndarray, min_train: int) -> Tuple[List[Dict[str, float]], List[np.ndarray]]:
    _, qs = so.replay_signal(x, v2.DEFAULT_CHAMPION, min_train=min_train, keep_q=True)
    rows = [so.signal_row(q, np.flatnonzero(x[t])) for q, t in zip(qs, range(min_train, len(x)))]
    return rows, qs


def _current_champion_q(x: np.ndarray, min_train: int) -> np.ndarray:
    cfg = v2.DEFAULT_CHAMPION
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    for t in range(min_train, len(x)):
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, cfg)
    return v2._score_distribution(x, keys, logw, cfg)


def precompute_rows(qs: Sequence[np.ndarray], x: np.ndarray, min_train: int) -> Dict[str, List[Dict[str, float]]]:
    out: Dict[str, List[Dict[str, float]]] = {}
    for cfg in PREDECLARED_CONFIGS:
        rows: List[Dict[str, float]] = []
        for offset, q in enumerate(qs):
            cq = calibrate_q(q, cfg)
            if not rank_preserved(q, cq):
                raise RuntimeError(f"ranking changed for {cfg.version()} at offset {offset}")
            actual_idx = np.flatnonzero(x[min_train + offset])
            rows.append(so.signal_row(cq, actual_idx))
        out[cfg.version()] = rows
    return out


def choose_config(config_rows: Dict[str, Sequence[Dict[str, float]]], target_index: int,
                  window: int = CALIBRATION_WINDOW, min_history: int = MIN_CALIBRATION_HISTORY) -> CalibrationConfig:
    if target_index < min_history:
        return PREDECLARED_CONFIGS[0]
    start = max(0, target_index - int(window))
    ranked = []
    for idx, cfg in enumerate(PREDECLARED_CONFIGS):
        history = config_rows[cfg.version()][start:target_index]
        ranked.append((selector_score(history), -cfg.strength(), -idx, cfg))
    return max(ranked, key=lambda z: (z[0], z[1], z[2]))[3]


def nested_calibration(qs: Sequence[np.ndarray], x: np.ndarray, min_train: int,
                       last_n: int = 120) -> Dict[str, object]:
    config_rows = precompute_rows(qs, x, min_train)
    total = len(qs)
    start_index = max(0, total - int(last_n))
    selected_rows: List[Dict[str, float]] = []
    selected_versions: List[str] = []
    selected_configs: List[CalibrationConfig] = []
    preservation: List[bool] = []
    counts: Dict[str, int] = {}
    for idx in range(start_index, total):
        cfg = choose_config(config_rows, idx)
        cq = calibrate_q(qs[idx], cfg)
        preserved = rank_preserved(qs[idx], cq)
        if not preserved:
            raise RuntimeError("rank-preserving calibration invariant failed")
        selected_rows.append(config_rows[cfg.version()][idx])
        selected_versions.append(cfg.version())
        selected_configs.append(cfg)
        preservation.append(preserved)
        counts[cfg.version()] = counts.get(cfg.version(), 0) + 1
    return {
        "start_index": start_index,
        "last_n": len(selected_rows),
        "rows": selected_rows,
        "selected_versions": selected_versions,
        "selected_configs": selected_configs,
        "selected_counts": counts,
        "rank_preservation_rate": float(np.mean(preservation)) if preservation else 0.0,
        "config_rows": config_rows,
    }


def _paired(a: Sequence[Dict[str, float]], b: Sequence[Dict[str, float]], key: str,
            sign: float = 1.0) -> List[float]:
    n = min(len(a), len(b))
    return [float(sign * (a[-n + i][key] - b[-n + i][key])) for i in range(n)]


def _write_rounds(path: Path, clean, min_train: int, nested: Dict[str, object],
                  champion_rows: Sequence[Dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = int(nested["start_index"])
    rows = list(nested["rows"])
    cfgs = list(nested["selected_configs"])
    fields = [
        "round", "draw_date", "calibration_version", "temperature", "uniform_mix", "rank_preserved",
        "calibrated_top7_hits", "champion_top7_hits", "calibrated_actual_mass", "champion_actual_mass",
        "calibrated_mean_log_prob_actual", "champion_mean_log_prob_actual", "calibrated_brier", "champion_brier",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for j, (row, cfg) in enumerate(zip(rows, cfgs)):
            idx = start + j
            t = min_train + idx
            base = champion_rows[idx]
            w.writerow({
                "round": clean["回別"].iloc[t] if "回別" in clean.columns else t + 1,
                "draw_date": clean["抽せん日"].iloc[t].date().isoformat(),
                "calibration_version": cfg.version(),
                "temperature": f"{cfg.temperature:.6f}",
                "uniform_mix": f"{cfg.uniform_mix:.6f}",
                "rank_preserved": "true",
                "calibrated_top7_hits": f"{row['top7_hits']:.6f}",
                "champion_top7_hits": f"{base['top7_hits']:.6f}",
                "calibrated_actual_mass": f"{row['actual_mass']:.12f}",
                "champion_actual_mass": f"{base['actual_mass']:.12f}",
                "calibrated_mean_log_prob_actual": f"{row['mean_log_prob_actual']:.12f}",
                "champion_mean_log_prob_actual": f"{base['mean_log_prob_actual']:.12f}",
                "calibrated_brier": f"{row['brier']:.12f}",
                "champion_brier": f"{base['brier']:.12f}",
            })


def run(csv_path: Path, out_dir: Path, min_train: int = 100, last_n: int = 120,
        bootstrap_reps: int = 4000) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    champion_rows, champion_qs = _champion_qs(x, min_train)
    nested = nested_calibration(champion_qs, x, min_train, last_n=last_n)
    n = int(nested["last_n"])
    calibrated_rows = list(nested["rows"])
    champion_eval = champion_rows[-n:]
    uniform_rows = [so.signal_row(UNIFORM_Q, np.flatnonzero(x[t])) for t in range(len(x) - n, len(x))]

    calibrated_signal = so.aggregate_signal(calibrated_rows)
    champion_signal = so.aggregate_signal(champion_eval)
    uniform_signal = so.aggregate_signal(uniform_rows)

    ci_vs_champion_log = meta.block_bootstrap_mean_ci(
        _paired(calibrated_rows, champion_eval, "mean_log_prob_actual"), seed=42_000_001,
        reps=bootstrap_reps, block_len=8,
    )
    ci_vs_champion_brier = meta.block_bootstrap_mean_ci(
        _paired(champion_eval, calibrated_rows, "brier"), seed=42_000_002,
        reps=bootstrap_reps, block_len=8,
    )
    ci_vs_champion_top7 = meta.block_bootstrap_mean_ci(
        _paired(calibrated_rows, champion_eval, "top7_hits"), seed=42_000_003,
        reps=bootstrap_reps, block_len=8,
    )
    ci_vs_uniform_log = meta.block_bootstrap_mean_ci(
        _paired(calibrated_rows, uniform_rows, "mean_log_prob_actual"), seed=42_000_004,
        reps=bootstrap_reps, block_len=8,
    )
    ci_vs_uniform_brier = meta.block_bootstrap_mean_ci(
        _paired(uniform_rows, calibrated_rows, "brier"), seed=42_000_005,
        reps=bootstrap_reps, block_len=8,
    )
    ci_vs_uniform_mass = meta.block_bootstrap_mean_ci(
        _paired(calibrated_rows, uniform_rows, "actual_mass"), seed=42_000_006,
        reps=bootstrap_reps, block_len=8,
    )

    improves_champion = bool(
        float(nested["rank_preservation_rate"]) == 1.0
        and abs(ci_vs_champion_top7["mean"]) < 1e-12
        and ci_vs_champion_log["low95"] > 0.0
        and ci_vs_champion_brier["low95"] > 0.0
    )
    research_worthy = bool(
        calibrated_signal["log_edge_vs_uniform"] > 0.0
        and calibrated_signal["brier_edge_vs_uniform"] > 0.0
        and calibrated_signal["actual_mass_delta_vs_uniform"] > 0.0
        and float(nested["rank_preservation_rate"]) == 1.0
    )
    robust_uniform_edge = bool(
        research_worthy
        and ci_vs_uniform_log["low95"] > 0.0
        and ci_vs_uniform_brier["low95"] > 0.0
        and ci_vs_uniform_mass["low95"] > 0.0
    )

    config_rows = nested["config_rows"]
    next_cfg = choose_config(config_rows, len(champion_qs))
    current_base_q = _current_champion_q(x, min_train)
    current_cal_q = calibrate_q(current_base_q, next_cfg)
    if not rank_preserved(current_base_q, current_cal_q):
        raise RuntimeError("next-draw ranking changed after calibration")
    ranking = rank_order(current_base_q) + 1

    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else str(len(clean))
    digits = "".join(ch for ch in latest_round_text if ch.isdigit())
    target_round = int(digits) + 1 if digits else len(clean) + 1

    config_summaries = []
    for cfg in PREDECLARED_CONFIGS:
        rows = config_rows[cfg.version()]
        config_summaries.append({
            "version": cfg.version(),
            "config": asdict(cfg),
            "full_selector_score": selector_score(rows),
            "last120_signal": so.aggregate_signal(rows[-min(120, len(rows)):]),
        })

    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "evaluation_type": "ranking_preserving_nested_calibration_of_champion_signal",
        "data_sha256": fingerprint_file(csv_path),
        "source_rows": int(len(x)),
        "min_train": int(min_train),
        "nested_last_n": n,
        "calibration_window": CALIBRATION_WINDOW,
        "minimum_calibration_history": MIN_CALIBRATION_HISTORY,
        "selector": f"log_edge_vs_uniform + {BRIER_WEIGHT:.1f} * brier_edge_vs_uniform",
        "predeclared_config_count": len(PREDECLARED_CONFIGS),
        "predeclared_configs": config_summaries,
        "nested_calibrated_champion": {
            "signal": calibrated_signal,
            "selected_counts": nested["selected_counts"],
            "rank_preservation_rate": nested["rank_preservation_rate"],
        },
        "uncalibrated_champion": {
            "version": v2.DEFAULT_CHAMPION.version(),
            "signal": champion_signal,
        },
        "uniform_reference": uniform_signal,
        "paired_block_bootstrap_vs_uncalibrated_champion": {
            "log_probability_delta": ci_vs_champion_log,
            "brier_improvement": ci_vs_champion_brier,
            "top7_hits_delta": ci_vs_champion_top7,
        },
        "paired_block_bootstrap_vs_uniform": {
            "log_probability_delta": ci_vs_uniform_log,
            "brier_improvement": ci_vs_uniform_brier,
            "actual_mass_delta": ci_vs_uniform_mass,
        },
        "ranking_preserving_calibration_improves_champion": improves_champion,
        "research_worthy_signal": research_worthy,
        "robust_uniform_edge": robust_uniform_edge,
        "historical_evidence_only": True,
        "production_promotion_eligible": False,
        "future_oos_status": "not_registered",
        "next_research_target_round": target_round,
        "next_calibration_version": next_cfg.version(),
        "next_calibration_config": asdict(next_cfg),
        "next_top15": [
            {
                "number": int(num),
                "champion_score": float(current_base_q[num - 1]),
                "calibrated_score": float(current_cal_q[num - 1]),
                "champion_index_vs_uniform": float(current_base_q[num - 1] * 37.0),
                "calibrated_index_vs_uniform": float(current_cal_q[num - 1] * 37.0),
            }
            for num in ranking[:15]
        ],
        "interpretation": (
            "Retrospective Research-only calibration. Temperature and uniform shrinkage are strictly monotone, so number ranking is unchanged. Historical improvement cannot promote Production without a separately pre-frozen Future-OOS protocol."
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "champion_ranking_calibration_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_rounds(out_dir / "champion_ranking_calibration_rounds.csv", clean, min_train, nested, champion_rows)
    with (out_dir / "champion_ranking_calibration_next_ranking.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["rank", "number", "champion_score", "calibrated_score", "champion_index_vs_uniform", "calibrated_index_vs_uniform"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rank_no, num in enumerate(ranking, 1):
            w.writerow({
                "rank": rank_no,
                "number": int(num),
                "champion_score": f"{current_base_q[num - 1]:.12f}",
                "calibrated_score": f"{current_cal_q[num - 1]:.12f}",
                "champion_index_vs_uniform": f"{current_base_q[num - 1] * 37.0:.8f}",
                "calibrated_index_vs_uniform": f"{current_cal_q[num - 1] * 37.0:.8f}",
            })

    report = [
        "# Champion Ranking-Preserving Calibration Replay",
        "",
        f"- calibration: **{CALIBRATION_VERSION}**",
        f"- Champion: **{v2.DEFAULT_CHAMPION.version()}**",
        f"- evaluated nested window: **{n} draws**",
        f"- rank preservation: **{float(nested['rank_preservation_rate']) * 100:.2f}%**",
        f"- next target: **round {target_round}**",
        f"- next calibration: **{next_cfg.version()}** (T={next_cfg.temperature:.2f}, uniform_mix={next_cfg.uniform_mix:.2f})",
        "- role: **Research only; no Production promotion authority**",
        "",
        "## Nested calibrated signal vs Uniform",
        "",
        f"- Top-7 hits: **{calibrated_signal['top7_hits']:.6f}** (edge {calibrated_signal['top7_hits_delta_vs_uniform']:+.6f})",
        f"- actual mass edge: **{calibrated_signal['actual_mass_delta_vs_uniform']:+.8f}**",
        f"- log edge: **{calibrated_signal['log_edge_vs_uniform']:+.8f}**",
        f"- Brier edge: **{calibrated_signal['brier_edge_vs_uniform']:+.8f}**",
        "",
        "## Paired vs uncalibrated Champion",
        "",
        f"- log delta: **{ci_vs_champion_log['mean']:+.8f}** (moving-block 95% CI {ci_vs_champion_log['low95']:+.8f} .. {ci_vs_champion_log['high95']:+.8f})",
        f"- Brier improvement: **{ci_vs_champion_brier['mean']:+.8f}** (95% CI {ci_vs_champion_brier['low95']:+.8f} .. {ci_vs_champion_brier['high95']:+.8f})",
        f"- Top-7 delta: **{ci_vs_champion_top7['mean']:+.8f}** (95% CI {ci_vs_champion_top7['low95']:+.8f} .. {ci_vs_champion_top7['high95']:+.8f})",
        "",
        "## Paired vs Uniform",
        "",
        f"- log delta: **{ci_vs_uniform_log['mean']:+.8f}** (95% CI {ci_vs_uniform_log['low95']:+.8f} .. {ci_vs_uniform_log['high95']:+.8f})",
        f"- Brier improvement: **{ci_vs_uniform_brier['mean']:+.8f}** (95% CI {ci_vs_uniform_brier['low95']:+.8f} .. {ci_vs_uniform_brier['high95']:+.8f})",
        f"- actual mass delta: **{ci_vs_uniform_mass['mean']:+.8f}** (95% CI {ci_vs_uniform_mass['low95']:+.8f} .. {ci_vs_uniform_mass['high95']:+.8f})",
        "",
        f"- calibration improves Champion proper scores without rank loss: **{str(improves_champion).lower()}**",
        f"- research-worthy signal vs Uniform: **{str(research_worthy).lower()}**",
        f"- robust Uniform edge: **{str(robust_uniform_edge).lower()}**",
        "",
        "> Calibration does not generate tickets and does not alter the Production Champion or any frozen Future-OOS registry.",
    ]
    (out_dir / "champion_ranking_calibration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="LOTO7 Champion ranking-preserving calibration replay")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=120)
    ap.add_argument("--bootstrap-reps", type=int, default=4000)
    args = ap.parse_args()
    summary = run(args.csv, args.out_dir, args.min_train, args.last_n, args.bootstrap_reps)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
