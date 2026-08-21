#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", type=Path, default=Path("STATUS.md"))
    ap.add_argument("--state", type=Path, default=Path("loto7_agent_output/evolution_state.json"))
    ap.add_argument("--evaluation", type=Path, default=Path("loto7_agent_output/model_evaluation.json"))
    args = ap.parse_args()

    state = load(args.state)
    ev = load(args.evaluation)
    base = args.status.read_text(encoding="utf-8") if args.status.exists() else "# LOTO7 AI Agent Status\n"
    markers = ("\n## Intraday Evolution v3\n", "\n## Daily Evolution v3\n")
    for marker in markers:
        if marker in base:
            base = base.split(marker, 1)[0].rstrip() + "\n"
            break

    promoted = "YES" if state.get("total_promotions") and ev.get("promoted") else "NO"
    locked = "YES" if state.get("promotion_locked_for_data_sha") else "NO"
    section = f"""
## Intraday Evolution v3

- 進化世代: **{state.get('generation', '確認できません')}**
- 同一データでの反復検証回数: **{state.get('data_day_index', '確認できません')}**
- Champion: **{state.get('champion_version', '確認できません')}**
- 最新研究Winner: **{state.get('research_winner', '確認できません')}**
- 今回のChampion昇格: **{promoted}**
- 同一データSHAでの追加昇格ロック: **{locked}**
- 累積Challenger評価数: **{state.get('total_evaluations', 0)}**
- 累積Champion昇格数: **{state.get('total_promotions', 0)}**
- 今回の候補あたり有意水準: **{state.get('per_candidate_alpha', '確認できません')}**
- 進化履歴ハッシュ: `{state.get('last_history_hash', '')}`

> 1日4回Challenger世代を生成・バックテストします。同じ抽せんデータに対する反復検定は実行のたびにalpha-spendingで厳格化し、Championは同一データSHAにつき最大1回だけ昇格できます。
"""
    args.status.write_text(base.rstrip() + "\n" + section, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())