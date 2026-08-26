#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List

import loto7_v2_runner as v2
import loto7_v4_runner as v4
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "weekly-production-publisher-v1"


def read_tickets(path: Path) -> List[str]:
    if not path.exists():
        return []
    out: List[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            numbers = str(row.get("numbers", "")).strip()
            if numbers:
                out.append(numbers)
    return out


def render_latest_prediction(state: Dict[str, object], tickets: List[str], generated_at: str) -> str:
    lines = [
        "LOTO7 最新予測",
        "=" * 56,
        f"対象回: {state.get('target_round', '')}",
        f"予測基準: {state.get('latest_round', '')} / {state.get('latest_draw_date', '')}",
        f"予測作成(JST): {generated_at}",
        f"モデル: {state.get('model_version', '')}",
        "",
    ]
    for i, numbers in enumerate(tickets, 1):
        lines.append(f"{i}. {numbers}")
    return "\n".join(lines) + "\n"


def current_production_is_frozen_and_current(
    out_dir: Path, data_sha: str, champion_version: str
) -> bool:
    state = v4.load_json(out_dir / "agent_state.json", {})
    return bool(
        state.get("model_version") == champion_version
        and state.get("data_sha256") == data_sha
        and (out_dir / "candidate_tickets.csv").exists()
        and (out_dir / "latest_prediction.txt").exists()
    )


def publish(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    champion_file: Path = Path("loto7_agent_output/model_champion.json"),
    research_state: Path = Path("loto7_agent_output/v4_research_state.json"),
    min_train: int = 100,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    champion = v2.load_champion(champion_file)
    research = v4.load_json(research_state, {})
    generation = int(research.get("generation", 0))
    checked_at = v4.now_jst()

    # Preserve an already-frozen Production artifact byte-for-byte. This is
    # especially important for the legacy v1 round-692 Production forecast.
    if current_production_is_frozen_and_current(out_dir, data_sha, champion.version()):
        result = {
            "report_version": REPORT_VERSION,
            "checked_at_jst": checked_at,
            "published": False,
            "reason": "current_frozen_production_preserved",
            "data_sha256": data_sha,
            "model_version": champion.version(),
        }
        v4.write_json(out_dir / "weekly_production_prediction_state.json", result)
        return result

    production = v4.ensure_production_outputs(
        x,
        clean,
        champion,
        out_dir,
        min_train,
        data_sha,
        os.environ.get("GITHUB_SHA", "local"),
        generation,
        force=False,
        promotion=None,
    )
    state = production.get("state") if isinstance(production.get("state"), dict) else {}
    tickets = read_tickets(out_dir / "candidate_tickets.csv")
    if len(tickets) != 5:
        raise RuntimeError(f"expected exactly 5 Production tickets, got {len(tickets)}")

    generated_at = v4.now_jst()
    (out_dir / "latest_prediction.txt").write_text(
        render_latest_prediction(state, tickets, generated_at), encoding="utf-8"
    )
    result = {
        "report_version": REPORT_VERSION,
        "checked_at_jst": checked_at,
        "published_at_jst": generated_at,
        "published": True,
        "data_sha256": data_sha,
        "model_version": champion.version(),
        "target_round": state.get("target_round"),
        "schedule_policy": "Friday 17:00 JST only",
        "production_promotion_method": "future_oos_only",
    }
    v4.write_json(out_dir / "weekly_production_prediction_state.json", result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish frozen Production prediction at the weekly Friday 17:00 JST slot")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    args = ap.parse_args()
    result = publish(args.csv, args.out_dir, args.champion_file, args.research_state, args.min_train)
    print(f"[WEEKLY-PRODUCTION] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
