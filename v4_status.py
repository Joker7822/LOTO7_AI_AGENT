#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def metrics_summary(path: Path):
    if not path.exists():
        return 0, None, None
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    vals = []
    for r in rows:
        try:
            vals.append(int(r.get("duration_seconds", "")))
        except ValueError:
            pass
    if not vals:
        return len(rows), None, None
    recent = vals[-20:]
    return len(vals), vals[-1], sum(recent) / len(recent)


def best_evidence(oos, champion):
    evidence = oos.get("evidence") if isinstance(oos.get("evidence"), dict) else {}
    candidates = []
    for rec in evidence.values():
        if not isinstance(rec, dict) or rec.get("champion_version") != champion:
            continue
        draws = int(rec.get("trusted_draws", 0))
        mean_delta = float(rec.get("sum_delta", 0.0)) / max(1, draws) if draws else 0.0
        win_rate = float(rec.get("wins", 0)) / max(1, draws) if draws else 0.0
        candidates.append((float(rec.get("e_value", 1.0)), draws, mean_delta, win_rate, rec))
    return max(candidates, default=None, key=lambda x: (x[0], x[2], x[1]))


def historical_lines(hist):
    if not hist:
        return ["- 過去回replay: **未生成**"]
    top = hist.get("top7") if isinstance(hist.get("top7"), dict) else {}
    pf = hist.get("portfolio_5_tickets") if isinstance(hist.get("portfolio_5_tickets"), dict) else {}
    prizes = hist.get("prize_grades") if isinstance(hist.get("prize_grades"), dict) else {}
    return [
        f"- 評価回数: **{hist.get('evaluated_rounds', 0)}回** ({hist.get('first_evaluated_round', '?')}〜{hist.get('last_evaluated_round', '?')})",
        f"- Top7平均本数字一致: **{float(top.get('mean_hits', 0.0)):.4f}** / random **{float(top.get('random_theoretical_mean_hits', 0.0)):.4f}**",
        f"- Top7近似両側p: **{float(top.get('approx_two_sided_p', 1.0)):.6f}** / 判定 **{top.get('signal_claim', '確認できません')}**",
        f"- 5口平均最大一致: **{float(pf.get('mean_max_hits', 0.0)):.4f}** / random **{float(pf.get('random_mean_max_hits', 0.0)):.4f}**",
        f"- 5口平均score差 vs random: **{float(pf.get('mean_score_delta_vs_random', 0.0)):+.4f}**",
        f"- 3個以上一致券あり: **{float(pf.get('ge3_round_rate', 0.0))*100:.1f}%** / random **{float(pf.get('random_ge3_round_rate', 0.0))*100:.1f}%**",
        f"- 4個以上一致券あり: **{float(pf.get('ge4_round_rate', 0.0))*100:.1f}%** / random **{float(pf.get('random_ge4_round_rate', 0.0))*100:.1f}%**",
        f"- 何らかの等級当選があった回: **{float(prizes.get('rounds_with_any_prize_rate', 0.0))*100:.2f}%**",
        "- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**",
    ]


def reconciliation_lines(rec):
    if not rec:
        return ["- 独立照合: **未生成**"]
    integrity = rec.get("integrity") if isinstance(rec.get("integrity"), dict) else {}
    return [
        f"- 独立再照合: **{rec.get('evaluated_rounds', 0)}回 / {rec.get('evaluated_tickets', 0)}口**",
        f"- 当選口数: **{rec.get('winning_tickets', 0)}口** ({float(rec.get('winning_ticket_rate', 0.0))*100:.3f}%)",
        f"- 参考購入額: **{int(rec.get('purchase_cost_yen', 0)):,}円**",
        f"- 公表当選額ベース参考払戻: **{int(rec.get('published_reference_payout_yen', 0)):,}円**",
        f"- 参考回収率: **{float(rec.get('published_reference_roi', 0.0))*100:.2f}%**",
        f"- 予測側実績とloto7.csvの不一致: **{int(integrity.get('mismatches', 0))}件**",
    ]


def nested_lines(nested):
    if not nested:
        return ["- Nested replay: **未生成**"]
    c = nested.get("champion_reference") if isinstance(nested.get("champion_reference"), dict) else {}
    r = nested.get("nested_research") if isinstance(nested.get("nested_research"), dict) else {}
    rnd = nested.get("random_reference") if isinstance(nested.get("random_reference"), dict) else {}
    dc = r.get("score_delta_vs_champion") if isinstance(r.get("score_delta_vs_champion"), dict) else {}
    dr = r.get("score_delta_vs_random") if isinstance(r.get("score_delta_vs_random"), dict) else {}
    return [
        f"- Nested評価回数: **{nested.get('evaluated_rounds', 0)}回** ({nested.get('first_round', '?')}〜{nested.get('last_round', '?')})",
        f"- 平均score Champion / Research / Random: **{float(c.get('mean_score', 0.0)):.4f} / {float(r.get('mean_score', 0.0)):.4f} / {float(rnd.get('mean_score', 0.0)):.4f}**",
        f"- Research差 vs Champion: **{float(dc.get('mean', 0.0)):+.4f}** (95% CI {float(dc.get('low95', 0.0)):+.4f}〜{float(dc.get('high95', 0.0)):+.4f})",
        f"- Research差 vs Random: **{float(dr.get('mean', 0.0)):+.4f}** (95% CI {float(dr.get('low95', 0.0)):+.4f}〜{float(dr.get('high95', 0.0)):+.4f})",
        f"- Research勝率 vs Champion / Random: **{float(r.get('round_win_rate_vs_champion', 0.0))*100:.1f}% / {float(r.get('round_win_rate_vs_random', 0.0))*100:.1f}%**",
        "- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", type=Path, default=Path("STATUS.md"))
    ap.add_argument("--state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--pool", type=Path, default=Path("loto7_agent_output/candidate_pool.json"))
    ap.add_argument("--registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    ap.add_argument("--oos", type=Path, default=Path("loto7_agent_output/oos_candidate_state.json"))
    ap.add_argument("--metrics", type=Path, default=Path("loto7_agent_output/execution_metrics.csv"))
    ap.add_argument("--historical", type=Path, default=Path("loto7_agent_output/historical_replay_summary.json"))
    ap.add_argument("--reconciliation", type=Path, default=Path("loto7_agent_output/historical_reconciliation_summary.json"))
    ap.add_argument("--nested", type=Path, default=Path("loto7_agent_output/nested_replay_summary.json"))
    args = ap.parse_args()

    state = load(args.state)
    pool = load(args.pool)
    registry = load(args.registry)
    oos = load(args.oos)
    historical = load(args.historical)
    reconciliation = load(args.reconciliation)
    nested = load(args.nested)
    champion = str(state.get("champion_version", ""))
    pool_n = len(pool.get("candidates", []) or [])
    shadow_n = len(registry.get("candidates", []) or [])
    total, latest, avg = metrics_summary(args.metrics)
    best = best_evidence(oos, champion)

    base = args.status.read_text(encoding="utf-8") if args.status.exists() else "# LOTO7 AI Agent Status\n"
    lines = [base.rstrip(), "", "## Continuous Research v4", ""]
    lines += [
        f"- 研究世代: **{state.get('generation', 0)}**",
        f"- Production Champion: **{champion or '確認できません'}**",
        f"- 最新Research Winner: **{state.get('research_winner', '確認できません')}**",
        f"- 候補プール: **{pool_n}モデル**",
        f"- 累積研究評価数: **{state.get('total_research_evaluations', 0)}**",
        "- 過去データの研究スコアから本番昇格: **無効（禁止）**",
        f"- 現在ソース検証: **{state.get('source_verification', '確認できません')}**",
        f"- 本番昇格に利用可能なソース: **{'YES' if state.get('source_trusted_for_promotion') else 'NO'}**",
        "",
        "## Historical Replay Accuracy",
        "",
    ]
    lines += historical_lines(historical)
    lines += ["", "## Historical Reconciliation", ""]
    lines += reconciliation_lines(reconciliation)
    lines += ["", "## Nested Champion / Research / Random", ""]
    lines += nested_lines(nested)
    lines += [
        "",
        "## OOS Governance v4",
        "",
        f"- 凍結済みshadow対象回: **第{registry.get('target_round', '確認できません')}回**",
        f"- 凍結shadow候補数: **{shadow_n}**",
        f"- 最終OOS採点回: **{oos.get('last_graded_round', 'なし')}**",
        f"- 累積Champion昇格数: **{state.get('total_promotions', 0)}**",
        "- 昇格条件: **信頼済み未来OOS 8回以上 / e-value ≥ 20 / 平均score差 ≥ 0.05 / 勝率 ≥ 55%**",
    ]
    if best:
        evalue, draws, mean_delta, win_rate, rec = best
        lines += [
            f"- 現Championに対する最有力shadow: **{rec.get('candidate_version', '')}**",
            f"- 信頼済みOOS回数: **{draws}**",
            f"- e-value: **{evalue:.4f}**",
            f"- 平均score差: **{mean_delta:.4f}**",
            f"- OOS勝率: **{win_rate*100:.1f}%**",
        ]
    else:
        lines.append("- 現Championに対するOOS証拠: **まだ蓄積なし**")

    lines += ["", "## Continuous Runtime", ""]
    if latest is None:
        lines.append("- 実測: **まだありません**")
    else:
        lines += [
            f"- 最新1回の研究実行時間: **{latest}秒**",
            f"- 直近20回平均: **{avg:.1f}秒**",
            f"- 累積実測回数: **{total}回**",
            "- 実行方式: **終了後、待ち時間なしで次の研究世代へ**",
            "- Git checkpoint: **10世代ごと、または重要イベント発生時**",
        ]
    args.status.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
