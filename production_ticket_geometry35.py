#!/usr/bin/env python3
"""Production ticket-layout policy for *new* targets 702+, separate from Champion.

A fair 7-of-37 draw has no learned predictable signal. This explicit user
authorized change only replaces the five-ticket *geometry* at the canonical
weekly publication boundary. The Champion, pre-existing freezes, and strict
Future-OOS evidence are not modified or promoted.

Never call from a research checkpoint or while drawing data is untrusted.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from balanced_uniform_portfolio import disjoint_portfolio, validate_portfolio
from joint_set_v2_signal_oos_guard import validate_trusted_source
import loto7_v4_runner as v4
from loto7_evolving_agent import fingerprint_file

VERSION = "production-disjoint35-layout-v1"
MIN_TARGET_ROUND = 702
SEED_BASE = 10_000_000
SEED_MULTIPLIER = 1009
JST = timezone(timedelta(hours=9))


def production_window_guard(now: datetime) -> None:
    local = now.astimezone(JST)
    hour_min = local.hour * 100 + local.minute
    if local.weekday() != 4 or not (1300 <= hour_min < 2000):
        raise RuntimeError("refusing disjoint35 Production outside Friday 13:00-19:59 JST")


def verify_source(csv_path: Path, source_path: Path,
                  expected_latest_round: int) -> dict:
    """Require two-source trusted latest draw and exact current CSV SHA."""
    verified = validate_trusted_source(csv_path, source_path)
    if not verified.get("trusted") or verified.get("round") != expected_latest_round:
        raise RuntimeError("refusing geometry35 Production without two-source verification")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    provenance = source.get("verification_provenance") or {}
    canonical_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if provenance.get("draw_csv_sha256") != canonical_sha:
        raise RuntimeError("refusing geometry35 Production with stale CSV fingerprint")
    return verified


def portfolio_for_target(target_round: int) -> list[tuple[int, ...]]:
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("cannot change an existing/frozen target before round 702")
    tickets = disjoint_portfolio(SEED_BASE + target_round * SEED_MULTIPLIER)
    validate_portfolio(tickets)
    return tickets


def render_ticket_csv(tickets: list[tuple[int, ...]]) -> str:
    validate_portfolio(tickets)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["ticket", "numbers", "sum", "odd_count"])
    for i, ticket in enumerate(tickets, 1):
        writer.writerow([i, " ".join(f"{n:02d}" for n in ticket),
                         sum(ticket), sum(n % 2 for n in ticket)])
    return "\ufeff" + stream.getvalue()


def prepare_new_production_outputs(
    *, csv_path: Path, out_dir: Path, champion_version: str,
    data_sha: str, latest_round: int, target_round: int,
    latest_draw_date: str, git_sha: str,
    source_path: Path, now: datetime | None = None,
) -> dict:
    """Prepare only the canonical publisher's NEW 702+ freeze.

    This does not append the immutable Production ledger: its existing
    append_current_predictions and frozen-target check remain authoritative.
    """
    if type(latest_round) is not int or target_round != latest_round + 1:
        raise RuntimeError("invalid Production target sequence")
    if target_round < MIN_TARGET_ROUND:
        raise RuntimeError("round 701 and earlier must use existing publisher unchanged")
    production_window_guard(now or datetime.now(JST))
    if fingerprint_file(csv_path) != data_sha:
        raise RuntimeError("Production source data hash mismatch")
    verify_source(csv_path, source_path, latest_round)

    tickets = portfolio_for_target(target_round)
    text = render_ticket_csv(tickets)
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    model_version = f"{champion_version}+{VERSION}"
    state = {
        "agent_version": v4.AGENT_VERSION,
        "model_version": model_version,
        "signal_champion_version": champion_version,
        "production_ticket_policy_version": VERSION,
        "production_ticket_policy_role": "ticket_geometry_only_not_signal_promotion",
        "data_sha256": data_sha,
        "latest_round": f"第{latest_round}回",
        "latest_draw_date": latest_draw_date,
        "target_round": f"第{target_round}回",
        "seed": SEED_BASE + target_round * SEED_MULTIPLIER,
        "git_sha": git_sha,
        "production_promotion_method": "future_oos_only",
        "promotion_this_run": None,
        "ticket_count": 5,
        "covered_distinct_numbers": 35,
        "ticket_layout_sha256": text_sha,
        "expert_weights": {},
        "no_lottery_signal_skill_claim": True,
        "first_prize_odds_unchanged": True,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    # The generated candidate view is *not* the canonical frozen ledger.
    # weekly_production_prediction.freeze writes that ledger only once.
    (out_dir / "candidate_tickets.csv").write_text(text, encoding="utf-8")
    v4.write_json(out_dir / "agent_state.json", state)
    return state
