#!/usr/bin/env python3
"""Replay every lottery prediction from round 20 whenever the system changes.

Target round t uses ONLY rounds 1..t-1. Round 20 has 19 prior draws,
below the legacy 20-row feature minimum; it is labelled COLD_START_UNIFORM.
Replay is retrospective re-evaluation of CURRENT parameters, not the original
live forecast or independent future evidence. This module cannot promote
models, edit registered predictions or change Production.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np

import autonomous_evolution_lab as learned
import autonomous_self_rewrite as rewrite
import balanced_uniform_portfolio as disjoint
import historical_replay as hist_replay
import loto7_v2_runner as v2
import loto7_v3_runner as v3
import production_ticket_geometry35 as geometry35
import top1_overlap34 as overlap34
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import (
    expert_probabilities, fingerprint_file, make_history,
    make_ticket_portfolio, read_csv_flexible,
)

VERSION = "change-triggered-round20-walkforward-v1"
FIRST_ROUND = 20
MODEL_MIN_PRIOR = 20
LEARNED_MIN_PRIOR = 100
LANES = ("current_champion", "uniform_disjoint35",
         "top1_shared34", "autonomous_learned")
SOURCES = (
    "loto7.csv",
    "loto7_agent_output/source_validation.json",
    "loto7_agent_output/model_champion.json",
    "loto7_evolving_agent.py",
    "loto7_v2_runner.py",
    "loto7_v3_runner.py",
    "historical_replay.py",
    "balanced_uniform_portfolio.py",
    "top1_overlap34.py",
    "production_ticket_geometry35.py",
    "autonomous_evolution_lab.py",
    "autonomous_self_rewrite.py",
    "round20_change_replay.py",
)
HEADER = (
    "target_round", "draw_date", "prior_rounds", "lane", "model_version",
    "training_status", "training_data_sha256", "forecast_sha256",
    "top7_numbers", "top7_hits", "actual_main", "actual_bonus",
    "ticket_1", "ticket_2", "ticket_3", "ticket_4", "ticket_5",
    "coverage", "max_hits", "mean_ticket_hits", "any_ge3", "any_ge4",
    "composite_score", "categorical_log_loss", "diagnostic_only",
)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stable(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not a JSON object: {path}")
    return value


def fmt(nums) -> str:
    return " ".join(f"{int(n):02d}" for n in sorted(nums))


def validate_inputs(root: Path, csv_path: Path, source_path: Path,
                    champion_path: Path) -> tuple[np.ndarray, object, v2.ModelConfig, dict]:
    if not (csv_path.is_file() and source_path.is_file() and champion_path.is_file()):
        raise ValueError("missing historical data, trust report or champion")
    x, clean = make_history(read_csv_flexible(csv_path))
    rounds = [hist_replay.parse_round(value, -1) for value in clean["回別"]]
    if rounds != list(range(1, len(x) + 1)):
        raise ValueError("missing, duplicate or out-of-order historical draw")
    if len(x) < FIRST_ROUND or x.shape[1] != 37:
        raise ValueError("incomplete initial historical replay")
    if not np.all(x.sum(axis=1) == 7):
        raise ValueError("one or more seven-number main draws invalid")
    dates = [d.date().isoformat() for d in clean["抽せん日"]]
    if dates != sorted(set(dates)):
        raise ValueError("draw dates are not increasing")
    status = validate_trusted_source(csv_path, source_path)
    if status.get("trusted") is not True or status.get("round") != len(x):
        raise ValueError("latest draw not independently two-source verified")
    info = load(source_path)
    if (info.get("verification") != "verified_two_result_sources"
            or (info.get("verification_provenance") or {}).get("draw_csv_sha256")
               != fingerprint_file(csv_path)):
        raise ValueError("source attestation and historical draw SHA differ")
    champion = load(champion_path)
    config = v2.ModelConfig(**champion["config"])
    if champion.get("model_version") != config.version():
        raise ValueError("Champion model version and config disagree")
    return x, clean, config, {"last_round": len(x), "model_version": config.version(),
                              "csv_sha256": fingerprint_file(csv_path)}


def learned_program(root: Path) -> tuple[dict | None, dict]:
    sub = root / "research" / "autonomous_generated"
    src, manifest_path = sub / rewrite.SOURCE, sub / rewrite.MANIFEST
    if not src.exists() and not manifest_path.exists():
        return None, {"state": "not_generated", "enabled": False}
    if src.exists() != manifest_path.exists():
        raise ValueError("learned research code and manifest must both exist")
    manifest = load(manifest_path)
    cfg = rewrite.validate_model(manifest["learned_config"])
    expected = rewrite.generate_source(
        config=cfg, candidate_id=manifest["learned_candidate_id"],
        data_sha=manifest["draw_data_sha256"],
        source_state_sha=manifest["source_state_sha256"],
    )
    if (src.read_text(encoding="utf-8") != expected
            or sha(src.read_bytes()) != manifest["source_sha256"]
            or manifest.get("source_authority") !=
               "research_only_not_loaded_by_production"
            or manifest.get("champion_changed") is not False
            or manifest.get("historical_only_not_independent") is not True):
        raise ValueError("learned source SHA, template or authority mismatch")
    # Parameters were selected after viewing historical outcomes. A replay of
    # those same outcomes has selection bias, even with prior-only q per draw.
    return cfg, {"state": "historical_post_selected_diagnostic_only",
                 "enabled": True, "version": manifest["learned_candidate_id"],
                 "generated_source_sha256": manifest["source_sha256"],
                 "historical_selection_data_sha256": manifest["draw_data_sha256"]}


def check_tickets(tickets, coverage: int | None = None) -> list[tuple[int, ...]]:
    if len(tickets) != 5:
        raise ValueError("five tickets required")
    normalized = [tuple(sorted(int(x) for x in ticket)) for ticket in tickets]
    if any(len(t) != 7 or len(set(t)) != 7
           or min(t) < 1 or max(t) > 37 for t in normalized):
        raise ValueError("ticket outside 7/37")
    if len(set(normalized)) != 5:
        raise ValueError("five distinct tickets required")
    used = len(set().union(*(set(t) for t in normalized)))
    if coverage is not None and used != coverage:
        raise ValueError("unexpected portfolio coverage")
    return normalized


def _logloss(q: np.ndarray, actual: set[int]) -> float:
    # Surrogate categorical log score per drawn number, not the joint
    # without-replacement draw likelihood; equal for all tickets on a lane.
    if q.shape != (37,) or not np.all(np.isfinite(q)) or np.any(q <= 0):
        raise ValueError("invalid prior-only 37-label model distribution")
    if not np.isclose(q.sum(), 1.0, atol=1e-12):
        raise ValueError("model distribution is not normalized")
    return float(-np.mean(np.log(q[[n-1 for n in sorted(actual)]])))


def make_row(*, target: int, date: str, prior: int, lane: str,
             version: str, training: str, training_sha: str,
             q: np.ndarray, tickets, actual: set[int], bonus) -> dict:
    if lane not in LANES or target != prior + 1:
        raise ValueError("target/training round mismatch")
    tickets = check_tickets(tickets)
    top7 = tuple((np.argsort(-q, kind="stable")[:7] + 1).tolist())
    m = v2._portfolio_metrics(tickets, actual)
    cover = len(set().union(*(set(t) for t in tickets)))
    commitment = {"target": target, "lane": lane, "version": version,
                  "prior": prior, "q": [float(x) for x in q],
                  "tickets": tickets, "training_sha256": training_sha}
    result = {
        "target_round": target, "draw_date": date, "prior_rounds": prior,
        "lane": lane, "model_version": version, "training_status": training,
        "training_data_sha256": training_sha,
        "forecast_sha256": sha(stable(commitment).encode("utf-8")),
        "top7_numbers": fmt(top7), "top7_hits": len(set(top7) & actual),
        "actual_main": fmt(actual), "actual_bonus": fmt(bonus),
        **{f"ticket_{i}": fmt(t) for i, t in enumerate(tickets, 1)},
        "coverage": cover,
        "max_hits": int(m["max_hits"]), "mean_ticket_hits": float(m["mean_hits"]),
        "any_ge3": int(m["ge3"]), "any_ge4": int(m["ge4"]),
        "composite_score": float(v3.row_score(m)),
        "categorical_log_loss": _logloss(q, actual),
        "diagnostic_only": True,
    }
    return result


def validate_temporal_invariance(row: dict, *, prior: int, target: int,
                                 q: np.ndarray, tickets) -> None:
    """A replay row must be immutable when its own result is revealed."""
    if (row["target_round"] != target or row["prior_rounds"] != prior
            or row["training_data_sha256"] == ""
            or row["forecast_sha256"] == ""):
        raise ValueError("retrospective forecast missing pre-result state")
    if row["lane"] == "uniform_disjoint35":
        disjoint.validate_portfolio(tickets)
    if row["lane"] == "top1_shared34":
        overlap34.validate_tickets(tickets, int(np.argmax(q)) + 1)


def summarize(rows: list[dict], provenance: dict, learned_meta: dict,
              sources: dict[str, str], pool_size: int) -> dict:
    bucket = defaultdict(list)
    for row in rows:
        bucket[row["lane"]].append(row)
    if not rows or set(bucket) < set(LANES[:3]):
        raise ValueError("missing primary retrospective lanes")
    summary = {}
    for lane, items in sorted(bucket.items()):
        scores = np.array([r["composite_score"] for r in items])
        top7 = np.array([r["top7_hits"] for r in items])
        summaries = {
            "rounds": len(items),
            "first_round": items[0]["target_round"],
            "last_round": items[-1]["target_round"],
            "mean_composite": float(scores.mean()),
            "mean_max_hits": float(np.mean([r["max_hits"] for r in items])),
            "any_ge3_rate": float(np.mean([r["any_ge3"] for r in items])),
            "any_ge4_rate": float(np.mean([r["any_ge4"] for r in items])),
            "mean_top7_hits": float(top7.mean()),
            "mean_categorical_logloss": float(np.mean(
                [r["categorical_log_loss"] for r in items])),
            "average_covered_numbers": float(np.mean([r["coverage"] for r in items])),
            "post_selection_warning": lane == "autonomous_learned",
        }
        summary[lane] = summaries
    common = {
        lane: {r["target_round"]: r for r in items}
        for lane, items in bucket.items()
    }
    matched = []
    for lane in ("top1_shared34", "current_champion", "autonomous_learned"):
        if lane not in common:
            continue
        rounds = sorted(set(common[lane]) & set(common["uniform_disjoint35"]))
        d = np.array([common[lane][t]["composite_score"] -
                      common["uniform_disjoint35"][t]["composite_score"]
                      for t in rounds], dtype=float)
        matched.append({
            "lane": lane, "comparator": "uniform_disjoint35",
            "paired_rounds": len(rounds),
            "observed_mean_score_delta": float(d.mean()),
            "observed_delta_standard_error": (
                float(d.std(ddof=1)/np.sqrt(len(d))) if len(d) > 1 else None
            ),
            "descriptive_only": True,
            "not_independent_post_selection_holdout": True,
        })
    return {
        "version": VERSION,
        "evaluation_type": "retrospective_reexecution_with_priors_only",
        "first_target_round": FIRST_ROUND,
        "last_target_round": provenance["last_round"],
        "latest_draw_sha256": provenance["csv_sha256"],
        "tested_champion_version": provenance["model_version"],
        "model_selected_using_full_historical_data": True,
        "first_model_eligible_target": MODEL_MIN_PRIOR + 1,
        "round20_handling": "uniform_cold_start_with_19_prior_draws",
        "pool_size": pool_size,
        "source_file_sha256": sources,
        "source_manifest_sha256": sha(stable(sources).encode("utf-8")),
        "learned_model": learned_meta,
        "lanes": summary,
        "paired_descriptive_comparisons": matched,
        "total_retrospective_rows": len(rows),
        "outcome_was_not_an_input_to_any_forecast": True,
        "first_prize_odds_improved": False,
        "production_promoted": False,
        "future_oos_registry_or_pre_frozen_predictions_modified": False,
        "trial_budget_consumed": 0,
        "reference_scope": (
            "Current model/config replayed on old data (parameter selection can "
            "have used these outcomes); NOT actual archived predictions or "
            "independent prospective OOS. Research only."
        ),
    }


def execute(root: Path, pool_size: int = 150) -> tuple[dict, list[dict]]:
    if type(pool_size) is not int or not 100 <= pool_size <= 2000:
        raise ValueError("invalid bounded candidate ticket pool")
    root = root.resolve()
    csv_path = root / "loto7.csv"
    src_path = root / "loto7_agent_output/source_validation.json"
    ch_path = root / "loto7_agent_output/model_champion.json"
    x, clean, cfg, source = validate_inputs(root, csv_path, src_path, ch_path)
    learned_cfg, learned_meta = learned_program(root)
    sources = {str(p): sha((root / p).read_bytes())
               for p in SOURCES if (root / p).is_file()}
    if set(sources) != set(SOURCES):
        raise ValueError("required algorithm code fingerprint missing")

    uniform = np.full(37, 1/37, dtype=float)
    keys = list(expert_probabilities(x[:MODEL_MIN_PRIOR]).keys())
    logw = np.zeros(len(keys), dtype=float)
    rows: list[dict] = []
    for t in range(FIRST_ROUND - 1, len(x)):
        target = t + 1
        prefix = x[:t]  # This is the ONLY input to the forecaster.
        training_sha = sha(prefix.tobytes())
        if t < MODEL_MIN_PRIOR:
            q = uniform.copy()
            phase = "cold_start_19_priors_uniform"
        else:
            q = v2._score_distribution(prefix, keys, logw, cfg)
            phase = "prior_only_champion"
        top1 = int(np.argmax(q)) + 1
        champion_tickets = make_ticket_portfolio(
            q, n_tickets=5, seed=target, pool_size=pool_size,
            overlap_penalty=cfg.overlap_penalty)
        portfolios = {
            "current_champion": (cfg.version(), phase, q, champion_tickets),
            "uniform_disjoint35": (
                disjoint.VERSION, "fair_uniform_geometry_only", uniform,
                disjoint.disjoint_portfolio(
                    geometry35.SEED_BASE + target*geometry35.SEED_MULTIPLIER)),
            "top1_shared34": (
                overlap34.VERSION, "top1_from_prior_only_model", q,
                overlap34.make_portfolio(top1, 31_000_000 + target*1009)),
        }
        if learned_cfg is not None and t >= LEARNED_MIN_PRIOR:
            q7 = learned.prior_probabilities(prefix, learned_cfg)
            lq = q7 / 7.0
            portfolios["autonomous_learned"] = (
                learned_meta["version"], "post_selected_research_parameters_prior_only_q",
                lq,
                make_ticket_portfolio(
                    lq, n_tickets=5, seed=61_000_000 + target*1009,
                    pool_size=pool_size, overlap_penalty=cfg.overlap_penalty),
            )
        # An outcome is read *only after* all this round's portfolios/q exist.
        actual = {int(n) for n in (np.flatnonzero(x[t]) + 1)}
        bonus = hist_replay.parse_nums(clean.iloc[t].get("ボーナス数字", ""))[:2]
        date = clean.iloc[t]["抽せん日"].date().isoformat()
        for lane, (version, mode, pred, tickets) in portfolios.items():
            row = make_row(target=target, date=date, prior=t,
                           lane=lane, version=version, training=mode,
                           training_sha=training_sha, q=pred,
                           tickets=tickets, actual=actual, bonus=bonus)
            validate_temporal_invariance(row, prior=t, target=target,
                                         q=pred, tickets=tickets)
            rows.append(row)
        if t >= MODEL_MIN_PRIOR:
            logw = v2._update_log_weights(prefix, np.flatnonzero(x[t]), keys, logw, cfg)
    per_lane = defaultdict(list)
    for row in rows:
        per_lane[row["lane"]].append(row["target_round"])
    for lane in LANES[:3]:
        if per_lane[lane] != list(range(FIRST_ROUND, len(x)+1)):
            raise ValueError("replay skipped or duplicated a required target")
    if learned_cfg and per_lane["autonomous_learned"] != list(
            range(LEARNED_MIN_PRIOR+1, len(x)+1)):
        raise ValueError("learned lane skipped prior eligible rounds")
    new_sources = {str(p): sha((root / p).read_bytes()) for p in SOURCES}
    if sources != new_sources or sha(csv_path.read_bytes()) != source["csv_sha256"]:
        raise ValueError("source inputs changed during replay; reject mixed snapshots")
    return summarize(rows, source, learned_meta, sources, pool_size), rows


def csv_data(rows: list[dict]) -> str:
    file = io.StringIO(newline="")
    writer = csv.DictWriter(file, fieldnames=HEADER, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row[k] for k in HEADER})
    return file.getvalue()


def markdown(summary: dict) -> str:
    lines = [
        "# LOTO7 第20回からの全回ウォークフォワード再予測",
        "",
        f"- 対象: 第**{summary['first_target_round']}〜{summary['last_target_round']}回**",
        f"- 現在のChampion: `{summary['tested_champion_version']}`",
        "- 第20回: 直前19回で既存モデルは学習できず、一様コールドスタート",
        "- 第21回以降: 対象回以前の結果だけで毎回予測・順次モデル重み更新",
        "- 全回を最新モデルのパラメータで遡及再計算。過去の当時の実運用記録や真の未来OOSではありません。",
        "- 現行35数字Production幾何は第702回以降が本番対象。以下の過去比較は仮想研究再現です。",
        "",
        "| 方法 | 評価回数 | 複合スコア | 平均最大一致 | 3個以上率 | Top7一致 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, stat in summary["lanes"].items():
        lines.append(
            f"| {name} | {stat['rounds']} | {stat['mean_composite']:.5f} "
            f"| {stat['mean_max_hits']:.5f} | {100*stat['any_ge3_rate']:.2f}% "
            f"| {stat['mean_top7_hits']:.5f} |"
        )
    lines += ["", "## 同一抽せん回での35数字方式との差（探索的比較）"]
    for item in summary["paired_descriptive_comparisons"]:
        lines.append(
            f"- {item['lane']}: Δ={item['observed_mean_score_delta']:+.5f}, "
            f"共通{item['paired_rounds']}回 (推定不確実性は過去データ内の参考値のみ)"
        )
    lines += [
        "", "## 解釈と禁止",
        "- 未来の結果が予測関数に渡されないことをテストしています。",
        "- 現在のChampionや生成研究モデルの係数は過去データを見て選ばれ得るため、将来予測力の独立証拠ではありません。",
        "- generated研究モデルは事後選択の診断であり、本番昇格の根拠にしません。",
        "- 真正な事前凍結・独立照合・26回将来検証は別の既存台帳が唯一の根拠です。",
        "- 本レポートはChampion、発行済みの5口、将来OOSの凍結を変更しません。",
        f"- 履歴CSV SHA: `{summary['latest_draw_sha256']}`",
        f"- コード/モデル入力SHAセット: `{summary['source_manifest_sha256']}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path,
                   default=Path("research_output/round20_replay"))
    p.add_argument("--pool-size", type=int, default=150)
    opts = p.parse_args()
    summary, rounds = execute(opts.repo_root, opts.pool_size)
    opts.out_dir.mkdir(parents=True, exist_ok=True)
    (opts.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    (opts.out_dir / "all_round_predictions.csv").write_text(
        csv_data(rounds), encoding="utf-8-sig")
    (opts.out_dir / "report.md").write_text(
        markdown(summary), encoding="utf-8")
    print(json.dumps({
        "first": summary["first_target_round"],
        "last": summary["last_target_round"],
        "records": summary["total_retrospective_rows"],
        "lanes": list(summary["lanes"]),
        "champion": summary["tested_champion_version"],
        "production_changed": summary["production_promoted"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
