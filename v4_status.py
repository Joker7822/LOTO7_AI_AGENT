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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", type=Path, default=Path("STATUS.md"))
    ap.add_argument("--state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--pool", type=Path, default=Path("loto7_agent_output/candidate_pool.json"))
    ap.add_argument("--registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    ap.add_argument("--oos", type=Path, default=Path("loto7_agent_output/oos_candidate_state.json"))
    ap.add_argument("--metrics", type=Path, default=Path("loto7_agent_output/execution_metrics.csv"))
    args = ap.parse_args()

    state = load(args.state)
    pool = load(args.pool)
    registry = load(args.registry)
    oos = load(args.oos)
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
