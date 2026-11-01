#!/usr/bin/env python3
"""Read-only diagnostic scorecard. Never freezes, grades, predicts, or promotes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

VERSION = "prediction-metrics-scorecard-v1"
FILES = {
    "historical": "historical_replay_summary.json",
    "reconciliation": "historical_reconciliation_summary.json",
    "calibration": "champion_calibration_oos_state.json",
    "future_oos": "future_holdout_evidence.json",
}


def _read(path: Path) -> tuple[dict | None, str | None]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError, UnicodeError):
        return None, None
    if not isinstance(value, dict):
        return None, None
    return value, hashlib.sha256(raw).hexdigest()


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("nonfinite metric")
    return value


def _integer(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("invalid count")
    return value


def build_scorecard(output_dir: Path) -> dict:
    """Only use published aggregate reports; each category fails closed independently."""
    reports = {key: _read(output_dir / filename) for key, filename in FILES.items()}
    hist, _ = reports["historical"]
    recon, _ = reports["reconciliation"]
    cal, _ = reports["calibration"]
    future, _ = reports["future_oos"]
    result = {
        "version": VERSION,
        "scope": "read_only_aggregate_diagnostics",
        "prediction_skill_confirmed": False,
        "historical": {"status": "unavailable"},
        "random_baseline": {"status": "unavailable"},
        "calibration": {"status": "unavailable", "ece": None},
        "reference_payout": {"status": "unavailable", "actual_profit": None},
        "future_oos": {"status": "unavailable", "confirmed": False},
        "provenance": {key: {"file": FILES[key], "sha256": digest}
                       for key, (_, digest) in reports.items()},
    }
    if hist is not None:
        try:
            if hist["evaluation_type"] != "strict_walk_forward_fixed_baseline":
                raise ValueError("not a fixed historical replay")
            draws = _integer(hist["evaluated_rounds"], minimum=1)
            start = _integer(hist["first_evaluated_round"], minimum=1)
            end = _integer(hist["last_evaluated_round"], minimum=start)
            if draws != end - start + 1:
                raise ValueError("nonconsecutive historical scope")
            top = hist["top7"]
            port = hist["portfolio_5_tickets"]
            mean_hits, uniform_hits = _number(top["mean_hits"]), _number(top["random_theoretical_mean_hits"])
            max_hits, random_max = _number(port["mean_max_hits"]), _number(port["random_mean_max_hits"])
            score, random_score = _number(port["mean_score"]), _number(port["random_mean_score"])
            if not (0 <= mean_hits <= 7 and 0 <= max_hits <= 7 and 0 <= random_max <= 7):
                raise ValueError("impossible hits")
            if abs(mean_hits - uniform_hits - _number(top["delta_vs_random"])) > 1e-8:
                raise ValueError("top7 delta mismatch")
            if abs(score - random_score - _number(port["mean_score_delta_vs_random"])) > 1e-8:
                raise ValueError("score delta mismatch")
            result["historical"] = {
                "status": "historical_only", "rounds": draws, "start_round": start,
                "end_round": end, "top7_mean_hits": mean_hits,
                "uniform_expected_hits": uniform_hits,
                "top7_delta_vs_uniform": mean_hits - uniform_hits,
                "p_value_exploratory": _number(top["approx_two_sided_p"]),
            }
            result["random_baseline"] = {
                "status": "historical_only", "rounds": draws,
                "portfolio_mean_max_hits": max_hits, "random_mean_max_hits": random_max,
                "mean_max_hits_delta": max_hits - random_max,
                "portfolio_mean_score": score, "random_mean_score": random_score,
                "mean_score_delta": score - random_score,
                "random_portfolios_per_round": _integer(hist["random_portfolios_per_round"], minimum=1),
            }
        except (KeyError, TypeError, ValueError):
            result["historical"] = {"status": "invalid_evidence"}
            result["random_baseline"] = {"status": "invalid_evidence"}
    if recon is not None:
        try:
            if (hist is None or result["historical"]["status"] != "historical_only" or
                    recon["loto_csv_sha256"] != hist["csv_sha256"] or
                    _integer(recon["evaluated_rounds"]) != result["historical"]["rounds"] or
                    _integer(recon["evaluated_tickets"]) != _integer(hist["evaluated_tickets"]) or
                    _integer(recon["known_payout_rows"]) != _integer(recon["evaluated_tickets"]) or
                    _integer(recon["unknown_payout_rows"]) != 0 or
                    recon["integrity"]["prediction_actual_fields_reverified"] is not True or
                    _integer(recon["integrity"]["mismatches"]) != 0):
                raise ValueError("reconciliation or source mismatch")
            cost = _integer(recon["purchase_cost_yen"], minimum=1)
            payout = _integer(recon["published_reference_payout_yen"])
            if cost != _integer(recon["evaluated_tickets"]) * 300 or (
                    abs(payout / cost - _number(recon["published_reference_roi"])) > 1e-8):
                raise ValueError("invalid reference return")
            result["reference_payout"] = {
                "status": "historical_hypothetical_only",
                "tickets": _integer(recon["evaluated_tickets"]),
                "winning_tickets": _integer(recon["winning_tickets"]),
                "reference_cost_yen": cost, "reference_payout_yen": payout,
                "reference_net_yen": payout - cost, "reference_roi": payout / cost,
                "actual_profit": None,
            }
        except (KeyError, TypeError, ValueError):
            result["reference_payout"] = {"status": "invalid_evidence", "actual_profit": None}
    if cal is not None:
        try:
            if cal["protocol_version"] != "champion-calibration-oos-v1":
                raise ValueError("unknown calibration protocol")
            trusted = _integer(cal["trusted_draws"])
            horizon = _integer(cal["horizon_trusted_draws"], minimum=1)
            if trusted > horizon or cal.get("promotion_role") != "diagnostic_only":
                raise ValueError("invalid prospective calibration scope")
            result["calibration"] = {
                "status": "descriptive_only" if trusted else "waiting_for_future_draws",
                "trusted_draws": trusted, "horizon_draws": horizon,
                "mean_log_improvement_vs_uniform": _number(cal["sum_log_delta_vs_uniform"]) / trusted if trusted else None,
                "mean_brier_improvement_vs_uniform": _number(cal["sum_brier_improvement_vs_uniform"]) / trusted if trusted else None,
                "mean_log_improvement_vs_base": _number(cal["sum_log_delta_vs_base"]) / trusted if trusted else None,
                "mean_brier_improvement_vs_base": _number(cal["sum_brier_improvement_vs_base"]) / trusted if trusted else None,
                "ece": None, "reliability_binning": "not_available_from_aggregate_state",
                "skill_claim": False,
            }
        except (KeyError, TypeError, ValueError):
            result["calibration"] = {"status": "invalid_evidence", "ece": None}
    if future is not None:
        try:
            if future["version"] != "future-holdout-evidence-report-v1":
                raise ValueError("unknown future evidence")
            progress = future["progress"]
            trusted = _integer(progress["trusted_draws"])
            horizon = _integer(progress["horizon_trusted_draws"], minimum=1)
            prereg = future["confirmation_policy_timing"]["registered_before_first_trusted_draw"]
            if not isinstance(prereg, bool) or trusted > horizon or not isinstance(future["confirmed"], bool):
                raise ValueError("invalid prospective evidence")
            # This card is diagnostic; no promotion or confirmatory inference authority.
            result["future_oos"] = {
                "status": "diagnostic_only", "trusted_draws": trusted,
                "horizon_draws": horizon, "policy_registered_before_first_outcome": prereg,
                "claim_status": str(future["claim_status"])[:100],
                "confirmed": False,
            }
        except (KeyError, TypeError, ValueError):
            result["future_oos"] = {"status": "invalid_evidence", "confirmed": False}
    return result


def markdown(scorecard: dict) -> str:
    h = scorecard["historical"]
    r = scorecard["random_baseline"]
    c = scorecard["calibration"]
    p = scorecard["reference_payout"]
    f = scorecard["future_oos"]
    fmt = lambda x, digits=6: "未確認" if x is None else f"{x:+.{digits}f}"
    lines = [
        "# LOTO7 予測指標の分離レポート",
        "",
        "> 読み取り専用。過去結果、ランダム比較、確率予測、参考払戻を混ぜずに表示します。",
        f"- 過去の一致数: {h['status']}",
        f"- ランダム対照: {r['status']}",
        f"- 確率校正: {c['status']}",
        f"- 参考払戻: {p['status']}",
        f"- 将来検証: {f['status']}",
        "",
    ]
    if h["status"] == "historical_only":
        lines.extend([f"## 過去の一致数（第{h['start_round']}〜{h['end_round']}回・{h['rounds']}回）",
                      f"- Top7平均: {h['top7_mean_hits']:.6f}個",
                      f"- 公平抽せん理論: {h['uniform_expected_hits']:.6f}個",
                      f"- 差: {fmt(h['top7_delta_vs_uniform'])}個。探索的p値は確認的証拠ではありません。",
                      ""])
    if r["status"] == "historical_only":
        lines.extend(["## 同条件ランダム対照（過去検証のみ）",
                      f"- 5口最大一致の平均差: {fmt(r['mean_max_hits_delta'])}個",
                      f"- 複合スコア差: {fmt(r['mean_score_delta'])}",
                      f"- 各回のランダム比較ポートフォリオ数: {r['random_portfolios_per_round']}",
                      ""])
    if c["status"] == "descriptive_only":
        lines.extend([f"## 事前凍結の確率予測（{c['trusted_draws']}/{c['horizon_draws']}回）",
                      f"- 一様予測比の平均対数スコア改善: {fmt(c['mean_log_improvement_vs_uniform'], 8)}",
                      f"- 一様予測比の平均Brier改善: {fmt(c['mean_brier_improvement_vs_uniform'], 8)}",
                      "- 正の改善値は小さいほど良い損失関数に対する改善を意味します。",
                      "- ECE・reliability binsは未計算。適切な校正が立証された意味ではありません。",
                      ""])
    if p["status"] == "historical_hypothetical_only":
        lines.extend(["## 参考払戻（実購入利益ではない）",
                      f"- {p['tickets']}口 / 参考購入費 {p['reference_cost_yen']:,}円 / 公表配当参考払戻 {p['reference_payout_yen']:,}円",
                      f"- 参考収支 {p['reference_net_yen']:,}円 / 参考回収率 {p['reference_roi']:.2%}",
                      "- 公表当選額による仮定上の試算であり、実際の販売・実現損益ではありません。",
                      ""])
    lines.extend(["## 将来OOSの判定範囲",
                  f"- 状態: {f['status']} / 正式な予測力の証明: 未確認",
                  "- 過去指標と異なるモデル・期間の数値を結合して優位性を主張しません。",
                  ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    scorecard = build_scorecard(args.out_dir)
    body = (json.dumps(scorecard, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            if args.format == "json" else markdown(scorecard))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    else:
        print(body)


if __name__ == "__main__":
    main()
