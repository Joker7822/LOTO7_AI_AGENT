#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def find_evidence(oos, candidate_version: str, champion_version: str):
    evidence = oos.get("evidence") if isinstance(oos.get("evidence"), dict) else {}
    for rec in evidence.values():
        if not isinstance(rec, dict):
            continue
        if candidate_version and rec.get("candidate_version") != candidate_version:
            continue
        if champion_version and rec.get("champion_version") != champion_version:
            continue
        return rec
    return {}


def render(registry, oos, formal, holdout, holdout_registry):
    size = int(registry.get("matched_ensemble_size", 0) or 0)
    candidate = str(formal.get("candidate_version", ""))
    champion = str(formal.get("champion_version", registry.get("champion_version", "")))
    rec = find_evidence(oos, candidate, champion)
    draws = int(rec.get("matched_ensemble_trusted_draws", 0) or 0)
    mean_delta = (
        float(rec.get("matched_ensemble_sum_delta", 0.0) or 0.0) / max(1, draws)
        if draws else 0.0
    )
    win_rate = (
        float(rec.get("matched_ensemble_wins", 0) or 0) / max(1, draws)
        if draws else 0.0
    )
    hdraws = int(holdout.get("matched_ensemble_trusted_draws", 0) or 0)
    horizon = int(holdout.get("horizon_trusted_draws", 26) or 26)
    hmean = (
        float(holdout.get("sum_delta_vs_matched_ensemble", 0.0) or 0.0) / max(1, hdraws)
        if hdraws else 0.0
    )
    hwin = (
        float(holdout.get("wins_vs_matched_ensemble", 0) or 0) / max(1, hdraws)
        if hdraws else 0.0
    )
    return [
        "## Matched Permutation Ensemble",
        "",
        f"- Ensemble版: **{registry.get('matched_ensemble_version', oos.get('matched_ensemble_version', '未凍結'))}**",
        f"- Ensemble size: **{size}**",
        f"- Promotionで使用: **{'YES' if size == 32 and registry.get('matched_ensemble_frozen_at_jst') else 'NO'}**",
        f"- 第{registry.get('target_round', '?')}回事前凍結: **{'YES' if registry.get('matched_ensemble_frozen_at_jst') else 'NO'}**",
        f"- Ensemble凍結日時(JST): **{registry.get('matched_ensemble_frozen_at_jst', '未凍結')}**",
        f"- member 0（旧single comparator）凍結日時(JST): **{registry.get('matched_reference_frozen_at_jst', '未凍結')}**",
        "- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**",
        "- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**",
        "- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**",
        f"- Ensemble trusted OOS: **{draws}/8回**",
        f"- 平均score差 vs Matched Ensemble: **{mean_delta:+.4f}**",
        f"- 勝率 vs Matched Ensemble: **{win_rate*100:.1f}%**",
        f"- raw e-value vs Matched Ensemble: **{float(rec.get('matched_ensemble_e_value_raw', 1.0)):.4f}**",
        f"- family-adjusted intersection e-value: **{float(rec.get('family_adjusted_e_value', rec.get('e_value', 0.0)) or 0.0):.4f}** / threshold **20.0000**",
        f"- Holdout Ensemble進捗: **{hdraws}/{horizon} trusted draws**",
        f"- Holdout平均score差 vs Matched Ensemble: **{hmean:+.4f}**",
        f"- Holdout勝率 vs Matched Ensemble: **{hwin*100:.1f}%**",
        f"- Holdout e-value vs Matched Ensemble: **{float(holdout.get('matched_ensemble_e_value', 1.0)):.4f}**",
        f"- Holdout Ensemble凍結: **{'YES' if holdout_registry.get('matched_ensemble_frozen_at_jst') else 'NO'}**",
        "",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", type=Path, default=Path("STATUS.md"))
    ap.add_argument("--registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    ap.add_argument("--oos", type=Path, default=Path("loto7_agent_output/oos_candidate_state.json"))
    ap.add_argument("--formal", type=Path, default=Path("loto7_agent_output/formal_challenger_state.json"))
    ap.add_argument("--holdout-state", type=Path, default=Path("loto7_agent_output/future_holdout_state.json"))
    ap.add_argument("--holdout-registry", type=Path, default=Path("loto7_agent_output/future_holdout_registry.json"))
    args = ap.parse_args()

    text = args.status.read_text(encoding="utf-8") if args.status.exists() else "# LOTO7 AI Agent Status\n"
    marker = "\n## Matched Permutation Ensemble\n"
    if marker in text:
        before, after = text.split(marker, 1)
        next_header = after.find("\n## ")
        text = before + (after[next_header:] if next_header >= 0 else "\n")

    text = text.replace(
        "Champion・事前凍結Random・geometry-matched permutation nullの全てに勝つことを要求",
        "Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求",
    )
    text = text.replace(
        "Champion・Random・Matched permutationの全てで満たす",
        "Champion・Random・Matched Ensemble(32)の全てで満たす",
    )

    registry = load(args.registry)
    oos = load(args.oos)
    formal = load(args.formal)
    holdout = load(args.holdout_state)
    holdout_registry = load(args.holdout_registry)
    section = "\n".join(render(registry, oos, formal, holdout, holdout_registry))

    insert_before = "\n## Fixed Prospective Holdout\n"
    if insert_before in text:
        left, right = text.split(insert_before, 1)
        text = left.rstrip() + "\n\n" + section.rstrip() + "\n" + insert_before + right
    else:
        text = text.rstrip() + "\n\n" + section
    args.status.write_text(text.rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
