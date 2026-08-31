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


def _rank_lines(rec, holdout, size: int):
    draws = int(rec.get("matched_ensemble_rank_trusted_draws", 0) or 0)
    hdraws = int(holdout.get("matched_ensemble_rank_trusted_draws", 0) or 0)
    minimum_p = float(
        rec.get(
            "matched_ensemble_rank_minimum_possible_p",
            holdout.get("matched_ensemble_rank_minimum_possible_p", 1.0 / (max(1, size) + 1.0)),
        )
        or (1.0 / (max(1, size) + 1.0))
    )
    lines = [
        "- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**",
        f"- 単回Monte-Carlo permutation p最小値: **{minimum_p:.4f}** (= 1/{max(1, size) + 1})",
    ]
    if draws:
        mean_pct = float(rec.get("matched_ensemble_rank_percentile_sum", 0.0) or 0.0) / draws
        mean_p = float(rec.get("matched_ensemble_rank_permutation_p_sum", 0.0) or 0.0) / draws
        last_pct = float(rec.get("last_matched_ensemble_rank_percentile_midrank", 0.0) or 0.0)
        last_p = float(rec.get("last_matched_ensemble_rank_permutation_p_upper", 1.0) or 1.0)
        last_rank = float(rec.get("last_matched_ensemble_rank_midrank_from_top", 0.0) or 0.0)
        last_round = rec.get("last_matched_ensemble_rank_rank_round", "?")
        below = int(rec.get("last_matched_ensemble_rank_null_below", 0) or 0)
        equal = int(rec.get("last_matched_ensemble_rank_null_equal", 0) or 0)
        above = int(rec.get("last_matched_ensemble_rank_null_above", 0) or 0)
        lines += [
            f"- Rank診断 trusted OOS: **{draws}/8回**",
            f"- 直近(第{last_round}回) percentile / MC p: **{last_pct:.2f}% / {last_p:.4f}**",
            f"- 直近 observed+null rank: **{last_rank:.1f}/{size + 1}位相当** (null below/equal/above = {below}/{equal}/{above})",
            f"- trusted平均 percentile / 単回MC p平均: **{mean_pct:.2f}% / {mean_p:.4f}**",
        ]
    else:
        lines += [
            "- Rank診断 trusted OOS: **0/8回**",
            "- 直近 percentile / MC p / rank: **未採点**",
        ]

    if hdraws:
        hmean_pct = float(holdout.get("matched_ensemble_rank_percentile_sum", 0.0) or 0.0) / hdraws
        hmean_p = float(holdout.get("matched_ensemble_rank_permutation_p_sum", 0.0) or 0.0) / hdraws
        hlast_pct = float(holdout.get("last_matched_ensemble_rank_percentile_midrank", 0.0) or 0.0)
        hlast_p = float(holdout.get("last_matched_ensemble_rank_permutation_p_upper", 1.0) or 1.0)
        hlast_rank = float(holdout.get("last_matched_ensemble_rank_midrank_from_top", 0.0) or 0.0)
        hlast_round = holdout.get("last_matched_ensemble_rank_rank_round", "?")
        lines += [
            f"- Holdout Rank診断: **{hdraws}/26 trusted draws**",
            f"- Holdout直近(第{hlast_round}回) percentile / MC p / rank: **{hlast_pct:.2f}% / {hlast_p:.4f} / {hlast_rank:.1f}/{size + 1}位相当**",
            f"- Holdout平均 percentile / 単回MC p平均: **{hmean_pct:.2f}% / {hmean_p:.4f}**",
        ]
    else:
        lines.append("- Holdout Rank診断: **0/26 trusted draws（未採点）**")
    return lines


def _audit_lines(registry, oos, rec, holdout, holdout_registry, candidate: str):
    ref_hashes = registry.get("matched_ensemble_reference_sha256_by_candidate")
    ref_hashes = ref_hashes if isinstance(ref_hashes, dict) else {}
    ref_hash = str(ref_hashes.get(candidate, ""))
    holdout_ref = str(holdout_registry.get("matched_ensemble_reference_sha256", ""))
    audit_status = str(
        rec.get(
            "matched_ensemble_score_vector_audit_status",
            oos.get("matched_ensemble_score_vector_audit_status", "未初期化"),
        )
    )
    lines = [
        "",
        "### Ensemble Score Vector Audit",
        "",
        f"- Score vector監査版: **{oos.get('matched_ensemble_score_vector_audit_version', registry.get('matched_ensemble_score_vector_audit_version', '未初期化'))}**",
        f"- Hash: **{oos.get('matched_ensemble_score_vector_hash_algorithm', registry.get('matched_ensemble_score_vector_hash_algorithm', '未設定'))}**",
        f"- canonical float: **{oos.get('matched_ensemble_score_vector_canonical_float', registry.get('matched_ensemble_score_vector_canonical_float', '未設定'))} binary64 round-trip decimal string**",
        "- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**",
        f"- Formal 32-member reference SHA-256事前確定: **{'YES' if ref_hash else 'NO'}**",
        f"- Formal reference SHA-256: **{ref_hash or '未確定'}**",
        f"- Holdout 32-member reference SHA-256事前確定: **{'YES' if holdout_ref else 'NO'}**",
        f"- Holdout reference SHA-256: **{holdout_ref or '未確定'}**",
        f"- Formal score vector audit status: **{audit_status}**",
    ]
    last_vector = str(rec.get("last_matched_ensemble_score_vector_sha256", ""))
    last_record = str(rec.get("last_matched_ensemble_audit_record_sha256", ""))
    last_round = rec.get("last_matched_ensemble_score_vector_audit_round")
    if last_vector:
        lines += [
            f"- 直近score vector: **第{last_round}回 / SHA-256 {last_vector}**",
            f"- 直近audit record SHA-256: **{last_record or '確認できません'}**",
            f"- 直近rank/p replay一致: **{'YES' if rec.get('last_matched_ensemble_score_vector_replay_verified') else 'NO'}**",
        ]
    else:
        lines.append("- 直近score vector / audit record: **未採点**")
    hlast_vector = str(holdout.get("last_matched_ensemble_score_vector_sha256", ""))
    if hlast_vector:
        lines += [
            f"- Holdout直近score vector SHA-256: **{hlast_vector}**",
            f"- Holdout直近rank/p replay一致: **{'YES' if holdout.get('last_matched_ensemble_score_vector_replay_verified') else 'NO'}**",
        ]
    else:
        lines.append("- Holdout score vector / audit record: **未採点**")
    return lines


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
    lines = [
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
        "### Ensemble Rank Diagnostics",
        "",
        f"- Rank診断版: **{oos.get('matched_ensemble_rank_diagnostics_version', holdout.get('matched_ensemble_rank_diagnostics_version', '未初期化'))}**",
        "- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**",
    ]
    lines += _rank_lines(rec, holdout, size or 32)
    lines += _audit_lines(registry, oos, rec, holdout, holdout_registry, candidate)
    lines.append("")
    return lines


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
