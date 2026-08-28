#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import audit_ledger as ledger
import loto7_v2_runner as v2
import loto7_v4_runner as v4
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "weekly-production-publisher-v3-ledger-canonical"


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


def current_production_outputs_are_current(
    out_dir: Path,
    data_sha: str,
    champion_version: str,
    expected_latest_round: Optional[int] = None,
    expected_target_round: Optional[int] = None,
) -> bool:
    state = v4.load_json(out_dir / "agent_state.json", {})
    tickets = read_tickets(out_dir / "candidate_tickets.csv")
    ok = bool(
        state.get("model_version") == champion_version
        and state.get("data_sha256") == data_sha
        and len(tickets) == 5
    )
    if expected_latest_round is not None:
        ok = ok and v4.parse_round(state.get("latest_round")) == expected_latest_round
    if expected_target_round is not None:
        ok = ok and v4.parse_round(state.get("target_round")) == expected_target_round
    return bool(ok)


def current_production_is_frozen_and_current(
    out_dir: Path, data_sha: str, champion_version: str
) -> bool:
    return current_production_outputs_are_current(out_dir, data_sha, champion_version)


def _frozen_target_rows(out_dir: Path, target_round: int) -> List[Dict[str,str]]:
    preds = out_dir / "predictions.csv"
    corrections = out_dir / "prediction_corrections.csv"
    rows = [
        r for r in ledger.active_prediction_rows(preds, corrections)
        if ledger.rno(r.get("target_round", "")) == target_round
    ]
    rows.sort(key=lambda r: int(r.get("ticket") or 999))
    if rows and len(rows) != 5:
        raise RuntimeError(
            f"frozen Production target 第{target_round}回 has {len(rows)} active tickets; expected 5"
        )
    return rows


def publish(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    champion_file: Path = Path("loto7_agent_output/model_champion.json"),
    research_state: Path = Path("loto7_agent_output/v4_research_state.json"),
    min_train: int = 100,
    republish_only: bool = False,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    loto_rows = ledger.read_csv(csv_path)
    data_sha = fingerprint_file(csv_path)
    champion = v2.load_champion(champion_file)
    research = v4.load_json(research_state, {})
    generation = int(research.get("generation", 0))
    checked_at = v4.now_jst()

    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    latest_round = v4.parse_round(latest_round_text) or int(len(clean))
    target_round = latest_round + 1

    preds = out_dir / "predictions.csv"
    corrections = out_dir / "prediction_corrections.csv"
    ledger.append_prediction_invalidations(loto_rows, preds, corrections, data_sha)

    frozen = _frozen_target_rows(out_dir, target_round)
    if frozen:
        (out_dir / "latest_prediction.txt").write_text(
            ledger.render_latest(preds, corrections, latest_round),
            encoding="utf-8",
        )
        result = {
            "report_version": REPORT_VERSION,
            "checked_at_jst": checked_at,
            "published_at_jst": checked_at,
            "published": True,
            "reason": "republished_frozen_ledger_prediction",
            "data_sha256": data_sha,
            "model_version": frozen[0].get("model_version", ""),
            "target_round": f"第{target_round}回",
            "schedule_policy": "Friday 15:00 JST",
            "production_promotion_method": "future_oos_only",
        }
        v4.write_json(out_dir / "weekly_production_prediction_state.json", result)
        return result

    if republish_only:
        (out_dir / "latest_prediction.txt").write_text(
            ledger.render_latest(preds, corrections, latest_round),
            encoding="utf-8",
        )
        result = {
            "report_version": REPORT_VERSION,
            "checked_at_jst": checked_at,
            "published": False,
            "reason": "no_frozen_prediction_to_republish",
            "data_sha256": data_sha,
            "model_version": champion.version(),
            "target_round": f"第{target_round}回",
            "schedule_policy": "Friday 15:00 JST",
            "production_promotion_method": "future_oos_only",
        }
        v4.write_json(out_dir / "weekly_production_prediction_state.json", result)
        return result

    reused_current_outputs = current_production_outputs_are_current(
        out_dir,
        data_sha,
        champion.version(),
        expected_latest_round=latest_round,
        expected_target_round=target_round,
    )
    if reused_current_outputs:
        state = v4.load_json(out_dir / "agent_state.json", {})
    else:
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

    if state.get("data_sha256") != data_sha:
        raise RuntimeError("refusing weekly Production freeze: agent_state data SHA is stale")
    if v4.parse_round(state.get("latest_round")) != latest_round:
        raise RuntimeError("refusing weekly Production freeze: agent_state latest round is stale")
    if v4.parse_round(state.get("target_round")) != target_round:
        raise RuntimeError("refusing weekly Production freeze: agent_state target round mismatch")

    ticket_rows = ledger.read_csv(out_dir / "candidate_tickets.csv")
    added = ledger.append_current_predictions(
        loto_rows,
        ticket_rows,
        preds,
        state,
        current_data_sha=data_sha,
        corrections=corrections,
        created_at=checked_at,
    )
    if added != 5:
        raise RuntimeError(f"expected to freeze 5 new Production tickets, froze {added}")

    frozen = _frozen_target_rows(out_dir, target_round)
    if len(frozen) != 5:
        raise RuntimeError("Production ledger freeze did not produce exactly 5 active tickets")

    (out_dir / "latest_prediction.txt").write_text(
        ledger.render_latest(preds, corrections, latest_round),
        encoding="utf-8",
    )
    result = {
        "report_version": REPORT_VERSION,
        "checked_at_jst": checked_at,
        "published_at_jst": checked_at,
        "published": True,
        "reason": "frozen_to_canonical_prediction_ledger",
        "data_sha256": data_sha,
        "model_version": frozen[0].get("model_version", champion.version()),
        "target_round": f"第{target_round}回",
        "schedule_policy": "Friday 15:00 JST",
        "production_promotion_method": "future_oos_only",
    }
    v4.write_json(out_dir / "weekly_production_prediction_state.json", result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Publish Production prediction at the weekly Friday 15:00 JST slot"
    )
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument(
        "--champion-file",
        type=Path,
        default=Path("loto7_agent_output/model_champion.json"),
    )
    ap.add_argument(
        "--research-state",
        type=Path,
        default=Path("loto7_agent_output/v4_research_state.json"),
    )
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument(
        "--republish-only",
        action="store_true",
        help="Re-publish an already-frozen Production target; never create a new forecast.",
    )
    args = ap.parse_args()
    result = publish(
        args.csv,
        args.out_dir,
        args.champion_file,
        args.research_state,
        args.min_train,
        republish_only=args.republish_only,
    )
    print(f"[WEEKLY-PRODUCTION] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
